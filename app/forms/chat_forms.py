from flask_wtf import FlaskForm
from wtforms import PasswordField, SubmitField
from wtforms.validators import DataRequired

class ApiKeyForm(FlaskForm):
    gemini_api_key = PasswordField('Gemini API Key', validators=[DataRequired()])
    submit = SubmitField('Save API Key')
