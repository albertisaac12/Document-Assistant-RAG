from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from app.extensions import db
from app.models.user import User
from app.forms.admin_forms import RoleChangeForm

admin_bp = Blueprint('admin', __name__)

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if current_user.role not in roles:
                flash('You do not have permission to access that area.', 'danger')
                return redirect(url_for('chat.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@admin_bp.route('/users', methods=['GET'])
@login_required
@role_required('admin')
def users():
    page = request.args.get('page', 1, type=int)
    pagination = User.query.order_by(User.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    
    view_forms = {}
    for user in pagination.items:
        form = RoleChangeForm(role=user.role)
        view_forms[user.id] = form
        
    return render_template('admin/users.html', 
                            pagination=pagination,
                            view_forms=view_forms)

@admin_bp.route('/users/<int:id>/role', methods=['POST'])
@login_required
@role_required('admin')
def change_role(id):
    if id == current_user.id:
        flash("You cannot change your own role.", "warning")
        return redirect(url_for('admin.users'))
        
    user = User.query.get_or_404(id)
    form = RoleChangeForm()
    
    if form.validate_on_submit():
        user.role = form.role.data
        db.session.commit()
        flash(f"Role updated for {user.email}.", "success")
    else:
        flash("Invalid role selection.", "danger")
        
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/<int:id>/disable', methods=['POST'])
@login_required
@role_required('admin')
def toggle_status(id):
    if id == current_user.id:
        flash("You cannot disable your own account.", "warning")
        return redirect(url_for('admin.users'))
        
    user = User.query.get_or_404(id)
    # Simple formless POST just toggles it
    user.is_active = not user.is_active
    db.session.commit()
    
    status_str = "enabled" if user.is_active else "disabled"
    flash(f"User {user.email} has been {status_str}.", "success")
    return redirect(url_for('admin.users'))
