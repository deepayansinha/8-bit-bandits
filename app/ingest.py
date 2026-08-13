"""
Document ingestion pipeline for OnboardBot.

Pipeline:
    Documents
        ↓
    Text extraction
        ↓
    Section detection
        ↓
    Chunking
        ↓
    Embeddings
        ↓
    FAISS index + metadata
"""

import json
import os
import re
from pathlib import Path

import faiss
from dotenv import load_dotenv
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer


load_dotenv()


# =========================================================
# PATHS & CONFIGURATION
# =========================================================

# backend/
BASE_DIR = Path(__file__).resolve().parent.parent

# backend/data/docs/
DOCS_DIR = BASE_DIR / "data" / "docs"

# backend/data/index/
INDEX_DIR = BASE_DIR / "data" / "index"

INDEX_FILE = INDEX_DIR / "company_docs.faiss"
METADATA_FILE = INDEX_DIR / "metadata.json"


EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",
)


# Make sure index directory exists.
INDEX_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# =========================================================
# EMBEDDING MODEL
# =========================================================

_embedding_model = None


def get_embedding_model():
    """
    Load the embedding model once and reuse it.
    """

    global _embedding_model

    if _embedding_model is None:

        print(
            f"Loading embedding model: {EMBEDDING_MODEL}"
        )

        _embedding_model = SentenceTransformer(
            EMBEDDING_MODEL
        )

    return _embedding_model


# =========================================================
# TEXT CLEANING
# =========================================================

def clean_text(text: str) -> str:
    """
    Normalize extracted document text.
    """

    text = text.replace(
        "\x00",
        " ",
    )

    # Remove excessive spaces.
    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    # Remove excessive blank lines.
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    return text.strip()


# =========================================================
# FILE LOADERS
# =========================================================

def load_pdf(
    file_path: Path,
) -> str:
    """
    Extract text from a PDF.
    """

    reader = PdfReader(
        str(file_path)
    )

    pages = []

    for page in reader.pages:

        text = page.extract_text() or ""

        if text.strip():
            pages.append(text)

    return "\n\n".join(pages)


def load_text(
    file_path: Path,
) -> str:
    """
    Load TXT or Markdown files.
    """

    return file_path.read_text(
        encoding="utf-8",
        errors="ignore",
    )


# =========================================================
# DOCUMENT LOADING
# =========================================================

def load_documents(
    docs_dir: Path = DOCS_DIR,
) -> list[dict]:
    """
    Load all supported documents from data/docs/.

    Supported:
        .pdf
        .md
        .txt
    """

    documents = []

    supported_extensions = {
        ".pdf",
        ".md",
        ".txt",
    }

    if not docs_dir.exists():

        print(
            f"Documents directory does not exist: {docs_dir}"
        )

        return documents

    for file_path in sorted(
        docs_dir.iterdir()
    ):

        if not file_path.is_file():
            continue

        if file_path.suffix.lower() not in supported_extensions:
            continue

        try:

            extension = file_path.suffix.lower()

            if extension == ".pdf":

                text = load_pdf(
                    file_path
                )

            else:

                text = load_text(
                    file_path
                )

            text = clean_text(
                text
            )

            if not text:
                print(
                    f"Skipping empty document: {file_path.name}"
                )
                continue

            documents.append(
                {
                    "filename": file_path.name,
                    "text": text,
                }
            )

            print(
                f"Loaded: {file_path.name}"
            )

        except Exception as exc:

            print(
                f"Failed to load "
                f"{file_path.name}: {exc}"
            )

    return documents


# =========================================================
# SECTION DETECTION
# =========================================================

def detect_section(
    line: str,
) -> str | None:
    """
    Detect Markdown-style headings and numbered headings.
    """

    line = line.strip()

    if not line:
        return None

    # Markdown heading:
    # # Leave Policy
    # ## Annual Leave
    if re.match(
        r"^#{1,6}\s+",
        line,
    ):

        return re.sub(
            r"^#{1,6}\s+",
            "",
            line,
        ).strip()

    # Numbered heading:
    # 3.1 Annual Leave
    # 3.2 Sick Leave
    if re.match(
        r"^\d+(?:\.\d+)*\s+[A-Z][^\n]{2,100}$",
        line,
    ):

        return line

    return None


# =========================================================
# CHUNKING
# =========================================================

def chunk_document(
    filename: str,
    text: str,
    chunk_size: int = 400,
    overlap: int = 50,
) -> list[dict]:
    """
    Split a document into overlapping word-based chunks.

    Each chunk retains:
        - document filename
        - section
        - text
    """

    text = clean_text(
        text
    )

    if not text:
        return []

    lines = text.splitlines()

    sections = []

    current_section = None
    current_lines = []

    for line in lines:

        detected_section = detect_section(
            line
        )

        if detected_section:

            if current_lines:

                sections.append(
                    {
                        "section": current_section,
                        "text": "\n".join(
                            current_lines
                        ).strip(),
                    }
                )

            current_section = detected_section

            current_lines = [
                line
            ]

        else:

            current_lines.append(
                line
            )

    # Save final section.
    if current_lines:

        sections.append(
            {
                "section": current_section,
                "text": "\n".join(
                    current_lines
                ).strip(),
            }
        )

    chunks = []

    for section in sections:

        section_text = clean_text(
            section["text"]
        )

        if not section_text:
            continue

        words = section_text.split()

        start = 0

        while start < len(words):

            end = min(
                start + chunk_size,
                len(words),
            )

            chunk_text = " ".join(
                words[start:end]
            ).strip()

            if chunk_text:

                chunks.append(
                    {
                        "doc": filename,
                        "section": section["section"],
                        "text": chunk_text,
                    }
                )

            if end >= len(words):
                break

            # Overlap between chunks.
            start = max(
                end - overlap,
                start + 1,
            )

    return chunks


# =========================================================
# EMBEDDING + FAISS STORAGE
# =========================================================

def embed_and_store(
    chunks: list[dict],
) -> None:
    """
    Convert chunks into embeddings and save them
    into a FAISS vector index.
    """

    if not chunks:

        raise ValueError(
            "No chunks were generated."
        )

    texts = [
        chunk["text"]
        for chunk in chunks
    ]

    model = get_embedding_model()

    print(
        f"Creating embeddings for "
        f"{len(texts)} chunks..."
    )

    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    embeddings = embeddings.astype(
        "float32"
    )

    dimension = embeddings.shape[1]

    # Inner product on normalized vectors
    # is equivalent to cosine similarity.
    index = faiss.IndexFlatIP(
        dimension
    )

    index.add(
        embeddings
    )

    faiss.write_index(
        index,
        str(INDEX_FILE),
    )

    metadata = {
        "embedding_model": EMBEDDING_MODEL,
        "chunks": chunks,
    }

    METADATA_FILE.write_text(
        json.dumps(
            metadata,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        f"FAISS index saved to: {INDEX_FILE}"
    )

    print(
        f"Metadata saved to: {METADATA_FILE}"
    )


# =========================================================
# FULL INGESTION PIPELINE
# =========================================================

def run_ingestion() -> dict:
    """
    Run the complete ingestion pipeline.
    """

    print(
        "\n=== OnboardBot Ingestion ==="
    )

    documents = load_documents()

    if not documents:

        return {
            "status": "success",
            "documents_indexed": 0,
            "chunks_created": 0,
        }

    all_chunks = []

    for document in documents:

        chunks = chunk_document(
            filename=document["filename"],
            text=document["text"],
        )

        print(
            f"{document['filename']}: "
            f"{len(chunks)} chunks"
        )

        all_chunks.extend(
            chunks
        )

    if not all_chunks:

        raise ValueError(
            "Documents were found, "
            "but no chunks were generated."
        )

    embed_and_store(
        all_chunks
    )

    result = {
        "status": "success",
        "documents_indexed": len(documents),
        "chunks_created": len(all_chunks),
    }

    print(
        "\n=== Ingestion Complete ==="
    )

    print(result)

    return result


# =========================================================
# COMMAND LINE ENTRY POINT
# =========================================================

if __name__ == "__main__":

    run_ingestion()