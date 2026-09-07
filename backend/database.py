import os
import sys

# Ensure caches use a writable directory
os.environ.setdefault("HF_HOME", os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache", "hf"))
os.environ.setdefault("FASTEMBED_CACHE_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache", "fastembed"))

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_community.embeddings import FastEmbedEmbeddings

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

CHROMA_PATH = os.path.join(BASE_DIR, "chroma-db")
os.makedirs(CHROMA_PATH, exist_ok=True)

if os.environ.get("RENDER"):
    UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
elif os.environ.get("VERCEL"):
    UPLOAD_DIR = "/tmp/uploads"
else:
    UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

os.makedirs(UPLOAD_DIR, exist_ok=True)

_vectorstore = None

def get_vectorstore():
    global _vectorstore
    if _vectorstore is None:
        embeddings_model = FastEmbedEmbeddings(
            model_name="BAAI/bge-small-en-v1.5"
        )
        _vectorstore = Chroma(
            persist_directory=CHROMA_PATH,
            embedding_function=embeddings_model,
            collection_name="sasta_pdf_documents",
        )
    return _vectorstore

def delete_document_from_vectorstore(document_id: str):
    try:
        store = get_vectorstore()
        store._collection.delete(where={"document_id": document_id})
        return True
    except Exception as e:
        print(f"Error deleting document {document_id} from vectorstore: {e}")
        return False
