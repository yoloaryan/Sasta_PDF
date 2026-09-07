import os

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

embeddings_model = FastEmbedEmbeddings(
    model_name="BAAI/bge-small-en-v1.5"
)

vectorstore = Chroma(
    persist_directory=CHROMA_PATH,
    embedding_function=embeddings_model,
    collection_name="sasta_pdf_documents",
)

def get_vectorstore():
    return vectorstore

def delete_document_from_vectorstore(document_id: str):
    try:
        vectorstore._collection.delete(where={"document_id": document_id})
        return True
    except Exception as e:
        print(f"Error deleting document {document_id} from vectorstore: {e}")
        return False


