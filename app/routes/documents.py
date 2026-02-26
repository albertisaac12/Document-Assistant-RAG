from flask import Blueprint, render_template, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import uuid
from app.extensions import db
from app.models.document import Document
from app.forms.document_forms import UploadDocumentForm
from app.services.rag_service import ingest_document, delete_document_vectors

documents_bp = Blueprint('documents', __name__)

@documents_bp.route('/', methods=['GET'])
@login_required
def manage():
    form = UploadDocumentForm()
    
    my_documents = Document.query.filter_by(owner_id=current_user.id, is_active=True).order_by(Document.created_at.desc()).all()
    global_documents = []
    
    if current_user.role == 'admin':
        global_documents = Document.query.filter_by(is_global=True, is_active=True).order_by(Document.created_at.desc()).all()
        
    return render_template('documents/manage.html', 
                            form=form, 
                            my_documents=my_documents, 
                            global_documents=global_documents)

@documents_bp.route('/upload', methods=['POST'])
@login_required
def upload():
    form = UploadDocumentForm()
    if form.validate_on_submit():
        if not current_user.has_api_key() or not current_user.has_pinecone_configured():
            flash("You need Gemini and Pinecone API keys configured to upload and process documents. Add your keys in Settings.", "warning")
            return redirect(url_for('profile.settings'))

        file = form.document.data
        original_filename = secure_filename(file.filename)
        ext = original_filename.rsplit('.', 1)[1].lower()
        
        stored_filename = f"{uuid.uuid4().hex}.{ext}"
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], stored_filename)
        file.save(file_path)

        is_global = form.is_global.data
        
        doc = Document(
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_path=file_path,
            status='processing',
            owner_id=None if is_global else current_user.id,
            is_global=is_global,
            pinecone_namespace=None
        )
        db.session.add(doc)
        db.session.commit()
        
        doc.pinecone_namespace = str(doc.id)
        db.session.commit()

        try:
            chunks_created = ingest_document(
                file_path, 
                doc.id, 
                ext, 
                current_user.gemini_api_key, 
                current_user.pinecone_api_key, 
                current_user.pinecone_index_name
            )
            doc.status = 'ready'
            doc.chunk_count = chunks_created
        except Exception as e:
            doc.status = 'failed'
            flash(f"Error processing document: {str(e)}", "danger")

        db.session.commit()
        if doc.status == 'ready':
            flash("Document uploaded and processed successfully.", "success")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(error, "danger")
            
    return redirect(url_for('documents.manage'))

@documents_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    doc = Document.query.get_or_404(id)
    
    if doc.owner_id != current_user.id and current_user.role != 'admin':
        flash('You do not have permission to delete this document.', 'danger')
        return redirect(url_for('documents.manage'))
        
    try:
        delete_document_vectors(doc.id, current_user.pinecone_api_key, current_user.pinecone_index_name)
    except Exception as e:
        print(f"Pinecone delete failed: {e}")
        
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)
        
    doc.is_active = False
    db.session.commit()
    
    flash('Document deleted successfully.', 'success')
    return redirect(url_for('documents.manage'))
