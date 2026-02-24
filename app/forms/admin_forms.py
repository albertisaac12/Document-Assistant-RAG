from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField

class RoleChangeForm(FlaskForm):
    role = SelectField('Role', choices=[('user', 'User'), ('admin', 'Admin')])
    submit = SubmitField('Save')
