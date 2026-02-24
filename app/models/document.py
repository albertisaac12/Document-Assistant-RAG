from app.extensions import db
from datetime import datetime

class Document(db.Model):
    __tablename__ = 'documents'
    id = db.Column(db.Integer, primary_key=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(20), default='processing')
    
    # owner_id is NULL for admin-uploaded global documents
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_global = db.Column(db.Boolean, default=False)
    chunk_count = db.Column(db.Integer, default=0)
    pinecone_namespace = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.id,
            'original_filename': self.original_filename,
            'status': self.status,
            'is_global': self.is_global,
            'chunk_count': self.chunk_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active
        }
