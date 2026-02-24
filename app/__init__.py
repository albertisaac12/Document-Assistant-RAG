from flask import Flask
from app.config import Config
from app.extensions import db, migrate, login_manager, csrf, oauth

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Flask extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    oauth.init_app(app)
    
    from app import models  # Register models with SQLAlchemy

    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return User.query.get(int(user_id))

    # Create upload directory if it doesn't exist
    import os
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Configure login_manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'warning'

    # Register blueprints (to correctly import logic later)
    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp)
    
    from app.routes.profile import profile_bp
    app.register_blueprint(profile_bp, url_prefix='/profile')

    from app.routes.documents import documents_bp
    app.register_blueprint(documents_bp, url_prefix='/documents')

    from app.routes.chat import chat_bp
    app.register_blueprint(chat_bp, url_prefix='/chat')

    from app.routes.admin import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Error handlers
    @app.errorhandler(403)
    def forbidden(error):
        from flask import render_template
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(error):
        from flask import render_template
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        from flask import render_template
        return render_template('errors/500.html'), 500

    return app
