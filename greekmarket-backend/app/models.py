from . import db
from datetime import datetime

class School(db.Model):
    __tablename__ = 'schools'
    school_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    domain = db.Column(db.String(255), unique=True, nullable=False)
    users = db.relationship('User', backref='school', lazy=True)
    chapters = db.relationship('Chapter', backref='school', lazy=True)
    posts = db.relationship('Post', backref='school', lazy=True)

class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    profile_picture_url = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.school_id'), nullable=True)
    memberships = db.relationship('UserChapterMembership', backref='user', lazy=True)
    posts = db.relationship('Post', backref='user', lazy=True)
    comments = db.relationship('Comment', backref='user', lazy=True)
    favorites = db.relationship('Favorite', backref='user', lazy=True)
    handle = db.Column(db.String(50), unique=True, nullable=False)
    stripe_account_id = db.Column(db.String(128), nullable=True)

class Chapter(db.Model):
    __tablename__ = 'chapters'
    chapter_id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.school_id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    nickname = db.Column(db.String(50))
    type = db.Column(db.String(20), nullable=False)
    verified = db.Column(db.Boolean, default=False)
    profile_picture_url = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    memberships = db.relationship('UserChapterMembership', backref='chapter', lazy=True)
    posts = db.relationship('Post', backref='chapter', lazy=True)

class UserChapterMembership(db.Model):
    __tablename__ = 'user_chapter_memberships'
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), primary_key=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapters.chapter_id'), primary_key=True)
    role = db.Column(db.String(20), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

class Post(db.Model):
    __tablename__ = 'posts'
    post_id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapters.chapter_id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.school_id'), nullable=False)
    type = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2))
    views = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    comments = db.relationship('Comment', backref='post', lazy=True)
    images = db.relationship('PostImage', backref='post', cascade="all, delete-orphan", lazy=True)
    favorites = db.relationship('Favorite', backref='post', lazy=True)
    is_sold = db.Column(db.Boolean, default=False)
    visibility = db.Column(db.String(20), nullable=False, default="public")

class PostImage(db.Model):
    __tablename__ = 'post_images'
    image_id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.post_id'), nullable=False)
    url = db.Column(db.Text, nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

class Comment(db.Model):
    __tablename__ = 'comments'
    comment_id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.post_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Favorite(db.Model):
    __tablename__ = 'favorites'
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.post_id'), primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Message(db.Model):
    __tablename__ = 'messages'
    message_id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.Text)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages', lazy=True)
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_messages', lazy=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)

class PinnedConversation(db.Model):
    __tablename__ = 'pinned_conversations'
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), primary_key=True)
    other_user_id = db.Column(db.Integer, primary_key=True)
    pinned_at = db.Column(db.DateTime, default=datetime.utcnow)

class PostReport(db.Model):
    __tablename__ = 'post_reports'
    report_id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.post_id'), nullable=False)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    reason = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    post = db.relationship("Post", backref="reports")
    reporter = db.relationship("User", backref="post_reports")

class UserReport(db.Model):
    __tablename__ = "user_reports"
    report_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)  # who is reporting
    reported_user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)  # who is being reported
    reason = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reporter = db.relationship("User", foreign_keys=[user_id], backref="user_reports_made")
    reported_user = db.relationship("User", foreign_keys=[reported_user_id], backref="user_reports_received")

class BlockedUser(db.Model):
    __tablename__ = "blocked_users"
    block_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)  # The blocker
    blocked_user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)  # The one being blocked
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "blocked_user_id", name="uq_blocked_pair"),
    )

class Purchase(db.Model):
    __tablename__ = 'purchases'

    purchase_id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.post_id'), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    stripe_session_id = db.Column(db.String(255), unique=True, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    purchased_at = db.Column(db.DateTime, default=datetime.utcnow)

    post = db.relationship("Post", backref="purchases", lazy=True)
    buyer = db.relationship("User", backref="purchases", lazy=True)
