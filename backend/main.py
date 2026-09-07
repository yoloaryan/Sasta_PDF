import os
import shutil

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ingestion import (
    process_pdf,
    safe_filename,
    delete_pdf,
    UPLOAD_DIR
)
from rag import ask_question

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

app = FastAPI(
    title="SastaPDF AI",
    version="1.0.0"
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Server Error: {str(exc)}"}
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/files",
    StaticFiles(directory=UPLOAD_DIR),
    name="files"
)

class ChatRequest(BaseModel):
    question: str
    document_id: str | None = None

@app.get("/")
def root():
    return {
        "status": "online",
        "message": "SastaPDF AI is running"
    }

@app.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...)
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file selected."
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported."
        )

    # 10MB File Size Limit Check
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="File size exceeds the 10MB limit."
        )

    filename = safe_filename(file.filename)
    file_path = os.path.join(
        UPLOAD_DIR,
        filename
    )

    if os.path.exists(file_path):
        base, ext = os.path.splitext(filename)
        counter = 1

        while os.path.exists(file_path):
            filename = f"{base}_{counter}{ext}"
            file_path = os.path.join(
                UPLOAD_DIR,
                filename
            )
            counter += 1

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(
            file.file,
            buffer
        )

    try:
        result = process_pdf(
            file_path,
            filename
        )
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)

        raise HTTPException(
            status_code=500,
            detail=f"PDF processing failed: {e}"
        )

    return {
        "success": True,
        **result
    }

@app.delete("/documents/{document_id}")
def delete_document(document_id: str, filename: str | None = None):
    try:
        delete_pdf(filename, document_id)
        return {
            "success": True,
            "message": f"Document {document_id} deleted successfully."
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete document: {e}"
        )


@app.post("/chat")
def chat(request: ChatRequest):
    if not request.question.strip():
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )

    try:
        result = ask_question(
            request.question,
            request.document_id
        )

        return {
            "success": True,
            **result
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"RAG error: {e}"
        )

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )
