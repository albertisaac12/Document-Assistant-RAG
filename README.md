# Document Q&A Chatbot

A full-stack web application that allows users to query their documents using a LangChain + Pinecone + Gemini RAG pipeline.

## Features
- Ask questions to your PDF, TXT, or DOCX documents with context-aware RAG.
- Per-user Gemini API Key settings stored securely.
- "Global" documents uploaded by admins for all users.
- Private documents uploaded by standard users.
- Pinecone Serverless integration for vector search.
- Complete conversation history per chat session.
- Google OAuth login integration and normal credentials auth.

## Setup Requirements

1. Python 3.9+
2. A free Pinecone account (pinecone.io) for vector storage
3. Google OAuth App in Google Cloud Console
4. A free Gemini API Key from Google AI Studio (provided per-user in the app UI)

## Installation Guide

1. Clone this repository or use the directory.
2. Initialize virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Linux/macOS
   venv\Scripts\activate     # On Windows
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure the `.env` file with your Pinecone configuration and Google OAuth keys.
5. Create the Pinecone index (dimension 3072 is required):
   ```bash
   python scripts/create_pinecone_index.py
   ```
6. Run the database migrations with Flask:
   ```bash
   flask db upgrade
   ```
7. Start the application:
   ```bash
   python run.py
   ```
8. The app will be available at `http://localhost:5000`.

## Architecture
- **Framework**: Flask (Python)
- **Database**: SQLite with SQLAlchemy (ORM)
- **UI**: Bootstrap 5 + Jinja2 Templates
- **LLM/Embeddings**: Google Gemini API & Generative AI Embeddings
- **Vector Database**: Pinecone
- **RAG orchestration**: LangChain
