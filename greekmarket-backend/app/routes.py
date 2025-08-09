# app/routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity,
    set_refresh_cookies, unset_jwt_cookies
)
from werkzeug.security import generate_password_hash, check_password_hash

import os
import stripe
import cloudinary
import cloudinary.uploader

from . import db
from .models import (
    School, User, Chapter, UserChapterMembership, Post, PostImage, Comment,
    Favorite, Message, PinnedConversation, PostReport, UserReport, BlockedUser,
    Purchase
)

# -----------------------------------------------------------------------------
# Setup
# -----------------------------------------------------------------------------
bp = Blueprint("main", __name__)

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
stripe.api_key = STRIPE_SECRET_KEY


# -----------------------------------------------------------------------------
# Helpers / Serializers
# -----------------------------------------------------------------------------
def is_blocked(user_id: int, other_user_id: int) -> bool:
    """Return True if either user has blocked the other."""
    return BlockedUser.query.filter(
        db.or_(
            db.and_(
                BlockedUser.user_id == user_id,
                BlockedUser.blocked_user_id == other_user_id
            ),
            db.and_(
                BlockedUser.user_id == other_user_id,
                BlockedUser.blocked_user_id == user_id
            ),
        )
    ).first() is not None


def serialize_user(user: User) -> dict:
    return {
        "user_id": user.user_id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "handle": user.handle,
        "school_id": user.school_id,
        "profile_picture_url": user.profile_picture_url,
        "stripe_account_id": user.stripe_account_id,
    }


def serialize_post(post: Post) -> dict:
    return {
        "post_id": post.post_id,
        "title": post.title,
        "type": post.type,
        "description": post.description,
        "price": float(post.price) if post.price is not None else None,
        "user_id": post.user_id,
        "school_id": post.school_id,
        "chapter_id": post.chapter_id,
        "is_sold": post.is_sold,
        "visibility": post.visibility,
        "created_at": post.created_at.isoformat(),
        "main_image_url": post.images[0].url if post.images else None,
    }


# -----------------------------------------------------------------------------
# Root / Health
# -----------------------------------------------------------------------------
@bp.route("/")
def home():
    return jsonify({"message": "Welcome to GreekVault API!"})


# -----------------------------------------------------------------------------
# Auth
# -----------------------------------------------------------------------------
@bp.route("/register", methods=["POST"])
def register_user():
    data = request.get_json() or {}

    required = ["email", "password", "handle", "school_id"]
    if not all(k in data for k in required):
        return jsonify({"error": "Missing required fields"}), 400

    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already exists"}), 409

    if User.query.filter_by(handle=data["handle"]).first():
        return jsonify({"error": "Handle already taken"}), 409

    school = School.query.get(data["school_id"])
    if not school:
        return jsonify({"error": "Invalid school_id"}), 400

    user = User(
        first_name=data.get("first_name"),
        last_name=data.get("last_name"),
        email=data["email"],
        handle=data["handle"],
        school_id=school.school_id,
        password_hash=generate_password_hash(data["password"]),
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "User registered on GreekVault!", "user_id": user.user_id}), 201


@bp.route("/login", methods=["POST"])
def login_user():
    data = request.get_json() or {}
    user = User.query.filter_by(email=data.get("email")).first()

    if user and check_password_hash(user.password_hash, data.get("password")):
        access_token = create_access_token(identity=str(user.user_id))
        refresh_token = create_refresh_token(identity=str(user.user_id))
        resp = jsonify(access_token=access_token)
        set_refresh_cookies(resp, refresh_token)  # HttpOnly cookie
        return resp, 200

    return jsonify({"error": "Invalid credentials"}), 401


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


# -----------------------------------------------------------------------------
# Profile
# -----------------------------------------------------------------------------
@bp.route("/me", methods=["GET"])
@jwt_required()
def get_profile():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    membership = UserChapterMembership.query.filter_by(user_id=user.user_id).first()
    chapter_name = chapter_id = chapter_role = None
    if membership:
        chapter = Chapter.query.get(membership.chapter_id)
        if chapter:
            chapter_name = chapter.name
            chapter_id = chapter.chapter_id
            chapter_role = membership.role

    return jsonify({
        **serialize_user(user),
        "chapter_id": chapter_id,
        "chapter_name": chapter_name,
        "chapter_role": chapter_role,
    })


@bp.route("/me", methods=["PUT"])
@jwt_required()
def update_profile():
    """
    Minimal profile update (currently supports setting school_id).
    Body: { "school_id": <int> }
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json() or {}
    school_id = data.get("school_id")

    if school_id is not None:
        school = School.query.get(school_id)
        if not school:
            return jsonify({"error": "Invalid school_id"}), 400
        user.school_id = school.school_id

    db.session.commit()
    return jsonify({"message": "Profile updated.", "school_id": user.school_id})


# -----------------------------------------------------------------------------
# Lookups / Search
# -----------------------------------------------------------------------------
@bp.route("/schools", methods=["GET"])
def get_schools():
    schools = School.query.all()
    return jsonify([{"id": s.school_id, "name": s.name, "domain": s.domain} for s in schools])


@bp.route("/search/schools")
def search_schools():
    q = (request.args.get("q") or "").strip().lower()
    if not q:
        return jsonify([])
    schools = School.query.filter(
        db.or_(School.name.ilike(f"%{q}%"), School.domain.ilike(f"%{q}%"))
    ).all()
    return jsonify([{"school_id": s.school_id, "name": s.name, "domain": s.domain} for s in schools])


@bp.route("/search/chapters", methods=["GET"])
def search_chapters():
    q = (request.args.get("q") or "").strip().lower()
    if not q:
        return jsonify([])
    chapters = Chapter.query.all()
    matches = []
    for c in chapters:
        name = (c.name or "").lower()
        nickname = (c.nickname or "").lower()
        if q in name or q in nickname:
            matches.append({
                "chapter_id": c.chapter_id,
                "name": c.name,
                "nickname": c.nickname,
                "school_id": c.school_id,
                "type": c.type,
            })
    return jsonify(matches)


@bp.route("/search/users", methods=["GET"])
@jwt_required()
def search_users():
    q = (request.args.get("q") or "").strip().lower()
    if not q:
        return jsonify({"error": "Missing search query"}), 400

    me = get_jwt_identity()

    # Who I blocked
    blocked_ids = {
        b.blocked_user_id for b in BlockedUser.query.filter_by(user_id=me).all()
    }
    # Who blocked me
    blocked_by_ids = {
        b.user_id for b in BlockedUser.query.filter_by(blocked_user_id=me).all()
    }
    excluded = blocked_ids | blocked_by_ids

    users = User.query.filter(
        ~User.user_id.in_(excluded),
        db.or_(
            User.first_name.ilike(f"%{q}%"),
            User.last_name.ilike(f"%{q}%"),
            User.email.ilike(f"%{q}%"),
            User.handle.ilike(f"%{q}%"),
        )
    ).all()
    return jsonify([serialize_user(u) for u in users])


@bp.route("/search/posts", methods=["GET"])
@jwt_required(optional=True)
def search_posts():
    viewer_id = get_jwt_identity()
    q = (request.args.get("q") or "").strip().lower()
    if not q:
        return jsonify({"error": "Missing query string"}), 400

    viewer = User.query.get(viewer_id) if viewer_id else None
    viewer_school_id = viewer.school_id if viewer else None

    chapter_ids = []
    if viewer_id:
        chapter_ids = [
            m.chapter_id for m in UserChapterMembership.query.filter_by(user_id=viewer_id)
        ]

    posts = Post.query.filter(
        db.and_(
            db.or_(Post.title.ilike(f"%{q}%"), Post.description.ilike(f"%{q}%")),
            db.or_(
                Post.visibility == "public",
                db.and_(Post.visibility == "school", Post.school_id == viewer_school_id),
                db.and_(Post.visibility == "chapter", Post.chapter_id.in_(chapter_ids)),
            ),
        )
    ).order_by(Post.created_at.desc()).all()

    visible = [p for p in posts if not viewer_id or not is_blocked(viewer_id, p.user_id)]
    return jsonify([{**serialize_post(p), "user_handle": p.user.handle} for p in visible])


# -----------------------------------------------------------------------------
# Chapters
# -----------------------------------------------------------------------------

@bp.route("/chapters/<int:chapter_id>", methods=["GET"])
@jwt_required(optional=True)
def get_chapter_detail(chapter_id):
    """
    Chapter profile:
      - basic info
      - is_member (if logged in)
      - stats (members, recent_posts)
      - recent posts (lightweight)
      - members (first/last/handle/avatar/role)
    """
    user_id = get_jwt_identity()
    chapter = Chapter.query.get(chapter_id)
    if not chapter:
        return jsonify({"error": "Chapter not found"}), 404

    # membership for current user
    is_member = False
    if user_id:
        is_member = UserChapterMembership.query.filter_by(
            user_id=user_id, chapter_id=chapter_id
        ).first() is not None

    # stats
    member_count = UserChapterMembership.query.filter_by(chapter_id=chapter_id).count()

    recent_posts_q = (
        Post.query.filter_by(chapter_id=chapter_id)
        .order_by(Post.created_at.desc())
        .limit(12)
    )
    recent_posts = [
        {
            "post_id": p.post_id,
            "title": p.title,
            "type": p.type,
            "price": float(p.price) if p.price is not None else None,
            "created_at": p.created_at.isoformat(),
            "user_handle": p.user.handle if p.user else None,
            "image_url": p.images[0].url if p.images else None,
        }
        for p in recent_posts_q.all()
    ]

    memberships = UserChapterMembership.query.filter_by(chapter_id=chapter_id).all()
    user_ids = [m.user_id for m in memberships]
    users = User.query.filter(User.user_id.in_(user_ids)).all()
    user_by_id = {u.user_id: u for u in users}
    members = []
    for m in memberships:
        u = user_by_id.get(m.user_id)
        if not u:
            continue
        members.append({
            "user_id": u.user_id,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "handle": u.handle,
            "profile_picture_url": u.profile_picture_url,
            "role": m.role,
        })

    return jsonify({
        "chapter": {
            "chapter_id": chapter.chapter_id,
            "school_id": chapter.school_id,
            "name": chapter.name,
            "nickname": chapter.nickname,
            "type": chapter.type,
            "verified": bool(chapter.verified),
        },
        "is_member": is_member,
        "stats": {
            "members": member_count,
            "recent_posts": len(recent_posts),
        },
        "recent_posts": recent_posts,
        "members": members,
    }), 200


@bp.route("/chapters/<int:chapter_id>/join", methods=["POST"])
@jwt_required()
def join_chapter_by_id(chapter_id):
    """Join a chapter by id (canonical join endpoint)."""
    user_id = get_jwt_identity()
    chapter = Chapter.query.get(chapter_id)
    if not chapter:
        return jsonify({"error": "Chapter not found"}), 404

    existing = UserChapterMembership.query.filter_by(
        user_id=user_id, chapter_id=chapter_id
    ).first()
    if existing:
        return jsonify({"message": "Already a member"}), 200

    db.session.add(UserChapterMembership(user_id=user_id, chapter_id=chapter_id, role="member"))
    db.session.commit()
    return jsonify({"message": "Joined chapter!"}), 201


# -----------------------------------------------------------------------------
# Posts
# -----------------------------------------------------------------------------
@bp.route("/posts", methods=["POST"])
@jwt_required()
def create_post():
    """
    Create a post. User must have a school_id set.
    Accepts JSON body or multipart/form-data.
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    if not user.school_id:
        return jsonify({"error": "Please select your school before creating a post."}), 400

    # Accept JSON or form-data
    data = request.get_json(silent=True)
    if data is None:
        data = request.form.to_dict(flat=True)
        image_urls = request.form.getlist("image_urls[]")
    else:
        image_urls = data.get("image_urls", [])

    title = (data.get("title") or "").strip()
    ptype = (data.get("type") or "").strip()
    if not title:
        return jsonify({"error": "Title is required."}), 400
    if not ptype:
        return jsonify({"error": "Type is required."}), 400

    description = (data.get("description") or "").strip()
    visibility = (data.get("visibility") or "public").strip()
    chapter_id = data.get("chapter_id")

    raw_price = data.get("price")
    price = None
    if raw_price not in (None, ""):
        try:
            price = float(raw_price)
        except (TypeError, ValueError):
            return jsonify({"error": "Price must be a number."}), 400

    try:
        post = Post(
            user_id=user_id,
            school_id=user.school_id,  # not None now
            chapter_id=chapter_id,
            type=ptype,
            title=title,
            description=description,
            price=price,
            is_sold=False,
            visibility=visibility,
        )
        db.session.add(post)
        db.session.flush()  # allocates post_id

        for url in image_urls or []:
            if url:
                db.session.add(PostImage(post_id=post.post_id, url=url))

        db.session.commit()
        return jsonify(serialize_post(post)), 201
    except Exception as e:
        db.session.rollback()
        print("Create post error:", e)  # local debug
        return jsonify({"error": "Server error creating post"}), 500


@bp.route("/posts/<int:school_id>", methods=["GET"])
@jwt_required(optional=True)
def get_posts_for_school(school_id):
    viewer_id = get_jwt_identity()
    viewer = User.query.get(viewer_id) if viewer_id else None

    allowed_chapter_ids = []
    if viewer:
        allowed_chapter_ids = [
            m.chapter_id for m in UserChapterMembership.query.filter_by(user_id=viewer_id)
        ]

    q = Post.query.filter_by(school_id=school_id)
    q = q.filter(
        db.or_(
            Post.visibility == "public",
            db.and_(Post.visibility == "school", viewer and Post.school_id == viewer.school_id),
            db.and_(Post.visibility == "chapter", Post.chapter_id.in_(allowed_chapter_ids)),
        )
    )

    post_type = request.args.get("type")
    if post_type:
        q = q.filter_by(type=post_type)

    sort = request.args.get("sort")
    if sort == "price":
        q = q.order_by(Post.price.asc())
    elif sort == "-price":
        q = q.order_by(Post.price.desc())
    else:
        q = q.order_by(Post.created_at.desc())

    posts = q.all()
    result = []
    for p in posts:
        if viewer_id and is_blocked(viewer_id, p.user_id):
            continue
        item = serialize_post(p)
        item["user_handle"] = p.user.handle
        result.append(item)
    return jsonify(result)


@bp.route("/post/<int:post_id>", methods=["GET"])
@jwt_required(optional=True)
def get_post_detail(post_id):
    viewer_id = get_jwt_identity()
    post = Post.query.get(post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404

    if viewer_id and is_blocked(viewer_id, post.user_id):
        return jsonify({"error": "You are not allowed to view this post"}), 403

    post.views += 1
    db.session.commit()

    data = serialize_post(post)
    data["image_urls"] = [img.url for img in post.images]
    data["views"] = post.views
    data["user_handle"] = post.user.handle
    return jsonify(data)


@bp.route("/my-posts", methods=["GET"])
@jwt_required()
def get_my_posts():
    me = get_jwt_identity()
    posts = Post.query.filter_by(user_id=me).order_by(Post.created_at.desc()).all()
    return jsonify([{**serialize_post(p), "user_handle": p.user.handle} for p in posts])


@bp.route("/posts/<int:post_id>", methods=["PUT"])
@jwt_required()
def edit_post(post_id):
    me = get_jwt_identity()
    post = Post.query.get(post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404
    if post.user_id != int(me):
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json() or {}
    post.title = data.get("title", post.title)
    post.description = data.get("description", post.description)
    post.price = data.get("price", post.price)
    post.visibility = data.get("visibility", post.visibility)

    if "image_urls" in data:
        PostImage.query.filter_by(post_id=post_id).delete()
        for url in data["image_urls"]:
            db.session.add(PostImage(post_id=post_id, url=url))

    db.session.commit()
    return jsonify({"message": "Post updated successfully"}), 200


@bp.route("/posts/<int:post_id>/mark-sold", methods=["POST"])
@jwt_required()
def mark_post_sold(post_id):
    me = get_jwt_identity()
    post = Post.query.get(post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404
    if post.user_id != me:
        return jsonify({"error": "You can only mark your own posts as sold"}), 403
    post.is_sold = True
    db.session.commit()
    return jsonify({"message": "Post marked as SOLD!"}), 200


@bp.route("/posts/<int:post_id>/report", methods=["POST"])
@jwt_required()
def report_post(post_id):
    me = get_jwt_identity()
    data = request.get_json() or {}
    reason = (data.get("reason") or "").strip()
    if not reason:
        return jsonify({"error": "Report reason is required"}), 400

    post = Post.query.get(post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404

    report = PostReport(user_id=me, post_id=post_id, reason=reason)
    db.session.add(report)
    db.session.commit()
    return jsonify({"message": "Post reported successfully"}), 201


@bp.route("/posts/<int:post_id>/comment", methods=["POST"])
@jwt_required()
def add_comment(post_id):
    me = get_jwt_identity()
    data = request.get_json() or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Comment text is required"}), 400

    post = Post.query.get(post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404

    db.session.add(Comment(user_id=me, post_id=post_id, text=text))
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
            "created_at": c.created_at.isoformat(),
        } for c in comments
    ])


# Favorites
@bp.route("/posts/<int:post_id>/favorite", methods=["POST"])
@jwt_required()
def favorite_post(post_id):
    me = get_jwt_identity()
    post = Post.query.get(post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404

    existing = Favorite.query.filter_by(user_id=me, post_id=post_id).first()
    if existing:
        return jsonify({"message": "Already favorited"}), 200

    db.session.add(Favorite(user_id=me, post_id=post_id))
    db.session.commit()
    return jsonify({"message": "Post favorited!"}), 201


@bp.route("/posts/<int:post_id>/unfavorite", methods=["DELETE"])
@jwt_required()
def unfavorite_post(post_id):
    me = get_jwt_identity()
    fav = Favorite.query.filter_by(user_id=me, post_id=post_id).first()
    if not fav:
        return jsonify({"error": "Favorite not found"}), 404
    db.session.delete(fav)
    db.session.commit()
    return jsonify({"message": "Post unfavorited"}), 200


@bp.route("/my-favorites", methods=["GET"])
@jwt_required()
def get_my_favorites():
    me = get_jwt_identity()
    favorites = Favorite.query.filter_by(user_id=me).all()
    post_ids = [f.post_id for f in favorites]
    posts = Post.query.filter(Post.post_id.in_(post_ids)).all()
    visible = [p for p in posts if not is_blocked(me, p.user_id)]
    return jsonify([{**serialize_post(p), "user_handle": p.user.handle} for p in visible])


# Analytics (public post)
@bp.route("/analytics/post/<int:post_id>", methods=["GET"])
def get_post_analytics(post_id):
    post = Post.query.get(post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404

    view_count = post.views or 0
    comment_count = Comment.query.filter_by(post_id=post_id).count()
    image_count = PostImage.query.filter_by(post_id=post_id).count()
    return jsonify({"post_id": post_id, "views": view_count, "comments": comment_count, "images": image_count}), 200


# -----------------------------------------------------------------------------
# Activity feeds
# -----------------------------------------------------------------------------
@bp.route("/activity/posts", methods=["GET"])
@jwt_required(optional=True)
def recent_posts():
    viewer_id = get_jwt_identity()
    posts = Post.query.order_by(Post.created_at.desc()).limit(20).all()
    visible = [p for p in posts if not viewer_id or not is_blocked(viewer_id, p.user_id)]
    return jsonify([{**serialize_post(p), "user_handle": p.user.handle} for p in visible])


@bp.route("/activity/comments", methods=["GET"])
def recent_comments():
    comments = Comment.query.order_by(Comment.created_at.desc()).limit(20).all()
    return jsonify([
        {
            "comment_id": c.comment_id,
            "text": c.text,
            "post_id": c.post_id,
            "user_id": c.user_id,
            "created_at": c.created_at.isoformat(),
        } for c in comments
    ])


# -----------------------------------------------------------------------------
# Messaging
# -----------------------------------------------------------------------------
@bp.route("/messages/send", methods=["POST"])
@jwt_required()
def send_message():
    sender_id = get_jwt_identity()
    data = request.get_json() or {}

    recipient_id = data.get("recipient_id")
    text = (data.get("text") or "").strip()
    image_url = data.get("image_url")

    if not recipient_id or not text:
        return jsonify({"error": "Missing recipient_id or text"}), 400
    if is_blocked(sender_id, recipient_id):
        return jsonify({"error": "Cannot message this user"}), 403

    msg = Message(sender_id=sender_id, recipient_id=recipient_id, text=text, image_url=image_url)
    db.session.add(msg)
    db.session.commit()
    return jsonify({"message": "Message sent!"}), 201


@bp.route("/messages/conversation/<int:user_id>", methods=["GET"])
@jwt_required()
def get_conversation(user_id):
    me = get_jwt_identity()
    if is_blocked(me, user_id):
        return jsonify({"error": "You cannot view this conversation"}), 403

    messages = Message.query.filter(
        db.or_(
            db.and_(Message.sender_id == me, Message.recipient_id == user_id),
            db.and_(Message.sender_id == user_id, Message.recipient_id == me),
        )
    ).order_by(Message.sent_at.asc()).all()

    return jsonify([
        {
            "message_id": m.message_id,
            "sender_id": m.sender_id,
            "recipient_id": m.recipient_id,
            "text": m.text,
            "image_url": m.image_url,
            "sent_at": m.sent_at.isoformat(),
        } for m in messages
    ])


@bp.route("/messages/inbox", methods=["GET"])
@jwt_required()
def inbox():
    me = int(get_jwt_identity())

    pinned_users = {p.other_user_id for p in PinnedConversation.query.filter_by(user_id=me).all()}
    messages = Message.query.filter(
        db.or_(Message.sender_id == me, Message.recipient_id == me)
    ).order_by(Message.sent_at.desc()).all()

    conversations = {}
    for msg in messages:
        other = msg.recipient_id if msg.sender_id == me else msg.sender_id
        if is_blocked(me, other):
            continue

        key = tuple(sorted([me, other]))
        if key not in conversations:
            unread = Message.query.filter_by(sender_id=other, recipient_id=me, read=False).count()
            conversations[key] = {
                "user_id": other,
                "last_message": msg.text,
                "timestamp": msg.sent_at.isoformat(),
                "unread_count": unread,
                "pinned": other in pinned_users,
            }

    sorted_convos = sorted(
        conversations.values(),
        key=lambda c: (not c["pinned"], c["timestamp"]),
        reverse=True,
    )
    return jsonify(sorted_convos)


@bp.route("/messages/<int:with_user_id>/read", methods=["POST"])
@jwt_required()
def mark_messages_as_read(with_user_id):
    me = get_jwt_identity()
    messages = Message.query.filter_by(sender_id=with_user_id, recipient_id=me, read=False).all()
    for m in messages:
        m.read = True
    db.session.commit()
    return jsonify({"message": "Messages marked as read"}), 200


@bp.route("/messages/delete/<int:message_id>", methods=["DELETE"])
@jwt_required()
def delete_message(message_id):
    me = int(get_jwt_identity())
    message = Message.query.get(message_id)
    if not message:
        return jsonify({"error": "Message not found"}), 404
    if message.sender_id != me:
        return jsonify({"error": "You can only delete your own messages"}), 403
    db.session.delete(message)
    db.session.commit()
    return jsonify({"message": "Message deleted"}), 200


@bp.route("/messages/<int:message_id>/edit", methods=["PUT"])
@jwt_required()
def edit_message(message_id):
    me = get_jwt_identity()
    message = Message.query.get(message_id)
    if not message:
        return jsonify({"error": "Message not found"}), 404
    if message.sender_id != int(me):
        return jsonify({"error": "You can only edit your own messages"}), 403

    data = request.get_json() or {}
    new_text = (data.get("text") or "").strip()
    if not new_text:
        return jsonify({"error": "New message text required"}), 400

    message.text = new_text
    db.session.commit()
    return jsonify({"message": "Message updated"}), 200


@bp.route("/messages/unread-count", methods=["GET"])
@jwt_required()
def unread_message_count():
    me = get_jwt_identity()
    count = Message.query.filter_by(recipient_id=me, read=False).count()
    return jsonify({"unread_count": count}), 200


@bp.route("/messages/inbox/search", methods=["GET"])
@jwt_required()
def search_inbox():
    me = int(get_jwt_identity())
    q = (request.args.get("q") or "").strip().lower()
    if not q:
        return jsonify({"error": "Missing search query"}), 400

    messages = Message.query.filter(
        db.or_(Message.sender_id == me, Message.recipient_id == me)
    ).order_by(Message.sent_at.desc()).all()

    results, seen = [], set()
    for msg in messages:
        other = msg.recipient_id if msg.sender_id == me else msg.sender_id
        key = tuple(sorted([me, other]))
        if key in seen:
            continue

        other_user = User.query.get(other)
        match = (
            (q in (msg.text or "").lower())
            or (q in (other_user.first_name or "").lower())
            or (q in (other_user.last_name or "").lower())
            or (q in (other_user.handle or "").lower())
        )
        if match:
            seen.add(key)
            results.append({
                "user_id": other,
                "handle": other_user.handle,
                "last_message": msg.text,
                "timestamp": msg.sent_at.isoformat(),
                "unread": (not msg.read and msg.recipient_id == me),
            })
    return jsonify(results)


@bp.route("/messages/pin/<int:other_user_id>", methods=["POST"])
@jwt_required()
def pin_conversation(other_user_id):
    me = get_jwt_identity()
    if me == other_user_id:
        return jsonify({"error": "Cannot pin conversation with yourself"}), 400

    existing_count = PinnedConversation.query.filter_by(user_id=me).count()
    if existing_count >= 3:
        return jsonify({"error": "You can only pin up to 3 conversations"}), 403

    if PinnedConversation.query.filter_by(user_id=me, other_user_id=other_user_id).first():
        return jsonify({"message": "Already pinned"}), 200

    db.session.add(PinnedConversation(user_id=me, other_user_id=other_user_id))
    db.session.commit()
    return jsonify({"message": "Conversation pinned"}), 201


@bp.route("/messages/unpin/<int:other_user_id>", methods=["DELETE"])
@jwt_required()
def unpin_conversation(other_user_id):
    me = get_jwt_identity()
    pin = PinnedConversation.query.filter_by(user_id=me, other_user_id=other_user_id).first()
    if not pin:
        return jsonify({"error": "Pin not found"}), 404
    db.session.delete(pin)
    db.session.commit()
    return jsonify({"message": "Conversation unpinned"}), 200


# -----------------------------------------------------------------------------
# Users / Profiles / Lists
# -----------------------------------------------------------------------------
@bp.route("/user/<int:user_id>", methods=["GET"])
@jwt_required()
def get_user_profile(user_id):
    me = get_jwt_identity()
    if is_blocked(me, user_id):
        return jsonify({"error": "Access denied"}), 403
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(serialize_user(user))


@bp.route("/user/<int:user_id>/posts", methods=["GET"])
@jwt_required(optional=True)
def get_posts_by_user(user_id):
    viewer_id = get_jwt_identity()
    if viewer_id and is_blocked(viewer_id, user_id):
        return jsonify([])
    posts = Post.query.filter_by(user_id=user_id).order_by(Post.created_at.desc()).all()
    return jsonify([{**serialize_post(p), "user_handle": p.user.handle} for p in posts])

# =========================
# Schools – details & join
# =========================

# === School detail (with chapters & stats) ===
@bp.route("/schools/<int:school_id>", methods=["GET"])
@jwt_required(optional=True)
def get_school_detail(school_id):
    """
    Return a school's profile:
      - basic info
      - membership status for current user (if logged in)
      - chapter list (id, name, nickname, type, verified)
      - simple stats (members, chapters, recent posts count)
      - recent posts (lightweight)
    """
    user_id = get_jwt_identity()
    school = School.query.get(school_id)
    if not school:
        return jsonify({"error": "School not found"}), 404

    # membership for current user
    is_member = False
    if user_id:
        me = User.query.get(user_id)
        is_member = (me is not None and me.school_id == school_id)

    # stats
    member_count = User.query.filter_by(school_id=school_id).count()
    chapter_q = Chapter.query.filter_by(school_id=school_id).order_by(Chapter.name.asc())
    chapters = [
        {
            "chapter_id": c.chapter_id,
            "name": c.name,
            "nickname": c.nickname,
            "type": c.type,
            "verified": bool(c.verified),
        }
        for c in chapter_q.all()
    ]

    recent_posts_q = (
        Post.query.filter_by(school_id=school_id)
        .order_by(Post.created_at.desc())
        .limit(10)
    )
    recent_posts = [
        {
            "post_id": p.post_id,
            "title": p.title,
            "type": p.type,
            "price": float(p.price) if p.price is not None else None,
            "created_at": p.created_at.isoformat(),
            "user_handle": p.user.handle if p.user else None,
            "image_url": p.images[0].url if p.images else None,
        }
        for p in recent_posts_q.all()
    ]

    return jsonify({
        "school": {
            "school_id": school.school_id,
            "name": school.name,
            "domain": school.domain,
        },
        "is_member": is_member,
        "stats": {
            "members": member_count,
            "chapters": len(chapters),
            "recent_posts": len(recent_posts),
        },
        "chapters": chapters,
        "recent_posts": recent_posts,
    }), 200


@bp.route("/schools/<int:school_id>/join", methods=["POST"])
@jwt_required()
def join_school(school_id):
    """Set the current user's school if not already set."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    school = School.query.get(school_id)

    if not school:
        return jsonify({"error": "School not found"}), 404

    if user.school_id == school_id:
        return jsonify({"message": "Already a member of this school"}), 200

    user.school_id = school_id
    db.session.commit()
    return jsonify({"message": "Joined school", "school_id": school_id}), 200


# -----------------------------------------------------------------------------
# Admin
# -----------------------------------------------------------------------------
@bp.route("/admin/remove-user", methods=["POST"])
@jwt_required()
def admin_remove_user():
    admin_id = get_jwt_identity()
    data = request.get_json() or {}
    target_id = data.get("user_id")
    if not target_id:
        return jsonify({"error": "Missing user_id"}), 400

    admin_membership = UserChapterMembership.query.filter_by(user_id=admin_id, role="admin").first()
    if not admin_membership:
        return jsonify({"error": "Only chapter admins can remove users"}), 403

    membership = UserChapterMembership.query.filter_by(
        user_id=target_id, chapter_id=admin_membership.chapter_id
    ).first()
    if not membership:
        return jsonify({"error": "User not found in your chapter"}), 404

    db.session.delete(membership)
    db.session.commit()
    return jsonify({"message": "User removed from chapter"}), 200


@bp.route("/admin/delete-post/<int:post_id>", methods=["DELETE"])
@jwt_required()
def delete_post(post_id):
    me = get_jwt_identity()
    admin_membership = UserChapterMembership.query.filter_by(user_id=me, role="admin").first()
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
    me = get_jwt_identity()
    membership = UserChapterMembership.query.filter_by(user_id=me, role="admin").first()
    if not membership:
        return jsonify({"error": "Only chapter admins can view analytics"}), 403

    chapter_id = membership.chapter_id
    total_posts = Post.query.filter_by(chapter_id=chapter_id).count()
    total_users = UserChapterMembership.query.filter_by(chapter_id=chapter_id).count()
    total_comments = db.session.query(Comment).join(Post).filter(Post.chapter_id == chapter_id).count()

    return jsonify({
        "chapter_id": chapter_id,
        "total_posts": total_posts,
        "total_users": total_users,
        "total_comments": total_comments,
    }), 200


@bp.route("/admin/analytics/platform", methods=["GET"])
@jwt_required()
def get_platform_analytics():
    me = get_jwt_identity()
    admin = UserChapterMembership.query.filter_by(user_id=me, role="admin").first()
    if not admin:
        return jsonify({"error": "Only chapter admins can view analytics"}), 403

    return jsonify({
        "total_users": User.query.count(),
        "total_posts": Post.query.count(),
        "total_comments": Comment.query.count(),
        "total_chapters": Chapter.query.count(),
    })


# -----------------------------------------------------------------------------
# Media / Uploads
# -----------------------------------------------------------------------------
@bp.route("/upload-image", methods=["POST"])
@jwt_required()
def upload_image():
    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    image_file = request.files["image"]
    if image_file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    try:
        upload_result = cloudinary.uploader.upload(
            image_file,
            folder="greekmarket/posts",
            overwrite=True,
            resource_type="image",
        )
        return jsonify({"url": upload_result["secure_url"]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -----------------------------------------------------------------------------
# Stripe / Payments
# -----------------------------------------------------------------------------
@bp.route("/create-checkout-session", methods=["POST"])
@jwt_required()
def create_checkout_session():
    data = request.get_json() or {}
    post_id = data.get("post_id")
    price = data.get("price")
    post_title = data.get("title")

    me = get_jwt_identity()
    user = User.query.get(me)

    if not user or not user.stripe_account_id:
        return jsonify({"error": "User must have a Stripe recipient account connected."}), 400

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": post_title},
                    "unit_amount": int(float(price) * 100),
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=os.getenv("FRONTEND_URL") + "/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=os.getenv("FRONTEND_URL") + "/cancel",
            metadata={"post_id": post_id, "buyer_id": me},
        )
        return jsonify({"checkout_url": session.url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/create-account-link", methods=["POST"])
@jwt_required()
def create_account_link():
    me = get_jwt_identity()
    user = User.query.get(me)
    if not user:
        return jsonify({"error": "User not found"}), 404

    if not user.stripe_account_id:
        account = stripe.Account.create(type="express")
        user.stripe_account_id = account.id
        db.session.commit()
    else:
        account = stripe.Account.retrieve(user.stripe_account_id)

    link = stripe.AccountLink.create(
        account=account.id,
        refresh_url=os.getenv("FRONTEND_URL") + "/reauth",
        return_url=os.getenv("FRONTEND_URL") + "/account",
        type="account_onboarding",
    )
    return jsonify({"url": link.url})


@bp.route("/webhook", methods=["POST"])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError:
        return jsonify({"error": "Invalid payload"}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({"error": "Invalid signature"}), 400

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        meta = session.get("metadata", {})
        post_id = meta.get("post_id")
        buyer_id = meta.get("buyer_id")

        if post_id and buyer_id:
            existing = Purchase.query.filter_by(post_id=post_id, buyer_id=buyer_id).first()
            if not existing:
                purchase = Purchase(post_id=post_id, buyer_id=buyer_id)
                db.session.add(purchase)

                post = Post.query.get(post_id)
                if post:
                    post.is_sold = True

                db.session.commit()

    return jsonify({"status": "success"}), 200


@bp.route("/my-purchases", methods=["GET"])
@jwt_required()
def get_my_purchases():
    me = get_jwt_identity()
    purchases = Purchase.query.filter_by(buyer_id=me).order_by(Purchase.purchased_at.desc()).all()
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
                "handle": seller.handle,
            },
        })
    return jsonify(results), 200
