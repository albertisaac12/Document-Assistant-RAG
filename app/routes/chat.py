from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models.document import Document
from app.models.conversation import Conversation, ChatMessage
from app.services.rag_service import query_documents

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/', methods=['GET'])
@login_required
def index():
    if not current_user.has_api_key():
        flash("Please add your Gemini API key in Settings first.", "warning")
        return redirect(url_for('profile.settings'))

    conversation_id = request.args.get('conversation_id', type=int)
    
    if conversation_id:
        conversation = Conversation.query.get_or_404(conversation_id)
        if conversation.user_id != current_user.id:
            flash("You don't have permission to access that conversation.", "danger")
            return redirect(url_for('chat.index'))
            
        all_conversations = Conversation.query.filter_by(user_id=current_user.id).order_by(Conversation.created_at.desc()).all()
        # To show names of queried documents
        queried_docs = Document.query.filter(Document.id.in_(conversation.document_ids)).all()
        doc_names = ", ".join([d.original_filename for d in queried_docs])
        
        return render_template('chat/index.html', 
                               active_conversation=conversation, 
                               all_conversations=all_conversations,
                               doc_names=doc_names)
                               
    # If no conversation_id, show document selection
    global_docs = Document.query.filter_by(is_global=True, status='ready', is_active=True).all()
    my_docs = Document.query.filter_by(owner_id=current_user.id, status='ready', is_active=True).all()
    
    return render_template('chat/index.html', 
                            global_docs=global_docs, 
                            my_docs=my_docs,
                            active_conversation=None)

@chat_bp.route('/start', methods=['POST'])
@login_required
def start():
    if not current_user.has_api_key():
        return redirect(url_for('profile.settings'))
        
    selected_ids = request.form.getlist('document_ids')
    if not selected_ids:
        flash("Please select at least one document to query.", "warning")
        return redirect(url_for('chat.index'))
        
    doc_ids = [int(i) for i in selected_ids]
    
    # Verify user has access to these documents
    docs = Document.query.filter(Document.id.in_(doc_ids)).all()
    for doc in docs:
        if not doc.is_global and doc.owner_id != current_user.id:
            flash("You selected a document you don't have access to.", "danger")
            return redirect(url_for('chat.index'))
            
    title = docs[0].original_filename if docs else "New Chat"
    
    conversation = Conversation(
        user_id=current_user.id,
        document_ids=doc_ids,
        title=title
    )
    db.session.add(conversation)
    db.session.commit()
    
    return redirect(url_for('chat.index', conversation_id=conversation.id))

@chat_bp.route('/message', methods=['POST'])
@login_required
def message():
    conversation_id = request.form.get('conversation_id', type=int)
    content = request.form.get('content', '').strip()
    
    if not conversation_id or not content:
        flash("Message cannot be empty.", "warning")
        if conversation_id:
            return redirect(url_for('chat.index', conversation_id=conversation_id))
        return redirect(url_for('chat.index'))
        
    conversation = Conversation.query.get_or_404(conversation_id)
    if conversation.user_id != current_user.id:
        flash("Unauthorized action.", "danger")
        return redirect(url_for('chat.index'))

    # Save user message
    user_msg = ChatMessage(
        conversation_id=conversation.id,
        role='user',
        content=content
    )
    db.session.add(user_msg)
    db.session.commit()
    
    history = [msg.to_dict() for msg in conversation.messages[:-1]] # Exclude the one just added
    
    try:
        answer, sources = query_documents(
            content, 
            conversation.document_ids, 
            history, 
            current_user.gemini_api_key
        )
        
        bot_msg = ChatMessage(
            conversation_id=conversation.id,
            role='assistant',
            content=answer,
            sources=list(sources)
        )
        db.session.add(bot_msg)
        db.session.commit()
    except Exception as e:
        print(f">>>> ERROR IN CHAT MESSAGE: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f"Error querying Gemini/Pinecone: {str(e)}", "danger")
        
    return redirect(url_for('chat.index', conversation_id=conversation.id))

from flask import Response
import json

@chat_bp.route('/stream', methods=['POST'])
@login_required
def stream():
    conversation_id = request.form.get('conversation_id', type=int)
    content = request.form.get('content', '').strip()
    
    if not conversation_id or not content:
        return {"error": "Missing parameters"}, 400
        
    conversation = Conversation.query.get_or_404(conversation_id)
    if conversation.user_id != current_user.id:
        return {"error": "Unauthorized"}, 403

    # Save user message immediately
    user_msg = ChatMessage(
        conversation_id=conversation.id,
        role='user',
        content=content
    )
    db.session.add(user_msg)
    db.session.commit()
    
    history = [msg.to_dict() for msg in conversation.messages[:-1]]

    # Extract api key before generator starts (since generator loses request context in some WSGI servers)
    api_key = current_user.gemini_api_key
    user_id = current_user.id
    from flask import current_app, copy_current_request_context
    app_context = current_app.app_context()
    
    @copy_current_request_context
    def generate():
        with app_context:
            full_answer = ""
            final_sources = []
            try:
                from app.services.rag_service import query_documents_stream
                
                for chunk_content, sources in query_documents_stream(
                    content, 
                    conversation.document_ids, 
                    history, 
                    api_key
                ):
                    final_sources = sources
                    if chunk_content:
                        full_answer += chunk_content
                        # Send SSE payload
                        yield f"data: {json.dumps({'chunk': chunk_content})}\n\n"
                
                # Save the final bot message to DB once stream finishes
                bot_msg = ChatMessage(
                    conversation_id=conversation.id,
                    role='assistant',
                    content=full_answer,
                    sources=list(final_sources)
                )
                db.session.add(bot_msg)
                db.session.commit()
                
                yield f"data: {json.dumps({'sources': list(final_sources), 'done': True})}\n\n"
                
            except Exception as e:
                print(f">>>> ERROR IN CHAT STREAM: {str(e)}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(generate(), mimetype='text/event-stream')

@chat_bp.route('/new', methods=['POST'])
@login_required
def new():
    return redirect(url_for('chat.index'))

@chat_bp.route('/delete/<int:conversation_id>', methods=['POST'])
@login_required
def delete(conversation_id):
    conversation = Conversation.query.get_or_404(conversation_id)
    if conversation.user_id != current_user.id:
        flash("Unauthorized action.", "danger")
        return redirect(url_for('chat.index'))
    
    # Delete associated messages manually because cascade is not set up
    ChatMessage.query.filter_by(conversation_id=conversation.id).delete()
    
    db.session.delete(conversation)
    db.session.commit()
    flash("Conversation deleted.", "success")
    
    active_conversation_id = request.form.get('active_conversation_id', type=int)
    
    # If the user deleted a background conversation in the sidebar, keep them on their active chat
    if active_conversation_id and active_conversation_id != conversation_id:
        return redirect(url_for('chat.index', conversation_id=active_conversation_id))
        
    # Otherwise, if they deleted the active chat, try loading the next most recent chat
    next_conv = Conversation.query.filter_by(user_id=current_user.id).order_by(Conversation.created_at.desc()).first()
    if next_conv:
        return redirect(url_for('chat.index', conversation_id=next_conv.id))
        
    return redirect(url_for('chat.index'))
