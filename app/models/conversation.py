from app.extensions import db
from datetime import datetime

class Conversation(db.Model):
    __tablename__ = 'conversations'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # JSON list of document IDs this conversation is querying
    document_ids = db.Column(db.JSON, nullable=False, default=list)
    title = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    messages = db.relationship('ChatMessage', backref='conversation',
                                lazy=True, order_by='ChatMessage.created_at')
                                
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'document_ids': self.document_ids,
            'title': self.title,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer,
                                 db.ForeignKey('conversations.id'),
                                 nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    sources = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'role': self.role,
            'content': self.content,
            'sources': self.sources,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
