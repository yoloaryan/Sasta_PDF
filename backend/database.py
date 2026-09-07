import os
import sys

# Override sqlite3 for ChromaDB compatibility on Vercel
try:
    import pysqlite3
    sys.modules['sqlite3'] = pysqlite3
except Exception:
    pass

# Ensure caches use writable /tmp in serverless environment
os.environ["HF_HOME"] = "/tmp/hf_home"
os.environ["FASTEMBED_CACHE_PATH"] = "/tmp/fastembed_cache"
os.environ["SENTENCE_TRANSFORMERS_HOME"] = "/tmp/st_home"

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_community.embeddings import FastEmbedEmbeddings

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

if os.environ.get("VERCEL"):
    CHROMA_PATH = "/tmp/chroma-db"
else:
    CHROMA_PATH = os.path.join(BASE_DIR, "chroma-db")

os.makedirs("/tmp/hf_home", exist_ok=True)
os.makedirs("/tmp/fastembed_cache", exist_ok=True)
os.makedirs("/tmp/st_home", exist_ok=True)
os.makedirs(CHROMA_PATH, exist_ok=True)

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


