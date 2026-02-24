from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
import os
import shutil

# To store local FAISS databases per document
FAISS_STORAGE_PATH = "instance/faiss_indexes"

# Global embeddings instance (loads into memory once, avoids reloading)
# all-MiniLM-L6-v2 is fast and small
_embeddings = None

def get_embeddings():
    """Return HuggingFaceEmbeddings using local model."""
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    return _embeddings

def get_llm(api_key):
    """Return ChatGoogleGenerativeAI using the provided API key."""
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key,
        temperature=0.3,
        max_retries=1,
        convert_system_message_to_human=True
    )

def _get_index_path(document_id):
    return os.path.join(FAISS_STORAGE_PATH, str(document_id))

def ingest_document(file_path, document_id, file_type, api_key):
    """Load, chunk, embed and store document in local FAISS."""
    loaders = {
        'pdf': PyPDFLoader,
        'txt': TextLoader,
        'docx': Docx2txtLoader
    }
    loader_class = loaders.get(file_type)
    if not loader_class:
        raise ValueError(f"Unsupported file type: {file_type}")
        
    loader = loader_class(file_path)
    docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500, chunk_overlap=50
    )
    chunks = splitter.split_documents(docs)

    for chunk in chunks:
        chunk.metadata['document_id'] = str(document_id)

    embeddings = get_embeddings()
    
    # Store directly in a document-specific FAISS index
    index_path = _get_index_path(document_id)
    os.makedirs(FAISS_STORAGE_PATH, exist_ok=True)
    
    vectorstore = FAISS.from_documents(chunks, embeddings)
    vectorstore.save_local(index_path)
    
    return len(chunks)

def query_documents(user_message, document_ids, conversation_history, api_key):
    """Query one or more documents and get Gemini response.
    document_ids: list of Document.id integers to search across.
    Returns (answer_string, list_of_source_filenames)."""

    embeddings = get_embeddings()
    all_docs = []

    # Search each document's FAISS index separately and combine results
    for doc_id in document_ids:
        index_path = _get_index_path(doc_id)
        if not os.path.exists(index_path):
            continue
            
        vectorstore = FAISS.load_local(
            index_path, 
            embeddings,
            allow_dangerous_deserialization=True # Required when loading local files you created
        )
        retriever = vectorstore.as_retriever(search_kwargs={"k": 20})
        results = retriever.invoke(user_message)
        all_docs.extend(results)

    # Gemini Flash has a very large context window, we can send many chunks
    all_docs = all_docs[:40]

    context = "\n\n".join([doc.page_content for doc in all_docs])
    sources = list(set([
        doc.metadata.get('source', 'Unknown') for doc in all_docs
    ]))

    history_str = ""
    for msg in conversation_history[-6:]:
        role = "User" if msg['role'] == 'user' else "Assistant"
        history_str += f"{role}: {msg['content']}\n"

    prompt = f"""You are a helpful assistant that answers questions
based on the provided document context.
Answer questions ONLY using the document context below.
If the answer is not found in the context, say:
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


def query_documents_stream(user_message, document_ids, conversation_history, api_key):
    """Query one or more documents and yield Gemini response chunks.
    document_ids: list of Document.id integers to search across.
    Yields (chunk_str, list_of_source_filenames) as a tuple for each chunk."""

    embeddings = get_embeddings()
    all_docs = []

    # Search each document's FAISS index separately and combine results
    for doc_id in document_ids:
        index_path = _get_index_path(doc_id)
        if not os.path.exists(index_path):
            continue
            
        vectorstore = FAISS.load_local(
            index_path, 
            embeddings,
            allow_dangerous_deserialization=True 
        )
        retriever = vectorstore.as_retriever(search_kwargs={"k": 20})
        results = retriever.invoke(user_message)
        all_docs.extend(results)

    # Gemini Flash has a very large context window, we can send many chunks
    all_docs = all_docs[:40]

    context = "\n\n".join([doc.page_content for doc in all_docs])
    sources = list(set([
        doc.metadata.get('source', 'Unknown') for doc in all_docs
    ]))

    history_str = ""
    for msg in conversation_history[-6:]:
        role = "User" if msg['role'] == 'user' else "Assistant"
        history_str += f"{role}: {msg['content']}\n"

    prompt = f"""You are a helpful assistant that answers questions
based on the provided document context.
Answer questions ONLY using the document context below.
If the answer is not found in the context, say:
"I could not find an answer to that in the provided documents."
Be clear, concise, and helpful.

DOCUMENT CONTEXT:
{context}

CONVERSATION HISTORY:
{history_str}

User: {user_message}
Assistant:"""

    llm = get_llm(api_key)
    
    # Send an initial chunk containing just the sources so the frontend can display them immediately
    yield ("", sources)
    
    for chunk in llm.stream(prompt):
        if chunk.content:
            yield (chunk.content, sources)

def delete_document_vectors(document_id):
    """Delete all local FAISS vectors for a document."""
    index_path = _get_index_path(document_id)
    if os.path.exists(index_path):
        shutil.rmtree(index_path)
