import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///document_chatbot.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
    }
    DEBUG = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=60)
    UPLOAD_FOLDER = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 'uploads'
    )
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'pdf', 'txt', 'docx'}
