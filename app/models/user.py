from app.extensions import db
from flask_login import UserMixin
from datetime import datetime

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    google_id = db.Column(db.String(255), unique=True, nullable=True)
    avatar_url = db.Column(db.String(500), nullable=True)
    role = db.Column(db.String(20), default='user', nullable=False)
    
    # User's own Gemini API key — stored as plain text for dev purposes
    gemini_api_key = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    documents = db.relationship('Document', backref='owner', lazy=True)
    conversations = db.relationship('Conversation', backref='user', lazy=True)

    def set_password(self, password):
        import bcrypt
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def check_password(self, password):
        if not self.password_hash:
            return False
        import bcrypt
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

    def has_api_key(self):
        return bool(self.gemini_api_key)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'has_api_key': self.has_api_key(),
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
