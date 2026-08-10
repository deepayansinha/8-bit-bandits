"""
OWNER: Person A

Ingestion pipeline: load company docs -> chunk -> embed -> store in vector index.

Run this as a script whenever docs in data/docs/ change:
    python -m app.ingest

TODO for Person A:
1. Implement `load_documents()` — read PDFs/txt/md from DOCS_DIR
2. Implement `chunk_document()` — split into ~300-500 token chunks,
   ideally splitting on headings/sections so citations are meaningful
3. Implement `embed_and_store()` — embed chunks and persist to FAISS/Chroma
4. Make sure each chunk keeps metadata: {doc filename, section title}
   This metadata is what powers the citations in the final answer.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DOCS_DIR = Path(os.getenv("DOCS_DIR", "data/docs"))
INDEX_DIR = Path(os.getenv("INDEX_DIR", "data/index"))
VECTOR_STORE = os.getenv("VECTOR_STORE", "faiss")


def load_documents(docs_dir: Path = DOCS_DIR) -> list[dict]:
    """
    Load all supported documents from docs_dir.

    Returns a list of dicts: [{"filename": str, "text": str}, ...]

    TODO: handle .pdf (use pypdf), .md and .txt (plain read).
    """
    raise NotImplementedError("Person A: implement document loading")


def chunk_document(filename: str, text: str, chunk_size: int = 400, overlap: int = 50) -> list[dict]:
    """
    Split a document's text into overlapping chunks.

    Returns: [{"doc": filename, "section": str | None, "text": chunk_text}, ...]

    TIP: If your docs use markdown-style headings (# Section Name) or numbered
    sections (3.2 Sick Leave), try to split ON those boundaries first, and
    only fall back to fixed-size chunking within an oversized section.
    This makes your citations ("Section 3.2 Sick Leave") much more readable
    than "chunk #14".
    """
    raise NotImplementedError("Person A: implement chunking logic")


def embed_and_store(chunks: list[dict]) -> None:
    """
    Generate embeddings for all chunks and persist to the vector store
    (FAISS index file or ChromaDB collection) at INDEX_DIR.

    Also persist the chunk metadata (doc, section, text) alongside the
    vectors so retrieval can return full chunk info, not just IDs.
    """
    raise NotImplementedError("Person A: implement embedding + storage")


def run_ingestion() -> dict:
    """Full pipeline: load -> chunk -> embed -> store. Called by CLI and /ingest route."""
    documents = load_documents()

    all_chunks: list[dict] = []
    for doc in documents:
        all_chunks.extend(chunk_document(doc["filename"], doc["text"]))

    embed_and_store(all_chunks)

    return {
        "status": "success",
        "documents_indexed": len(documents),
        "chunks_created": len(all_chunks),
    }


if __name__ == "__main__":
    result = run_ingestion()
    print(f"Ingestion complete: {result}")
