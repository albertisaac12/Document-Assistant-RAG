from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_pinecone import PineconeVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from pinecone import Pinecone, ServerlessSpec
import os
import shutil
import time

# Global embeddings instance (loads into memory once, avoids reloading)
# all-MiniLM-L6-v2 is fast and small
_embeddings = None
_checked_indexes = set()

def get_embeddings():
    """Return HuggingFaceEmbeddings using local model."""
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    return _embeddings

def ensure_pinecone_index(api_key, index_name):
    if not api_key or not index_name:
        return
        
    cache_key = f"{api_key}:{index_name}"
    if cache_key in _checked_indexes:
        return
        
    pc = Pinecone(api_key=api_key)
    embeddings = get_embeddings()
    test_vector = embeddings.embed_query("test")
    dim = len(test_vector)
    
    existing_indexes = [index_info["name"] for index_info in pc.list_indexes()]
    
    if index_name not in existing_indexes:
        print(f"Creating Pinecone index '{index_name}' with dimension {dim}...")
        pc.create_index(
            name=index_name,
            dimension=dim,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
        time.sleep(5)
    else:
        desc = pc.describe_index(index_name)
        if desc.dimension != dim:
            print(f"Dimension mismatch! Recreating index '{index_name}' with dimension {dim}...")
            pc.delete_index(index_name)
            pc.create_index(
                name=index_name,
                dimension=dim,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
            time.sleep(5)
            
    _checked_indexes.add(cache_key)


def get_llm(api_key):
    """Return ChatGoogleGenerativeAI using the provided API key."""
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key,
        temperature=0.3,
        max_retries=1,
        convert_system_message_to_human=True
    )

def ingest_document(file_path, document_id, file_type, gemini_api_key, pinecone_api_key, pinecone_index_name):
    """Load, chunk, embed and store document in Pinecone."""
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
    ensure_pinecone_index(pinecone_api_key, pinecone_index_name)
    
    # Store in Pinecone, using document_id as namespace
    PineconeVectorStore.from_documents(
        chunks,
        embeddings,
        pinecone_api_key=pinecone_api_key,
        index_name=pinecone_index_name,
        namespace=str(document_id)
    )
    
    return len(chunks)

def query_documents(user_message, document_ids, conversation_history, gemini_api_key, pinecone_api_key, pinecone_index_name):
    """Query one or more documents and get Gemini response.
    document_ids: list of Document.id integers to search across.
    Returns (answer_string, list_of_source_filenames)."""

    embeddings = get_embeddings()
    ensure_pinecone_index(pinecone_api_key, pinecone_index_name)
    all_docs = []

    # Search each document's Pinecone namespace separately and combine results
    for doc_id in document_ids:
        vectorstore = PineconeVectorStore(
            index_name=pinecone_index_name,
            pinecone_api_key=pinecone_api_key,
            embedding=embeddings,
            namespace=str(doc_id)
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

    llm = get_llm(gemini_api_key)
    response = llm.invoke(prompt)
    return response.content, sources


def query_documents_stream(user_message, document_ids, conversation_history, gemini_api_key, pinecone_api_key, pinecone_index_name):
    """Query one or more documents and yield Gemini response chunks.
    document_ids: list of Document.id integers to search across.
    Yields (chunk_str, list_of_source_filenames) as a tuple for each chunk."""

    embeddings = get_embeddings()
    ensure_pinecone_index(pinecone_api_key, pinecone_index_name)
    all_docs = []

    # Search each document's Pinecone namespace separately and combine results
    for doc_id in document_ids:
        vectorstore = PineconeVectorStore(
            index_name=pinecone_index_name,
            pinecone_api_key=pinecone_api_key,
            embedding=embeddings,
            namespace=str(doc_id)
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

    llm = get_llm(gemini_api_key)
    
    # Send an initial chunk containing just the sources so the frontend can display them immediately
    yield ("", sources)
    
    for chunk in llm.stream(prompt):
        if chunk.content:
            yield (chunk.content, sources)

def delete_document_vectors(document_id, pinecone_api_key, pinecone_index_name):
    """Delete all Pinecone vectors for a document."""
    pc = Pinecone(api_key=pinecone_api_key)
    try:
        index = pc.Index(pinecone_index_name)
        # Delete the entire namespace
        index.delete(delete_all=True, namespace=str(document_id))
    except Exception as e:
        print(f"Error deleting vectors from Pinecone: {e}")
