from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from app.extensions import db, oauth
from app.models.user import User
from app.forms.auth_forms import LoginForm, RegisterForm

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    return redirect(url_for('chat.index'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('chat.index'))
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(name=form.name.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('chat.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(url_for('chat.index'))
        else:
            flash('Invalid email or password.', 'danger')
            return redirect(url_for('auth.login'))
    return render_template('auth/login.html', form=form)

@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

# Google OAuth Setup
import os

google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID', 'fallback'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET', 'fallback'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

# Remember to initialize oauth in app factory or extensions. We will init it when blueprint registers or just let authlib figure it out. Wait, better to init in extensions.py.

@auth_bp.route('/auth/google')
def google_auth():
    redirect_uri = url_for('auth.google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@auth_bp.route('/login/google/authorized')
def google_callback():
    token = google.authorize_access_token()
    user_info = token.get('userinfo')
    
    if not user_info:
        flash('Failed to retrieve user info from Google.', 'danger')
        return redirect(url_for('auth.login'))
        
    email = user_info['email']
    name = user_info.get('name', '')
    google_id = user_info['sub']
    avatar_url = user_info.get('picture')

    user = User.query.filter_by(email=email).first()
    if user:
        if not user.google_id:
            user.google_id = google_id
            user.avatar_url = avatar_url
            db.session.commit()
    else:
        user = User(
            name=name,
            email=email,
            google_id=google_id,
            avatar_url=avatar_url,
            role='user'
        )
        db.session.add(user)
        db.session.commit()

    login_user(user)
    return redirect(url_for('chat.index'))
