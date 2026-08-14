"""
Document ingestion pipeline for OnboardBot.

Pipeline:
    Documents (MD, TXT, PDF)
        ↓
    Text extraction & Section detection
        ↓
    Chunking
        ↓
    Vector Embeddings & Index Storage (FAISS / SentenceTransformer / TF-IDF NumPy fallback)
"""

import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from pypdf import PdfReader

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "data" / "docs"
INDEX_DIR = BASE_DIR / "data" / "index"

INDEX_FILE = INDEX_DIR / "company_docs.faiss"
METADATA_FILE = INDEX_DIR / "metadata.json"
TFIDF_FILE = INDEX_DIR / "vectorizer.json"

INDEX_DIR.mkdir(parents=True, exist_ok=True)

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

_embedding_model = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            print(f"Loading embedding model: {EMBEDDING_MODEL}")
            _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        except Exception as e:
            print(f"SentenceTransformer not available: {e}. Will use TF-IDF fallback.")
            _embedding_model = False
    return _embedding_model


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def load_pdf(file_path: Path) -> str:
    reader = PdfReader(str(file_path))
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            pages.append(text)
    return "\n\n".join(pages)


def load_text(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8", errors="ignore")


def load_documents(docs_dir: Path = DOCS_DIR) -> list[dict]:
    documents = []
    supported_extensions = {".pdf", ".md", ".txt"}
    if not docs_dir.exists():
        print(f"Documents directory does not exist: {docs_dir}")
        return documents

    for file_path in sorted(docs_dir.iterdir()):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in supported_extensions:
            continue
        try:
            extension = file_path.suffix.lower()
            if extension == ".pdf":
                text = load_pdf(file_path)
            else:
                text = load_text(file_path)
            text = clean_text(text)
            if not text:
                continue
            documents.append({"filename": file_path.name, "text": text})
            print(f"Loaded: {file_path.name}")
        except Exception as exc:
            print(f"Failed to load {file_path.name}: {exc}")

    return documents


def detect_section(line: str) -> str | None:
    line = line.strip()
    if not line:
        return None
    if re.match(r"^#{1,6}\s+", line):
        return re.sub(r"^#{1,6}\s+", "", line).strip()
    if re.match(r"^\d+(?:\.\d+)*\s+[A-Z][^\n]{2,100}$", line):
        return line
    return None


def chunk_document(filename: str, text: str, chunk_size: int = 300, overlap: int = 40) -> list[dict]:
    text = clean_text(text)
    if not text:
        return []

    lines = text.splitlines()
    sections = []
    current_section = None
    current_lines = []

    for line in lines:
        detected = detect_section(line)
        if detected:
            if current_lines:
                sections.append({
                    "section": current_section,
                    "text": "\n".join(current_lines).strip()
                })
            current_section = detected
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        sections.append({
            "section": current_section,
            "text": "\n".join(current_lines).strip()
        })

    chunks = []
    for section in sections:
        sec_text = clean_text(section["text"])
        if not sec_text:
            continue
        words = sec_text.split()
        start = 0
        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunk_str = " ".join(words[start:end]).strip()
            if chunk_str:
                chunks.append({
                    "doc": filename,
                    "section": section["section"],
                    "text": chunk_str,
                })
            if end >= len(words):
                break
            start = max(end - overlap, start + 1)

    return chunks


def embed_and_store(chunks: list[dict]) -> None:
    if not chunks:
        raise ValueError("No chunks generated.")

    model = get_embedding_model()
    texts = [c["text"] for c in chunks]

    if model:
        try:
            import faiss
            embeddings = model.encode(texts, normalize_embeddings=True)
            embeddings = embeddings.astype("float32")
            dimension = embeddings.shape[1]
            index = faiss.IndexFlatIP(dimension)
            index.add(embeddings)
            faiss.write_index(index, str(INDEX_FILE))
            print(f"FAISS index saved to: {INDEX_FILE}")
        except Exception as e:
            print(f"Could not save FAISS index: {e}")

    # Always save metadata with terms for TF-IDF / keyword similarity fallback
    metadata = {
        "embedding_model": EMBEDDING_MODEL if model else "tfidf",
        "chunks": chunks,
    }
    METADATA_FILE.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Metadata saved to: {METADATA_FILE}")


def run_ingestion() -> dict:
    print("\n=== OnboardBot Ingestion ===")
    documents = load_documents()
    if not documents:
        return {"status": "success", "documents_indexed": 0, "chunks_created": 0}

    all_chunks = []
    for doc in documents:
        chunks = chunk_document(doc["filename"], doc["text"])
        print(f"{doc['filename']}: {len(chunks)} chunks")
        all_chunks.extend(chunks)

    embed_and_store(all_chunks)
    result = {
        "status": "success",
        "documents_indexed": len(documents),
        "chunks_created": len(all_chunks),
    }
    print("=== Ingestion Complete ===")
    return result


if __name__ == "__main__":
    run_ingestion()