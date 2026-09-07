# SastaPDF AI

Adobe Acrobat-inspired PDF RAG application using:

- FastAPI
- ChromaDB
- BAAI/bge-small-en-v1.5
- Groq GPT-OSS-120B
- PyPDFLoader
- HTML/CSS/JavaScript

## Run the backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
```

Windows:

```bash
.venv\Scripts\activate
```

Install:

```bash
pip install -r requirements.txt
```

Create `.env` from `.env.example` and add your Groq API key.

Then:

```bash
python main.py
```

## Run frontend

Open another terminal:

```bash
cd frontend
python -m http.server 5500
```

Open:

http://127.0.0.1:5500

## ChromaDB

ChromaDB is persistent in:

`backend/chroma-db/`

Uploaded PDFs are stored in:

`backend/uploads/`

Each PDF receives a `document_id`, so retrieval is restricted to the selected document.
