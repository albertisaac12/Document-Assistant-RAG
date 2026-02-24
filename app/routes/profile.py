from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.forms.chat_forms import ApiKeyForm

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    form = ApiKeyForm()
    if form.validate_on_submit():
        current_user.gemini_api_key = form.gemini_api_key.data.strip()
        db.session.commit()
        flash('API key saved successfully.', 'success')
        return redirect(url_for('profile.settings'))
        
    return render_template('profile/settings.html', form=form)

@profile_bp.route('/settings/key/delete', methods=['POST'])
@login_required
def delete_key():
    current_user.gemini_api_key = None
    db.session.commit()
    flash('API key removed successfully.', 'success')
    return redirect(url_for('profile.settings'))
