"""
Pure Python in-memory vector store using Mistral embeddings.
No native binaries (no SQLite, no ONNX). Works on Vercel serverless.
"""
import os
import json
import math
import http.client
import urllib.parse

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "")

if os.environ.get("VERCEL"):
    UPLOAD_DIR = "/tmp/uploads"
else:
    UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

os.makedirs(UPLOAD_DIR, exist_ok=True)


def get_mistral_embedding(texts: list[str]) -> list[list[float]]:
    """Call Mistral embedding API, returns list of embedding vectors."""
    payload = json.dumps({
        "model": "mistral-embed",
        "input": texts,
        "encoding_format": "float"
    }).encode("utf-8")

    conn = http.client.HTTPSConnection("api.mistral.ai", timeout=30)
    conn.request(
        "POST",
        "/v1/embeddings",
        body=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {MISTRAL_API_KEY}"
        }
    )
    resp = conn.getresponse()
    body = json.loads(resp.read().decode("utf-8"))
    conn.close()

    if resp.status != 200:
        raise RuntimeError(f"Mistral embedding error {resp.status}: {body}")

    return [item["embedding"] for item in body["data"]]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


# In-memory store: list of {"text": str, "embedding": list[float], "metadata": dict}
_store: list[dict] = []


def get_vectorstore():
    """Returns the in-memory store (for compatibility with existing code)."""
    return _store


def add_documents(chunks: list[dict]):
    """
    chunks: list of {"text": str, "metadata": dict}
    Embeds them and adds to in-memory store.
    """
    global _store
    texts = [c["text"] for c in chunks]
    if not texts:
        return

    # Batch in groups of 50 (Mistral API limit)
    all_embeddings = []
    for i in range(0, len(texts), 50):
        batch = texts[i:i + 50]
        embeddings = get_mistral_embedding(batch)
        all_embeddings.extend(embeddings)

    for chunk, embedding in zip(chunks, all_embeddings):
        _store.append({
            "text": chunk["text"],
            "embedding": embedding,
            "metadata": chunk["metadata"]
        })


def similarity_search(query: str, k: int = 5, document_id: str | None = None) -> list[dict]:
    """Search the in-memory store for the k most similar chunks."""
    if not _store:
        return []

    query_embedding = get_mistral_embedding([query])[0]

    scored = []
    for item in _store:
        if document_id and item["metadata"].get("document_id") != document_id:
            continue
        score = cosine_similarity(query_embedding, item["embedding"])
        scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:k]]


def delete_document_from_store(document_id: str):
    """Remove all chunks for a given document_id from in-memory store."""
    global _store
    _store = [item for item in _store if item["metadata"].get("document_id") != document_id]
    return True
