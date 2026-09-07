import os
import sys

# Ensure caches use writable /tmp in serverless environment
os.environ["HF_HOME"] = "/tmp/hf_home"
os.environ["FASTEMBED_CACHE_PATH"] = "/tmp/fastembed_cache"
os.environ["SENTENCE_TRANSFORMERS_HOME"] = "/tmp/st_home"
os.environ["CHROMA_TELEMETRY"] = "0"

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

IS_VERCEL = bool(os.environ.get("VERCEL"))

if IS_VERCEL:
    CHROMA_PATH = "/tmp/chroma-db"
else:
    CHROMA_PATH = os.path.join(BASE_DIR, "chroma-db")

_client = None
_vectorstore = None

def _get_client():
    global _client
    if _client is None:
        import chromadb
        if IS_VERCEL:
            # Use ephemeral client to avoid SQLite issues on Vercel serverless
            _client = chromadb.EphemeralClient()
        else:
            os.makedirs(CHROMA_PATH, exist_ok=True)
            _client = chromadb.PersistentClient(path=CHROMA_PATH)
    return _client

def get_vectorstore():
    global _vectorstore
    if _vectorstore is None:
        from langchain_chroma import Chroma
        from langchain_community.embeddings import FastEmbedEmbeddings

        os.makedirs("/tmp/fastembed_cache", exist_ok=True)

        embeddings_model = FastEmbedEmbeddings(
            model_name="BAAI/bge-small-en-v1.5"
        )
        client = _get_client()
        _vectorstore = Chroma(
            client=client,
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
