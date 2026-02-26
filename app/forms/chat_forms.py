from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import Optional

class ApiKeyForm(FlaskForm):
    gemini_api_key = PasswordField('Gemini API Key', validators=[Optional()])
    pinecone_api_key = PasswordField('Pinecone API Key', validators=[Optional()])
    pinecone_index_name = StringField('Pinecone Index Name', validators=[Optional()])
    submit = SubmitField('Save Settings')
