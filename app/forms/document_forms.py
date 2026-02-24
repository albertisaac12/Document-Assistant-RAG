from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import SubmitField, BooleanField

class UploadDocumentForm(FlaskForm):
    document = FileField('Select Document (PDF, TXT, DOCX - max 10MB)', validators=[
        FileRequired(),
        FileAllowed(['pdf', 'txt', 'docx'], 'Only PDF, TXT, and DOCX files are allowed.')
    ])
    is_global = BooleanField('Make this document Global (visible to everyone)')
    submit = SubmitField('Upload Document')
