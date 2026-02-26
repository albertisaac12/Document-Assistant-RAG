import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key')
    
    # Enable Azure-specific overrides for persistence
    # Azure App Service sets 'WEBSITE_SITE_NAME' automatically
    if os.environ.get('WEBSITE_SITE_NAME'):
        # Persist database in /home folder mapped to blob storage
        SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:////home/document_chatbot.db')
        UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', '/home/uploads')
    else:
        # Standard local deployment
        SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///document_chatbot.db')
        UPLOAD_FOLDER = os.environ.get(
            'UPLOAD_FOLDER', 
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
        )
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
    }
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=60)
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'pdf', 'txt', 'docx'}
