from flask import Blueprint, request, jsonify, request
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity,
    set_refresh_cookies, unset_jwt_cookies
)
from werkzeug.security import generate_password_hash, check_password_hash

import cloudinary
import cloudinary.uploader
import stripe
import os
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")

stripe.api_key = STRIPE_SECRET_KEY

from . import db
from .models import *
# ======= 🔧 Helpers =======

def is_blocked(user_id, other_user_id):
    return BlockedUser.query.filter(
        db.or_(
            db.and_(BlockedUser.user_id == user_id, BlockedUser.blocked_user_id == other_user_id),
            db.and_(BlockedUser.user_id == other_user_id, BlockedUser.blocked_user_id == user_id)
        )
    ).first() is not None

def serialize_user(user):
    return {
        "user_id": user.user_id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "handle": user.handle,
        "school_id": user.school_id
    }

def serialize_post(post):
    return {
        "post_id": post.post_id,
        "title": post.title,
        "type": post.type,
        "description": post.description,
        "price": float(post.price) if post.price else None,
        "user_id": post.user_id,
        "school_id": post.school_id,
        "chapter_id": post.chapter_id,
        "is_sold": post.is_sold,
        "visibility": post.visibility,
        "created_at": post.created_at.isoformat(),
        "main_image_url": post.images[0].url if post.images else None
    }

bp = Blueprint('main', __name__)

@bp.route("/")
def home():
    return jsonify({"message": "Welcome to GreekVault API!"})


# ✅ Get all schools
@bp.route("/schools", methods=["GET"])
def get_schools():
    schools = School.query.all()
    return jsonify([{"id": s.school_id, "name": s.name, "domain": s.domain} for s in schools])


# ✅ Register user
@bp.route("/register", methods=["POST"])
def register_user():
    data = request.get_json()
    
    required_fields = ["email", "password", "handle", "school_id"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already exists"}), 409

    if User.query.filter_by(handle=data["handle"]).first():
        return jsonify({"error": "Handle already taken"}), 409

    # Ensure school exists
    school = School.query.get(data["school_id"])
    if not school:
        return jsonify({"error": "Invalid school_id"}), 400

    user = User(
        first_name=data.get("first_name"),
        last_name=data.get("last_name"),
        email=data["email"],
        handle=data["handle"],
        school_id=data["school_id"],
        password_hash=generate_password_hash(data["password"])
    )
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "User registered on GreekVault!", "user_id": user.user_id}), 201

@bp.route("/login", methods=["POST"])
def login_user():
    data = request.get_json()
    user = User.query.filter_by(email=data.get("email")).first()

    if user and check_password_hash(user.password_hash, data.get("password")):
        access_token = create_access_token(identity=str(user.user_id))
        refresh_token = create_refresh_token(identity=str(user.user_id))

        resp = jsonify(access_token=access_token)
        # HttpOnly cookie carries the refresh token (browser stores it automatically)
        set_refresh_cookies(resp, refresh_token)
        return resp, 200

    return jsonify({"error": "Invalid credentials"}), 401



@bp.route("/me", methods=["GET"])
@jwt_required()
def get_profile():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    # Get first chapter membership if exists
    membership = UserChapterMembership.query.filter_by(user_id=user.user_id).first()
    chapter_name = None
    chapter_id = None
    chapter_role = None
    if membership:
        chapter = Chapter.query.get(membership.chapter_id)
        if chapter:
            chapter_name = chapter.name
            chapter_id = chapter.chapter_id
            chapter_role = membership.role

    return jsonify({
        "user_id": user.user_id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "handle": user.handle,
        "school_id": user.school_id,
        "profile_picture_url": user.profile_picture_url,
        "stripe_account_id": user.stripe_account_id,
        "chapter_id": chapter_id,
        "chapter_name": chapter_name,
        "chapter_role": chapter_role
    })

@bp.route("/posts", methods=["POST"])
@jwt_required()
def create_post():
    data = request.get_json()
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    post = Post(
        user_id=user_id,
        school_id=user.school_id,  # Automatically use user's school
        chapter_id=data.get("chapter_id"),
        type=data["type"],
        title=data["title"],
        description=data.get("description"),
        price=data.get("price"),
        is_sold=False,
        visibility=data.get("visibility", "public")
    )
    db.session.add(post)
    db.session.flush()

    image_urls = data.get("image_urls", [])
    for url in image_urls:
        db.session.add(PostImage(post_id=post.post_id, url=url))

    db.session.commit()
    return jsonify(serialize_post(post)), 201

@bp.route("/posts/<int:school_id>", methods=["GET"])
@jwt_required(optional=True)
def get_posts_for_school(school_id):
    user_id = get_jwt_identity()
    user = User.query.get(user_id) if user_id else None

    allowed_chapter_ids = []
    if user:
        allowed_chapter_ids = [
            m.chapter_id for m in UserChapterMembership.query.filter_by(user_id=user_id).all()
        ]

    query = Post.query.filter_by(school_id=school_id)

    # Filter by visibility
    query = query.filter(
        db.or_(
            Post.visibility == 'public',
            db.and_(Post.visibility == 'school', user and Post.school_id == user.school_id),
            db.and_(Post.visibility == 'chapter', Post.chapter_id.in_(allowed_chapter_ids))
        )
    )

    # Optional filters
    post_type = request.args.get("type")
    if post_type:
        query = query.filter_by(type=post_type)

    sort = request.args.get("sort")
    if sort == "price":
        query = query.order_by(Post.price.asc())
    elif sort == "-price":
        query = query.order_by(Post.price.desc())
    else:
        query = query.order_by(Post.created_at.desc())

    posts = query.all()

    result = []
    for p in posts:
        if user_id and is_blocked(user_id, p.user_id):
            continue
        post_data = serialize_post(p)
        post_data["user_handle"] = p.user.handle
        result.append(post_data)

    return jsonify(result)

@bp.route("/post/<int:post_id>", methods=["GET"])
@jwt_required(optional=True)
def get_post_detail(post_id):
    user_id = get_jwt_identity()
    post = Post.query.get(post_id)

    if not post:
        return jsonify({"error": "Post not found"}), 404

    # Prevent blocked users from seeing each other's posts
    if user_id and is_blocked(user_id, post.user_id):
        return jsonify({"error": "You are not allowed to view this post"}), 403

    post.views += 1
    db.session.commit()

    post_data = serialize_post(post)
    post_data["image_urls"] = [img.url for img in post.images]
    post_data["views"] = post.views
    post_data["user_handle"] = post.user.handle

    return jsonify(post_data)

@bp.route("/my-posts", methods=["GET"])
@jwt_required()
def get_my_posts():
    user_id = get_jwt_identity()
    posts = Post.query.filter_by(user_id=user_id).order_by(Post.created_at.desc()).all()

    return jsonify([
        {
            **serialize_post(p),
            "user_handle": p.user.handle
        } for p in posts
    ])

@bp.route("/join-chapter", methods=["POST"])
@jwt_required()
def join_chapter():
    user_id = get_jwt_identity()
    data = request.get_json()
    chapter_id = data.get("chapter_id")

    if not chapter_id:
        return jsonify({"error": "Missing chapter_id"}), 400

    # Check if chapter exists
    chapter = Chapter.query.get(chapter_id)
    if not chapter:
        return jsonify({"error": "Chapter not found"}), 404

    # Prevent duplicate memberships
    existing = UserChapterMembership.query.filter_by(user_id=user_id, chapter_id=chapter_id).first()
    if existing:
        return jsonify({"message": "Already a member"}), 200

    # ✅ Provide default role explicitly
    membership = UserChapterMembership(
        user_id=user_id,
        chapter_id=chapter_id,
        role="member"
    )
    db.session.add(membership)
    db.session.commit()

    return jsonify({"message": "Joined chapter!"}), 201

@bp.route("/promote-member", methods=["POST"])
@jwt_required()
def promote_member():
    user_id = get_jwt_identity()
    data = request.get_json()
    target_id = data.get("user_id")

    if not target_id:
        return jsonify({"error": "Missing user_id"}), 400

    admin_membership = UserChapterMembership.query.filter_by(user_id=user_id, role="admin").first()
    if not admin_membership:
        return jsonify({"error": "Only chapter admins can promote"}), 403

    target = UserChapterMembership.query.filter_by(
        user_id=target_id,
        chapter_id=admin_membership.chapter_id
    ).first()

    if not target:
        return jsonify({"error": "Target user not in your chapter"}), 404

    target.role = "admin"
    db.session.commit()

    return jsonify({"message": "User promoted to admin"}), 200

# Route to search chapters by name or nickname (fuzzy matching)
@bp.route("/search/chapters", methods=["GET"])
def search_chapters():
    query = request.args.get("q", "").lower()
    if not query:
        return jsonify([])

    chapters = Chapter.query.all()

    matches = []
    for chapter in chapters:
        name = (chapter.name or "").lower()
        nickname = (chapter.nickname or "").lower()
        if query in name or query in nickname:
            matches.append({
                "chapter_id": chapter.chapter_id,
                "name": chapter.name,
                "nickname": chapter.nickname,
                "school_id": chapter.school_id,
                "type": chapter.type
            })

    return jsonify(matches)

@bp.route("/search/posts")
@jwt_required(optional=True)
def search_posts():
    user_id = get_jwt_identity()
    query = request.args.get("q", "").strip().lower()
    if not query:
        return jsonify({"error": "Missing query string"}), 400

    user = User.query.get(user_id) if user_id else None
    school_id = user.school_id if user else None

    chapter_ids = []
    if user_id:
        chapter_ids = [
            m.chapter_id for m in UserChapterMembership.query.filter_by(user_id=user_id).all()
        ]

    posts = Post.query.filter(
        db.and_(
            db.or_(
                Post.title.ilike(f"%{query}%"),
                Post.description.ilike(f"%{query}%")
            ),
            db.or_(
                Post.visibility == 'public',
                db.and_(Post.visibility == 'school', Post.school_id == school_id),
                db.and_(Post.visibility == 'chapter', Post.chapter_id.in_(chapter_ids))
            )
        )
    ).order_by(Post.created_at.desc()).all()

    # Filter out posts where the user is blocked or has blocked the poster
    filtered_posts = [
        p for p in posts
        if not user_id or not is_blocked(user_id, p.user_id)
    ]

    return jsonify([
        {
            **serialize_post(p),
            "user_handle": p.user.handle
        } for p in filtered_posts
    ])

@bp.route("/search/schools")
def search_schools():
    query = request.args.get("q", "").strip().lower()
    if not query:
        return jsonify([])

    schools = School.query.filter(
        db.or_(
            School.name.ilike(f"%{query}%"),
            School.domain.ilike(f"%{query}%")
        )
    ).all()

    return jsonify([
        {
            "school_id": s.school_id,
            "name": s.name,
            "domain": s.domain
        } for s in schools
    ])

@bp.route("/search/users", methods=["GET"])
@jwt_required()
def search_users():
    query = request.args.get("q", "").lower()
    if not query:
        return jsonify({"error": "Missing search query"}), 400

    current_user_id = get_jwt_identity()

    # Get blocked user IDs
    blocked_ids = set(b.user_id for b in Block.query.filter_by(blocked_by=current_user_id).all())
    blocked_by_ids = set(b.blocked_by for b in Block.query.filter_by(user_id=current_user_id).all())
    excluded_ids = blocked_ids.union(blocked_by_ids)

    users = User.query.filter(
        ~User.user_id.in_(excluded_ids),
        db.or_(
            User.first_name.ilike(f"%{query}%"),
            User.last_name.ilike(f"%{query}%"),
            User.email.ilike(f"%{query}%")
        )
    ).all()

    return jsonify([serialize_user(u) for u in users])

@bp.route("/upload-image", methods=["POST"])
@jwt_required()
def upload_image():
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    image_file = request.files['image']
    if image_file.filename == '':
        return jsonify({"error": "Empty filename"}), 400

    try:
        upload_result = cloudinary.uploader.upload(
            image_file,
            folder="greekmarket/posts",
            public_id=None,
            overwrite=True,
            resource_type="image"
        )
        return jsonify({"url": upload_result["secure_url"]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route("/posts/<int:post_id>/comment", methods=["POST"])
@jwt_required()
def add_comment(post_id):
    data = request.get_json()
    user_id = get_jwt_identity()
    text = data.get("text")

    if not text:
        return jsonify({"error": "Comment text is required"}), 400

    post = Post.query.get(post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404

    comment = Comment(user_id=user_id, post_id=post_id, text=text)
    db.session.add(comment)
    db.session.commit()

    return jsonify({"message": "Comment added"}), 201

@bp.route("/posts/<int:post_id>/comments", methods=["GET"])
def get_comments(post_id):
    comments = Comment.query.filter_by(post_id=post_id).order_by(Comment.created_at.asc()).all()

    return jsonify([
        {
            "comment_id": c.comment_id,
            "user_id": c.user_id,
            "text": c.text,
            "created_at": c.created_at.isoformat()
        } for c in comments
    ])

# ❤️ Add a post to favorites
@bp.route("/posts/<int:post_id>/favorite", methods=["POST"])
@jwt_required()
def favorite_post(post_id):
    user_id = get_jwt_identity()
    post = Post.query.get(post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404

    existing = Favorite.query.filter_by(user_id=user_id, post_id=post_id).first()
    if existing:
        return jsonify({"message": "Already favorited"}), 200

    db.session.add(Favorite(user_id=user_id, post_id=post_id))
    db.session.commit()
    return jsonify({"message": "Post favorited!"}), 201


# 💔 Remove a post from favorites
@bp.route("/posts/<int:post_id>/unfavorite", methods=["DELETE"])
@jwt_required()
def unfavorite_post(post_id):
    user_id = get_jwt_identity()
    favorite = Favorite.query.filter_by(user_id=user_id, post_id=post_id).first()
    if not favorite:
        return jsonify({"error": "Favorite not found"}), 404

    db.session.delete(favorite)
    db.session.commit()
    return jsonify({"message": "Post unfavorited"}), 200


@bp.route("/my-favorites", methods=["GET"])
@jwt_required()
def get_my_favorites():
    user_id = get_jwt_identity()
    favorites = Favorite.query.filter_by(user_id=user_id).all()

    post_ids = [f.post_id for f in favorites]
    posts = Post.query.filter(Post.post_id.in_(post_ids)).all()

    visible_posts = [
        p for p in posts
        if not is_blocked(user_id, p.user_id)
    ]

    return jsonify([
        {
            **serialize_post(p),
            "user_handle": p.user.handle
        } for p in visible_posts
    ])

@bp.route("/activity/posts", methods=["GET"])
@jwt_required(optional=True)
def recent_posts():
    viewer_id = get_jwt_identity()
    posts = Post.query.order_by(Post.created_at.desc()).limit(20).all()

    visible_posts = [
        p for p in posts
        if not viewer_id or not is_blocked(viewer_id, p.user_id)
    ]

    return jsonify([
        {
            **serialize_post(p),
            "user_handle": p.user.handle
        } for p in visible_posts
    ])

@bp.route("/activity/comments", methods=["GET"])
def recent_comments():
    comments = Comment.query.order_by(Comment.created_at.desc()).limit(20).all()
    return jsonify([
        {
            "comment_id": c.comment_id,
            "text": c.text,
            "post_id": c.post_id,
            "user_id": c.user_id,
            "created_at": c.created_at.isoformat()
        } for c in comments
    ])

@bp.route("/my-chapter/posts", methods=["GET"])
@jwt_required()
def get_my_chapter_posts():
    user_id = get_jwt_identity()
    membership = UserChapterMembership.query.filter_by(user_id=user_id).first()

    if not membership:
        return jsonify({"error": "You are not in a chapter"}), 403

    posts = Post.query.filter_by(chapter_id=membership.chapter_id).order_by(Post.created_at.desc()).all()

    visible_posts = [
        p for p in posts if not is_blocked(user_id, p.user_id)
    ]

    return jsonify([
        {
            **serialize_post(p),
            "user_handle": p.user.handle
        } for p in visible_posts
    ])

@bp.route("/my-chapter/users", methods=["GET"])
@jwt_required()
def get_my_chapter_users():
    user_id = get_jwt_identity()
    membership = UserChapterMembership.query.filter_by(user_id=user_id).first()

    if not membership:
        return jsonify({"error": "You are not in a chapter"}), 403

    memberships = UserChapterMembership.query.filter_by(chapter_id=membership.chapter_id).all()
    user_ids = [m.user_id for m in memberships]
    users = User.query.filter(User.user_id.in_(user_ids)).all()

    visible_users = [
        u for u in users if not is_blocked(user_id, u.user_id)
    ]
    user_dict = {u.user_id: u for u in visible_users}

    return jsonify([
        {
            **serialize_user(user_dict[m.user_id]),
            "role": m.role
        } for m in memberships if m.user_id in user_dict
    ])

@bp.route("/user/<int:user_id>/posts", methods=["GET"])
@jwt_required(optional=True)
def get_posts_by_user(user_id):
    current_user_id = get_jwt_identity()

    # Block check
    if current_user_id and is_blocked(current_user_id, user_id):
        return jsonify([])

    posts = Post.query.filter_by(user_id=user_id).order_by(Post.created_at.desc()).all()
    return jsonify([jsonify_post(p) for p in posts])

@bp.route("/admin/remove-user", methods=["POST"])
@jwt_required()
def admin_remove_user():
    admin_id = get_jwt_identity()
    data = request.get_json()
    target_id = data.get("user_id")

    if not target_id:
        return jsonify({"error": "Missing user_id"}), 400

    admin_membership = UserChapterMembership.query.filter_by(user_id=admin_id, role="admin").first()
    if not admin_membership:
        return jsonify({"error": "Only admins can remove users"}), 403

    membership = UserChapterMembership.query.filter_by(
        user_id=target_id,
        chapter_id=admin_membership.chapter_id
    ).first()

    if not membership:
        return jsonify({"error": "User not found in your chapter"}), 404

    db.session.delete(membership)
    db.session.commit()
    return jsonify({"message": "User removed from chapter"}), 200

@bp.route("/admin/delete-post/<int:post_id>", methods=["DELETE"])
@jwt_required()
def delete_post(post_id):
    user_id = get_jwt_identity()
    admin_membership = UserChapterMembership.query.filter_by(user_id=user_id, role="admin").first()

    if not admin_membership:
        return jsonify({"error": "Only chapter admins can delete posts"}), 403

    post = Post.query.get(post_id)

    if not post:
        return jsonify({"error": "Post not found"}), 404

    if not post.chapter_id:
        return jsonify({"error": "Post is not assigned to a chapter"}), 400

    if post.chapter_id != admin_membership.chapter_id:
        return jsonify({"error": "Post not found in your chapter"}), 404

    db.session.delete(post)
    db.session.commit()
    return jsonify({"message": "Post deleted successfully"}), 200

@bp.route("/admin/analytics", methods=["GET"])
@jwt_required()
def chapter_analytics():
    user_id = get_jwt_identity()

    # Check if user is an admin
    membership = UserChapterMembership.query.filter_by(user_id=user_id, role="admin").first()
    if not membership:
        return jsonify({"error": "Only chapter admins can view analytics"}), 403

    chapter_id = membership.chapter_id

    total_posts = Post.query.filter_by(chapter_id=chapter_id).count()
    total_users = UserChapterMembership.query.filter_by(chapter_id=chapter_id).count()

    # Join posts and comments
    total_comments = db.session.query(Comment).join(Post).filter(Post.chapter_id == chapter_id).count()

    return jsonify({
        "chapter_id": chapter_id,
        "total_posts": total_posts,
        "total_users": total_users,
        "total_comments": total_comments
    }), 200

@bp.route("/admin/analytics/platform", methods=["GET"])
@jwt_required()
def get_platform_analytics():
    user_id = get_jwt_identity()

    admin_membership = UserChapterMembership.query.filter_by(user_id=user_id, role="admin").first()
    if not admin_membership:
        return jsonify({"error": "Only chapter admins can view analytics"}), 403

    return jsonify({
        "total_users": User.query.count(),
        "total_posts": Post.query.count(),
        "total_comments": Comment.query.count(),
        "total_chapters": Chapter.query.count()
    })

@bp.route("/analytics/post/<int:post_id>", methods=["GET"])
def get_post_analytics(post_id):
    post = Post.query.get(post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404

    view_count = post.views or 0
    comment_count = Comment.query.filter_by(post_id=post_id).count()
    image_count = PostImage.query.filter_by(post_id=post_id).count()

    return jsonify({
        "post_id": post_id,
        "views": view_count,
        "comments": comment_count,
        "images": image_count
    }), 200

# 📩 Send a direct message
@bp.route("/messages/send", methods=["POST"])
@jwt_required()
def send_message():
    sender_id = get_jwt_identity()
    data = request.get_json()

    recipient_id = data.get("recipient_id")
    text = data.get("text")
    image_url = data.get("image_url")

    if not recipient_id or not text:
        return jsonify({"error": "Missing recipient_id or text"}), 400

    # Prevent sending messages if either user has blocked the other
    if is_blocked(sender_id, recipient_id):
        return jsonify({"error": "Cannot message this user"}), 403

    message = Message(
        sender_id=sender_id,
        recipient_id=recipient_id,
        text=text,
        image_url=image_url
    )
    db.session.add(message)
    db.session.commit()

    return jsonify({"message": "Message sent!"}), 201

# 📬 Get conversation between two users
@bp.route("/messages/conversation/<int:user_id>", methods=["GET"])
@jwt_required()
def get_conversation(user_id):
    current_user = get_jwt_identity()

    # Use helper to check block status
    if is_blocked(current_user, user_id):
        return jsonify({"error": "You cannot view this conversation"}), 403

    messages = Message.query.filter(
        db.or_(
            db.and_(Message.sender_id == current_user, Message.recipient_id == user_id),
            db.and_(Message.sender_id == user_id, Message.recipient_id == current_user)
        )
    ).order_by(Message.sent_at.asc()).all()

    return jsonify([
        {
            "message_id": m.message_id,
            "sender_id": m.sender_id,
            "recipient_id": m.recipient_id,
            "text": m.text,
            "image_url": m.image_url,
            "sent_at": m.sent_at.isoformat()
        } for m in messages
    ])

@bp.route("/messages/inbox", methods=["GET"])
@jwt_required()
def inbox():
    user_id = int(get_jwt_identity())

    # Get all pinned user IDs for this user
    pinned_users = {
        pin.other_user_id for pin in PinnedConversation.query.filter_by(user_id=user_id).all()
    }

    messages = Message.query.filter(
        db.or_(Message.sender_id == user_id, Message.recipient_id == user_id)
    ).order_by(Message.sent_at.desc()).all()

    conversations = {}
    for msg in messages:
        other_user_id = msg.recipient_id if msg.sender_id == user_id else msg.sender_id

        if is_blocked(user_id, other_user_id):
            continue

        convo_key = tuple(sorted([user_id, other_user_id]))

        if convo_key not in conversations:
            unread_count = Message.query.filter_by(
                sender_id=other_user_id,
                recipient_id=user_id,
                read=False
            ).count()

            conversations[convo_key] = {
                "user_id": other_user_id,
                "last_message": msg.text,
                "timestamp": msg.sent_at.isoformat(),
                "unread_count": unread_count,
                "pinned": other_user_id in pinned_users
            }

    # Sort with pinned conversations first
    sorted_conversations = sorted(
        conversations.values(),
        key=lambda c: (not c["pinned"], c["timestamp"]),
        reverse=True
    )

    return jsonify(sorted_conversations)

@bp.route("/messages/<int:with_user_id>/read", methods=["POST"])
@jwt_required()
def mark_messages_as_read(with_user_id):
    user_id = get_jwt_identity()
    messages = Message.query.filter_by(sender_id=with_user_id, recipient_id=user_id, read=False).all()

    for msg in messages:
        msg.read = True

    db.session.commit()
    return jsonify({"message": "Messages marked as read"}), 200

@bp.route("/messages/delete/<int:message_id>", methods=["DELETE"])
@jwt_required()
def delete_message(message_id):
    user_id = int(get_jwt_identity())
    message = Message.query.get(message_id)

    if not message:
        return jsonify({"error": "Message not found"}), 404

    if message.sender_id != user_id:
        return jsonify({"error": "You can only delete your own messages"}), 403

    db.session.delete(message)
    db.session.commit()
    return jsonify({"message": "Message deleted"}), 200

@bp.route("/messages/<int:message_id>/edit", methods=["PUT"])
@jwt_required()
def edit_message(message_id):
    user_id = get_jwt_identity()
    message = Message.query.get(message_id)

    if not message:
        return jsonify({"error": "Message not found"}), 404

    if message.sender_id != int(user_id):
        return jsonify({"error": "You can only edit your own messages"}), 403

    data = request.get_json()
    new_text = data.get("text")

    if not new_text:
        return jsonify({"error": "New message text required"}), 400

    message.text = new_text
    db.session.commit()

    return jsonify({"message": "Message updated"}), 200

@bp.route("/messages/unread-count", methods=["GET"])
@jwt_required()
def unread_message_count():
    user_id = get_jwt_identity()
    count = Message.query.filter_by(recipient_id=user_id, read=False).count()
    return jsonify({"unread_count": count}), 200

@bp.route("/messages/inbox/search", methods=["GET"])
@jwt_required()
def search_inbox():
    user_id = int(get_jwt_identity())
    query = request.args.get("q", "").lower()

    if not query:
        return jsonify({"error": "Missing search query"}), 400

    # Get all messages involving the current user
    messages = Message.query.filter(
        db.or_(Message.sender_id == user_id, Message.recipient_id == user_id)
    ).order_by(Message.sent_at.desc()).all()

    results = []
    seen_conversations = set()

    for msg in messages:
        other_user_id = msg.recipient_id if msg.sender_id == user_id else msg.sender_id
        convo_key = tuple(sorted([user_id, other_user_id]))

        if convo_key in seen_conversations:
            continue

        # Check if search matches message or user info
        other_user = User.query.get(other_user_id)
        match = (
            (query in (msg.text or "").lower()) or
            (query in (other_user.first_name or "").lower()) or
            (query in (other_user.last_name or "").lower())
        )

        if match:
            seen_conversations.add(convo_key)
            results.append({
                "user_id": other_user_id,
                "handle": other_user.handle,
                "last_message": msg.text,
                "timestamp": msg.sent_at.isoformat(),
                "unread": (not msg.read and msg.recipient_id == user_id)
            })

    return jsonify(results)

@bp.route("/messages/pin/<int:other_user_id>", methods=["POST"])
@jwt_required()
def pin_conversation(other_user_id):
    user_id = get_jwt_identity()

    # Prevent pinning self
    if user_id == other_user_id:
        return jsonify({"error": "Cannot pin conversation with yourself"}), 400

    # Count existing pins
    existing_pins = PinnedConversation.query.filter_by(user_id=user_id).count()
    if existing_pins >= 3:
        return jsonify({"error": "You can only pin up to 3 conversations"}), 403

    # Prevent duplicate pin
    if PinnedConversation.query.filter_by(user_id=user_id, other_user_id=other_user_id).first():
        return jsonify({"message": "Already pinned"}), 200

    pin = PinnedConversation(user_id=user_id, other_user_id=other_user_id)
    db.session.add(pin)
    db.session.commit()
    return jsonify({"message": "Conversation pinned"}), 201

@bp.route("/messages/unpin/<int:other_user_id>", methods=["DELETE"])
@jwt_required()
def unpin_conversation(other_user_id):
    user_id = get_jwt_identity()
    pin = PinnedConversation.query.filter_by(user_id=user_id, other_user_id=other_user_id).first()

    if not pin:
        return jsonify({"error": "Pin not found"}), 404

    db.session.delete(pin)
    db.session.commit()
    return jsonify({"message": "Conversation unpinned"}), 200

@bp.route("/posts/<int:post_id>/mark-sold", methods=["POST"])
@jwt_required()
def mark_post_sold(post_id):
    user_id = get_jwt_identity()
    post = Post.query.get(post_id)

    if not post:
        return jsonify({"error": "Post not found"}), 404

    if post.user_id != user_id:
        return jsonify({"error": "You can only mark your own posts as sold"}), 403

    post.is_sold = True
    db.session.commit()
    return jsonify({"message": "Post marked as SOLD!"}), 200

@bp.route("/posts/<int:post_id>", methods=["PUT"])
@jwt_required()
def edit_post(post_id):
    user_id = get_jwt_identity()
    post = Post.query.get(post_id)

    if not post:
        return jsonify({"error": "Post not found"}), 404

    if post.user_id != int(user_id):
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()
    post.title = data.get("title", post.title)
    post.description = data.get("description", post.description)
    post.price = data.get("price", post.price)
    post.visibility = data.get("visibility", post.visibility)  # ✅ Update visibility

    if "image_urls" in data:
        PostImage.query.filter_by(post_id=post_id).delete()
        for url in data["image_urls"]:
            db.session.add(PostImage(post_id=post_id, url=url))

    db.session.commit()
    return jsonify({"message": "Post updated successfully"}), 200

@bp.route("/posts/<int:post_id>/report", methods=["POST"])
@jwt_required()
def report_post(post_id):
    user_id = get_jwt_identity()
    data = request.get_json()
    reason = data.get("reason")

    if not reason:
        return jsonify({"error": "Report reason is required"}), 400

    post = Post.query.get(post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404

    report = PostReport(user_id=user_id, post_id=post_id, reason=reason)
    db.session.add(report)
    db.session.commit()

    return jsonify({"message": "Post reported successfully"}), 201

@bp.route("/report/user/<int:reported_user_id>", methods=["POST"])
@jwt_required()
def report_user(reported_user_id):
    user_id = get_jwt_identity()
    data = request.get_json()
    reason = data.get("reason")

    if not reason:
        return jsonify({"error": "Reason is required"}), 400

    if user_id == reported_user_id:
        return jsonify({"error": "You cannot report yourself"}), 400

    existing = UserReport.query.filter_by(user_id=user_id, reported_user_id=reported_user_id).first()
    if existing:
        return jsonify({"message": "You already reported this user"}), 200

    report = UserReport(user_id=user_id, reported_user_id=reported_user_id, reason=reason)
    db.session.add(report)
    db.session.commit()

    return jsonify({"message": "User reported successfully"}), 201

@bp.route("/block/<int:blocked_user_id>", methods=["POST"])
@jwt_required()
def block_user(blocked_user_id):
    user_id = get_jwt_identity()

    if user_id == blocked_user_id:
        return jsonify({"error": "You cannot block yourself"}), 400

    existing = BlockedUser.query.filter_by(user_id=user_id, blocked_user_id=blocked_user_id).first()
    if existing:
        return jsonify({"message": "User already blocked"}), 200

    block = BlockedUser(user_id=user_id, blocked_user_id=blocked_user_id)
    db.session.add(block)
    db.session.commit()
    return jsonify({"message": "User blocked successfully"}), 201

@bp.route("/unblock/<int:blocked_user_id>", methods=["DELETE"])
@jwt_required()
def unblock_user(blocked_user_id):
    user_id = get_jwt_identity()

    block = BlockedUser.query.filter_by(user_id=user_id, blocked_user_id=blocked_user_id).first()
    if not block:
        return jsonify({"error": "User is not blocked"}), 404

    db.session.delete(block)
    db.session.commit()
    return jsonify({"message": "User unblocked successfully"}), 200

@bp.route("/user/<int:user_id>", methods=["GET"])
@jwt_required()
def get_user_profile(user_id):
    current_user_id = get_jwt_identity()

    # Use shared helper for block check
    if is_blocked(current_user_id, user_id):
        return jsonify({"error": "Access denied"}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify(serialize_user(user))

@bp.route("/create-checkout-session", methods=["POST"])
@jwt_required()
def create_checkout_session():
    data = request.get_json()
    post_id = data.get("post_id")
    price = data.get("price")  # price in dollars
    post_title = data.get("title")

    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user or not user.stripe_account_id:
        return jsonify({"error": "User must have a Stripe recipient account connected."}), 400

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": post_title,
                    },
                    "unit_amount": int(float(price) * 100),  # Stripe requires amount in cents
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=os.getenv("FRONTEND_URL") + "/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=os.getenv("FRONTEND_URL") + "/cancel",
            metadata={
                "post_id": post_id,
                "buyer_id": user_id
            }
        )

        return jsonify({"checkout_url": session.url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route("/create-account-link", methods=["POST"])
@jwt_required()
def create_account_link():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    if not user.stripe_account_id:
        account = stripe.Account.create(type="express")
        user.stripe_account_id = account.id
        db.session.commit()
    else:
        account = stripe.Account.retrieve(user.stripe_account_id)

    account_link = stripe.AccountLink.create(
        account=account.id,
        refresh_url=os.getenv("FRONTEND_URL") + "/reauth",
        return_url=os.getenv("FRONTEND_URL") + "/account",
        type="account_onboarding",
    )

    return jsonify({"url": account_link.url})

@bp.route("/webhook", methods=["POST"])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError as e:
        return jsonify({"error": "Invalid payload"}), 400
    except stripe.error.SignatureVerificationError as e:
        return jsonify({"error": "Invalid signature"}), 400

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata", {})
        post_id = metadata.get("post_id")
        buyer_id = metadata.get("buyer_id")

        if post_id and buyer_id:
            # Check if this purchase already exists
            existing = Purchase.query.filter_by(post_id=post_id, buyer_id=buyer_id).first()
            if not existing:
                purchase = Purchase(post_id=post_id, buyer_id=buyer_id)
                db.session.add(purchase)

                # Optionally mark post as sold
                post = Post.query.get(post_id)
                if post:
                    post.is_sold = True

                db.session.commit()

    return jsonify({"status": "success"}), 200

@bp.route("/my-purchases", methods=["GET"])
@jwt_required()
def get_my_purchases():
    user_id = get_jwt_identity()

    purchases = Purchase.query.filter_by(buyer_id=user_id).order_by(Purchase.purchased_at.desc()).all()

    results = []
    for purchase in purchases:
        post = purchase.post
        if not post:
            continue

        seller = post.user
        results.append({
            "purchase_id": purchase.purchase_id,
            "post_id": post.post_id,
            "title": post.title,
            "price": post.price,
            "image_url": post.images[0].url if post.images else None,
            "purchased_at": purchase.purchased_at.isoformat(),
            "seller": {
                "user_id": seller.user_id,
                "first_name": seller.first_name,
                "last_name": seller.last_name,
                "handle": seller.handle
            }
        })

    return jsonify(results), 200

@bp.route("/token/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh_access_token():
    user_id = get_jwt_identity()
    new_access = create_access_token(identity=str(user_id))
    return jsonify(access_token=new_access), 200

@bp.route("/logout", methods=["POST"])
def logout():
    resp = jsonify({"message": "Logged out"})
    unset_jwt_cookies(resp)
    return resp, 200
