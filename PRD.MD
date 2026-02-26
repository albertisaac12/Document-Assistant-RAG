Build a full-stack Document Q&A Chatbot web application.
Users upload documents, enter their Gemini API key, and chat with
their documents. Read every requirement carefully before writing any code.

---

## WHAT IT DOES
- User registers/logs in
- User enters their Gemini API key (saved to their profile)
- Admin uploads documents that all users can query
- Users can also upload their own private documents
- User opens chat, selects which document(s) to query
- User asks questions in natural language
- App retrieves relevant chunks from the document via Pinecone
- Gemini answers the question based on document content only
- Full conversation history is saved per session

---

## STACK
- Backend: Python + Flask
- Frontend: Jinja2 templates + Bootstrap 5 (CDN) + Vanilla JS + Web3 Dark Mode Theme (Polygon inspired)
- RAG Pipeline: LangChain + local FAISS
- LLM: Google Gemini (gemini-2.5-flash) with Server-Sent Events (SSE) Streaming — using USER'S OWN API key
- Embeddings: HuggingFace local embeddings (all-MiniLM-L6-v2)
- Database: SQLite via SQLAlchemy (file-based, zero setup)
- Auth: Flask-Login + Google OAuth via Authlib
- Security: Flask-WTF (CSRF), bcrypt, secure sessions

---

## PROJECT STRUCTURE

document_chatbot/
├── app/
│   ├── __init__.py
│   ├── extensions.py
│   ├── config.py
│   ├── models/
│   │   ├── user.py
│   │   ├── document.py
│   │   └── conversation.py
│   ├── routes/
│   │   ├── auth.py
│   │   ├── chat.py
│   │   ├── documents.py
│   │   └── admin.py
│   ├── services/
│   │   └── rag_service.py
│   ├── forms/
│   │   ├── auth_forms.py
│   │   ├── document_forms.py
│   │   ├── chat_forms.py
│   │   └── admin_forms.py
│   ├── templates/
│   │   ├── base.html
│   │   ├── auth/
│   │   │   ├── login.html
│   │   │   └── register.html
│   │   ├── chat/
│   │   │   └── index.html
│   │   ├── documents/
│   │   │   └── manage.html
│   │   ├── profile/
│   │   │   └── settings.html
│   │   ├── admin/
│   │   │   └── users.html
│   │   └── errors/
│   │       ├── 403.html
│   │       ├── 404.html
│   │       └── 500.html
│   └── static/
│       ├── css/
│       │   └── main.css
│       └── js/
│           └── chat.js
├── uploads/
├── migrations/
├── scripts/
│   └── create_pinecone_index.py
├── .env
├── requirements.txt
└── run.py

---

## ENVIRONMENT & SETUP RULES (CRITICAL — FOLLOW EXACTLY)

1. ALWAYS activate the virtual environment before installing anything:
   python -m venv venv
   source venv/bin/activate     # Linux/Mac
   venv\Scripts\activate        # Windows

2. Then install (inside venv only):
   pip install flask flask-sqlalchemy flask-login flask-wtf \
   flask-migrate authlib python-dotenv langchain langchain-google-genai \
   langchain-pinecone pinecone-client google-generativeai \
   bcrypt flask-cors gunicorn

3. NEVER run pip install outside the venv.
4. After all installs: pip freeze > requirements.txt
5. All secrets go in .env via python-dotenv. Never hardcode anything.

---

## DATABASE CONFIGURATION (config.py)

import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///document_chatbot.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
    }
    DEBUG = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=60)
    UPLOAD_FOLDER = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 'uploads'
    )
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'pdf', 'txt', 'docx'}

---

## .env FILE

FLASK_SECRET_KEY=your-secret-key-change-this
FLASK_ENV=development

# Pinecone (from pinecone.io)
PINECONE_API_KEY=
PINECONE_INDEX_NAME=document-chatbot

# Google OAuth (from console.cloud.google.com)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:5000/auth/google/callback

# Note: NO Gemini API key here — each user provides their own

---

## AUTHENTICATION & SECURITY

### Registration & Login
- Register: name, email, password (bcrypt hashed), default role = 'user'
- Login: email + password verification
- Google OAuth: "Sign in with Google" on login page
  - First login: auto-create user, role = 'user'
  - Subsequent logins: find by google_id and log in
  - After callback: redirect to /chat
- After any login: redirect to /chat

### Session Management
- Flask-Login handles sessions
- login_manager.login_view = 'auth.login'
- login_manager.login_message_category = 'warning'

### CSRF Protection
- Flask-WTF CSRFProtect in extensions.py
- Every form must include: {{ form.hidden_tag() }}
- Use FlaskForm base class for all forms

### Roles & Authorization
- Roles: 'user', 'admin'
- role_required(*roles) decorator:

  from functools import wraps
  from flask import flash, redirect, url_for
  from flask_login import current_user

  def role_required(*roles):
      def decorator(f):
          @wraps(f)
          def decorated_function(*args, **kwargs):
              if not current_user.is_authenticated:
                  return redirect(url_for('auth.login'))
              if current_user.role not in roles:
                  flash('You do not have permission.', 'danger')
                  return redirect(url_for('chat.index'))
              return f(*args, **kwargs)
          return decorated_function
      return decorator

---

## DATABASE MODELS

### User (app/models/user.py)
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    google_id = db.Column(db.String(255), unique=True, nullable=True)
    avatar_url = db.Column(db.String(500), nullable=True)
    role = db.Column(db.String(20), default='user', nullable=False)
    # User's own Gemini API key — stored as plain text for dev purposes
    gemini_api_key = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    documents = db.relationship('Document', backref='owner', lazy=True)
    conversations = db.relationship('Conversation', backref='user', lazy=True)

    def set_password(self, password): ...
    def check_password(self, password): ...
    def has_api_key(self): return bool(self.gemini_api_key)
    def to_dict(self): ...

### Document (app/models/document.py)
class Document(db.Model):
    __tablename__ = 'documents'
    id = db.Column(db.Integer, primary_key=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(20), default='processing')
    # owner_id is NULL for global documents
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_global = db.Column(db.Boolean, default=False) # Configurable by ALL users upon upload
    chunk_count = db.Column(db.Integer, default=0)
    pinecone_namespace = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    def to_dict(self): ...

### Conversation + ChatMessage (app/models/conversation.py)
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
    def to_dict(self): ...

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
    def to_dict(self): ...

---

## API KEY SETTINGS PAGE (/profile/settings)

GET /profile/settings:
- Render profile/settings.html
- Show current API key masked: "sk-...xxxx" or "Not set"

POST /profile/settings:
- Accept gemini_api_key from form
- Validate: not empty, strip whitespace
- Save to current_user.gemini_api_key
- flash("API key saved successfully.", "success")
- Redirect to GET /profile/settings

settings.html:
- Simple Bootstrap card: "Your Gemini API Key"
- Input field (type=password so key is hidden while typing)
- Show masked current key if already set
- Save button + CSRF
- Info text: "Get your free API key at aistudio.google.com"
- Link to aistudio.google.com (opens in new tab)
- Warning: "Your API key is used only to power your chat sessions."

### API Key Guard
Before any chat request, check if current_user.has_api_key():
- If no key: flash("Please add your Gemini API key in Settings first.", "warning")
- Redirect to /profile/settings

---

## RAG SERVICE (app/services/rag_service.py)

IMPORTANT: All functions that call Gemini accept api_key as a parameter.
The API key comes from current_user.gemini_api_key at the route level
and is passed into the service. The service never reads from .env for
the Gemini key — it always uses the key passed in.

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from pinecone import Pinecone, ServerlessSpec
import os

def get_embeddings(api_key):
    """Return GoogleGenerativeAIEmbeddings using the provided API key."""
    return GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=api_key
    )

def get_llm(api_key):
    """Return ChatGoogleGenerativeAI using the provided API key."""
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-pro",
        google_api_key=api_key,
        temperature=0.3,
        convert_system_message_to_human=True
    )

def ingest_document(file_path, document_id, file_type, api_key):
    """Load, chunk, embed and store document in Pinecone.
    Returns number of chunks created."""
    loaders = {
        'pdf': PyPDFLoader,
        'txt': TextLoader,
        'docx': Docx2txtLoader
    }
    loader = loaders[file_type](file_path)
    docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500, chunk_overlap=50
    )
    chunks = splitter.split_documents(docs)

    for chunk in chunks:
        chunk.metadata['document_id'] = str(document_id)

    embeddings = get_embeddings(api_key)
    PineconeVectorStore.from_documents(
        chunks, embeddings,
        index_name=os.environ["PINECONE_INDEX_NAME"],
        namespace=str(document_id)
    )
    return len(chunks)

def query_documents(user_message, document_ids, conversation_history, api_key):
    """Query one or more documents and get Gemini response.
    document_ids: list of Document.id integers to search across.
    Returns (answer_string, list_of_source_filenames)."""

    embeddings = get_embeddings(api_key)
    all_docs = []

    # Search each document namespace separately and combine results
    for doc_id in document_ids:
        vectorstore = PineconeVectorStore(
            index_name=os.environ["PINECONE_INDEX_NAME"],
            embedding=embeddings,
            namespace=str(doc_id)
        )
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
        results = retriever.invoke(user_message)
        all_docs.extend(results)

    # Sort by relevance and take top 5
    all_docs = all_docs[:5]

    context = "\n\n".join([doc.page_content for doc in all_docs])
    sources = list(set([
        doc.metadata.get('source', 'Unknown') for doc in all_docs
    ]))

    history_str = ""
    for msg in conversation_history[-6:]:
        role = "User" if msg['role'] == 'user' else "Assistant"
        history_str += f"{role}: {msg['content']}\n"

    prompt = f"""You are a helpful assistant that answers questions
based on the provided document content.
Answer questions ONLY using the document context below.
If the answer is not found in the documents, say:
"I could not find an answer to that in the provided documents."
Be clear, concise, and helpful.

DOCUMENT CONTEXT:
{context}

CONVERSATION HISTORY:
{history_str}

User: {user_message}
Assistant:"""

    llm = get_llm(api_key)
    response = llm.invoke(prompt)
    return response.content, sources

def delete_document_vectors(document_id):
    """Delete all vectors for a document namespace from Pinecone."""
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    index = pc.Index(os.environ["PINECONE_INDEX_NAME"])
    index.delete(delete_all=True, namespace=str(document_id))

---

## CORE FEATURES

### 1. Chat (/chat)

GET /chat:
- If current_user has no gemini_api_key: redirect to /profile/settings
  with warning flash
- Show list of available documents to query:
  - Global documents (is_global=True, status='ready')
  - User's own uploaded documents (owner_id=current_user.id, status='ready')
- If ?conversation_id= in query string: load that conversation
- Otherwise show document selection screen first
- Render chat/index.html

POST /chat/start:
- Accept list of selected document_ids from form
- Validate: at least one document selected
- Validate: user has access to selected documents
- Create new Conversation(user_id, document_ids=selected_ids,
  title=first document name)
- Redirect to /chat?conversation_id=<id>

POST /chat/message:
- Validate: message not empty + CSRF
- Get conversation by id, verify it belongs to current_user
- Save user ChatMessage to DB
- Build history from conversation.messages
- Call query_documents(message, conversation.document_ids, history,
  current_user.gemini_api_key) → (answer, sources)
- Save assistant ChatMessage (sources=sources)
- Redirect to GET /chat?conversation_id=<id>

POST /chat/new:
- Clear active conversation from session
- Redirect to GET /chat (back to document selection)

chat/index.html — two states:

STATE 1 — Document Selection (no active conversation):
- Heading: "Start a new chat — select documents to query"
- Two sections side by side:
  "Global Documents" (uploaded by admin)
  "My Documents" (uploaded by this user)
- Each document shown as a Bootstrap card with checkbox
- "Start Chat" button submits selected document IDs
- Link to /documents to upload more

STATE 2 — Active Chat:
- Left sidebar (col-3): list of user's past conversations
  showing title + date, clickable to switch
  "New Chat" button at top of sidebar
- Right (col-9): active chat window
  - Header: shows names of documents being queried
  - Scrollable message area
  - User messages: right-aligned, bg-primary text-white rounded
  - Assistant messages: left-aligned, bg-light rounded
  - Sources shown below assistant message in small text-muted italic
  - Form at bottom: textarea + Send + CSRF

chat.js:
- Auto-scroll chat window to bottom on load
- Auto-resize textarea on input
- Checkbox selection: highlight selected document cards

### 2. Document Management (/documents)

Users can upload their own documents.
Admins can upload global documents visible to all users.

GET /documents:
- Show user's own documents
- If admin: also show all global documents section
- Render documents/manage.html

POST /documents/upload:
- Validate extension (pdf/txt/docx) and size (under 10MB)
- Save with uuid4 stored_filename to uploads folder
- is_global = True if current_user.role == 'admin' else False
- owner_id = current_user.id
- Create Document record (status='processing'), commit
- Try: ingest_document(file_path, doc.id, ext, current_user.gemini_api_key)
  → status='ready', chunk_count=n
- Except: status='failed'
- Commit, flash result, redirect to GET /documents

POST /documents/<id>/delete:
- User can only delete their own documents
- Admin can delete any document
- delete_document_vectors(doc.id)
- Delete physical file
- Set is_active=False, commit
- Redirect to GET /documents

documents/manage.html:
- Upload form + CSRF
- Accepted: PDF, TXT, DOCX (max 10MB)
- "My Documents" table: Name, Status, Chunks, Date, Delete button
- Admin also sees "Global Documents" table with same columns
- JS confirm() before delete
- Status badges: processing=warning, ready=success, failed=danger
- If user has no API key: show warning banner
  "You need a Gemini API key to upload and process documents.
   Add your key in Settings."

### 3. Profile Settings (/profile/settings)

GET /profile/settings:
- Show user info (name, email, role)
- Gemini API key input section
- Render profile/settings.html

POST /profile/settings:
- Save gemini_api_key to current_user
- Flash success, redirect back

POST /profile/settings/key/delete:
- Delete gemini_api_key from current_user by setting to None
- Flash success, redirect back

settings.html:
- Card 1: Profile info (name, email, role badge) — read only for now
- Card 2: Gemini API Key
  - Password input for the key
  - Show status badge "Key Saved" or "Not Set"
  - Save button + CSRF
  - Helper text: "Get your free key at aistudio.google.com"
  - "Delete API Key" form + button underneath the save section

### 4. Admin Panel (/admin — Admin only)

GET /admin/users → list all users (20/page)

POST /admin/users/<id>/role:
- Validate role in ['user', 'admin']
- Prevent changing own role
- Update and redirect

POST /admin/users/<id>/disable:
- Prevent disabling own account
- Toggle is_active, redirect

admin/users.html:
- Bootstrap table: Name, Email, Role badge, API Key Set (Yes/No),
  Status, Joined, Actions
- Inline role select + Save per row
- Enable/Disable button per row
- Own row actions are disabled

---

## NAVIGATION (base.html)

Bootstrap 5 navbar, dark, sticky-top.

Left: brand name "DocChat"

Middle (authenticated only):
- Chat → /chat                     (all users)
- My Documents → /documents        (all users)
- Admin → /admin/users             (admin only)

Right:
- Logged in: name + role badge + Settings link + Logout
- Not logged in: Login + Register

Below navbar: dismissible Bootstrap flash alerts

---

## UI

base.html includes:
- Bootstrap 5.3 CSS + Icons CDN in <head>
- Bootstrap 5.3 JS bundle CDN before </body>
- {% block scripts %}{% endblock %}

main.css:
.chat-window {
    height: calc(100vh - 260px);
    overflow-y: auto;
}
.message-bubble {
    max-width: 75%;
    margin-bottom: 12px;
    padding: 10px 15px;
    border-radius: 18px;
}
.message-user { margin-left: auto; }
.message-bot  { margin-right: auto; }
.doc-card { cursor: pointer; transition: all 0.2s; }
.doc-card.selected { border-color: #0d6efd; background-color: #f0f5ff; }

---

## PINECONE SETUP (scripts/create_pinecone_index.py)

Run once before starting the app:

from pinecone import Pinecone, ServerlessSpec
import os
from dotenv import load_dotenv
load_dotenv()

pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
index_name = os.environ["PINECONE_INDEX_NAME"]

if index_name not in [i.name for i in pc.list_indexes()]:
    pc.create_index(
        name=index_name,
        dimension=768,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )
    print(f"Index '{index_name}' created.")
else:
    print(f"Index '{index_name}' already exists.")

---

## PRG PATTERN

Every POST route ends with redirect(), never render_template().
1. POST → process → flash → redirect to GET
2. GET → render with flash messages

---

## ERROR HANDLERS

@app.errorhandler(403) → errors/403.html
@app.errorhandler(404) → errors/404.html
@app.errorhandler(500) → errors/500.html

Each extends base.html with error code + message + link to /chat

---

## CODING RULES

1.  ALWAYS activate venv before pip install.
2.  App factory: create_app() in app/__init__.py.
3.  Blueprint for every route group.
4.  All secrets via .env — never hardcode.
5.  Flask-Migrate for all DB changes:
    flask db init
    flask db migrate -m "initial models"
    flask db upgrade
6.  Every protected route: @login_required + @role_required.
7.  Every form: {{ form.hidden_tag() }}.
8.  Always PRG pattern on every POST.
9.  Validate file extension AND size server-side on upload.
10. convert_system_message_to_human=True on ChatGoogleGenerativeAI.
11. Pinecone index dimension MUST be 768.
12. Docstrings on all service functions.
13. Register 403, 404, 500 error handlers.
14. Bootstrap utility classes — minimal custom CSS.
15. All models implement to_dict().
16. No email code anywhere.
17. Gemini API key ALWAYS comes from current_user.gemini_api_key
    and is passed as a parameter — never read from .env.
18. If user has no API key set, block chat and document upload
    and redirect to /profile/settings with a warning.

---

## BUILD ORDER

Phase 1 — Foundation
  1. Project folder structure + .gitignore
  2. config.py
  3. extensions.py (db, login_manager, csrf, oauth)
  4. app/__init__.py (app factory + blueprints + error handlers)
  5. run.py
  6. All database models
  7. flask db init + migrate + upgrade

Phase 2 — Auth
  8.  forms/auth_forms.py (LoginForm, RegisterForm)
  9.  routes/auth.py (register, login, logout, Google OAuth)
  10. templates/auth/login.html
  11. templates/auth/register.html
  12. templates/base.html

Phase 3 — Profile & API Key
  13. forms/chat_forms.py (ApiKeyForm)
  14. routes/profile.py (GET + POST /profile/settings)
  15. templates/profile/settings.html

Phase 4 — RAG & Documents
  16. scripts/create_pinecone_index.py
  17. services/rag_service.py
  18. forms/document_forms.py
  19. routes/documents.py
  20. templates/documents/manage.html

Phase 5 — Chat
  21. routes/chat.py
  22. templates/chat/index.html
  23. static/js/chat.js
  24. static/css/main.css

Phase 6 — Admin
  25. forms/admin_forms.py
  26. routes/admin.py
  27. templates/admin/users.html

Phase 7 — Polish
  28. templates/errors/403.html + 404.html + 500.html
  29. README.md

Phase 8 — Architecture & UI Revamp
  30. Replace Pinecone with FAISS local vector DB
  31. Replace Google embeddings with HuggingFace local models
  32. Revamp CSS to a Polygon-inspired Web3 Dark/Light theme

Phase 9 — Streaming Chat
  34. Refactor RAG logic to yield generation chunks
  35. Implement Flask Server-Sent Events (SSE) generator route
  36. Update Vanilla JS to consume data stream

Phase 10 — UX Improvements
  37. Allow all users to pick `is_global` on document upload
  38. Update RAG limits to pass up to 40 chunks max 
  39. Allow users to explicitly delete their Google API Key

Write complete, working, production-ready code for every file.
Do not use placeholder comments like "# TODO" or "# add logic here".
Every function must be fully implemented.