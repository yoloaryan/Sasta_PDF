import os

from dotenv import load_dotenv

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
        from langchain_chroma import Chroma
        from langchain_mistralai import MistralAIEmbeddings

        embeddings_model = MistralAIEmbeddings(
            model="mistral-embed",
            mistral_api_key=os.environ.get("MISTRAL_API_KEY", "")
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
