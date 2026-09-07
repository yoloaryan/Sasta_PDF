import os
import re
import uuid
import pypdf

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from database import add_documents, delete_document_from_store, UPLOAD_DIR

os.makedirs(UPLOAD_DIR, exist_ok=True)


def delete_pdf(filename: str, document_id: str):
    delete_document_from_store(document_id)
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
    raw_docs = []

    # Attempt 1: pypdf PdfReader
    try:
        reader = pypdf.PdfReader(file_path)
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            raw_docs.append({
                "text": text,
                "page": i + 1
            })
    except Exception as e:
        print(f"pypdf PdfReader error: {e}")

    total_pages = len(raw_docs)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks_to_embed = []
    for doc in raw_docs:
        cleaned = clean_text(doc["text"])
        if not cleaned:
            continue

        sub_chunks = splitter.split_text(cleaned)
        for sub in sub_chunks:
            sub_cleaned = clean_text(sub)
            if sub_cleaned:
                chunks_to_embed.append({
                    "text": sub_cleaned,
                    "metadata": {
                        "document_id": document_id,
                        "filename": filename,
                        "page_number": doc["page"],
                    }
                })

    warning_msg = None
    if chunks_to_embed:
        add_documents(chunks_to_embed)
    elif total_pages > 0:
        warning_msg = "PDF uploaded, but no readable text was detected (e.g. scanned image PDF)."

    return {
        "document_id": document_id,
        "filename": filename,
        "pages": total_pages,
        "chunks": len(chunks_to_embed),
        "warning": warning_msg
    }
