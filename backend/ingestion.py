import os
import re
import uuid
import pypdf

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from database import get_vectorstore, delete_document_from_vectorstore

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

def delete_pdf(filename: str, document_id: str):
    delete_document_from_vectorstore(document_id)
    if filename:
        file_path = os.path.join(UPLOAD_DIR, safe_filename(filename))
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Error removing file {file_path}: {e}")


def clean_text(text: str) -> str:
    if not text or not isinstance(text, str):
        return ""
    cleaned = text.encode("utf-8", "ignore").decode("utf-8").strip()
    return cleaned

def safe_filename(filename: str) -> str:
    filename = os.path.basename(filename)
    return re.sub(r"[^a-zA-Z0-9._-]", "_", filename)

def process_pdf(file_path: str, filename: str):
    document_id = str(uuid.uuid4())
    documents = []

    # Attempt 1: PyPDFLoader
    try:
        loader = PyPDFLoader(file_path)
        documents = loader.load()
    except Exception as e:
        print(f"PyPDFLoader warning: {e}. Falling back to pypdf.PdfReader...")

    # Attempt 2: Fallback to pypdf PdfReader if PyPDFLoader returned 0 docs or failed
    if not documents:
        try:
            reader = pypdf.PdfReader(file_path)
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                documents.append(
                    Document(
                        page_content=text,
                        metadata={"page": i}
                    )
                )
        except Exception as e:
            print(f"pypdf PdfReader error: {e}")

    valid_documents = []
    for doc in documents:
        cleaned = clean_text(doc.page_content)
        doc.page_content = cleaned
        doc.metadata["document_id"] = document_id
        doc.metadata["filename"] = filename
        doc.metadata["page_number"] = doc.metadata.get("page", 0) + 1

        if cleaned:
            valid_documents.append(doc)

    total_pages = len(documents) if documents else len(valid_documents)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = splitter.split_documents(valid_documents) if valid_documents else []

    valid_chunks = []
    for chunk in chunks:
        chunk.page_content = clean_text(chunk.page_content)
        if not chunk.page_content:
            continue

        chunk.metadata["document_id"] = document_id
        chunk.metadata["filename"] = filename
        valid_chunks.append(chunk)

    if valid_chunks:
        vectorstore = get_vectorstore()
        ids = [f"{document_id}_{i}" for i in range(len(valid_chunks))]
        vectorstore.add_documents(
            documents=valid_chunks,
            ids=ids
        )

    warning_msg = None
    if total_pages > 0 and len(valid_chunks) == 0:
        warning_msg = "PDF uploaded, but no readable text was detected (e.g. scanned image PDF)."

    return {
        "document_id": document_id,
        "filename": filename,
        "pages": total_pages,
        "chunks": len(valid_chunks),
        "warning": warning_msg
    }
