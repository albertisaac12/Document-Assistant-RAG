from pinecone import Pinecone, ServerlessSpec
import os
from dotenv import load_dotenv

load_dotenv()

def create_index():
    api_key = os.environ.get("PINECONE_API_KEY")
    index_name = os.environ.get("PINECONE_INDEX_NAME")

    if not api_key or not index_name:
        print("Please set PINECONE_API_KEY and PINECONE_INDEX_NAME in .env")
        return

    pc = Pinecone(api_key=api_key)

    if index_name not in [i.name for i in pc.list_indexes()]:
        pc.create_index(
            name=index_name,
            dimension=3072,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
        print(f"Index '{index_name}' created.")
    else:
        print(f"Index '{index_name}' already exists.")

if __name__ == "__main__":
    create_index()
