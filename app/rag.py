"""
Retrieval + generation layer for OnboardBot.
"""

import json
import os
from pathlib import Path

import faiss
from dotenv import load_dotenv

from app.ingest import (
    get_embedding_model,
    INDEX_DIR,
    INDEX_FILE,
    METADATA_FILE,
)

from app.prompts import (
    SYSTEM_PROMPT,
    build_user_prompt,
    DEFAULT_SIMILARITY_THRESHOLD,
)

from app.schemas import (
    AskResponse,
    Source,
)


load_dotenv()


TOP_K = int(
    os.getenv(
        "TOP_K",
        "4",
    )
)

SIMILARITY_THRESHOLD = float(
    os.getenv(
        "SIMILARITY_THRESHOLD",
        DEFAULT_SIMILARITY_THRESHOLD,
    )
)

LLM_PROVIDER = os.getenv(
    "LLM_PROVIDER",
    "anthropic",
)


# ---------------------------------------------------------
# Load index
# ---------------------------------------------------------

def load_index():

    if not INDEX_FILE.exists():

        raise FileNotFoundError(
            "FAISS index not found. "
            "Run ingestion first."
        )

    return faiss.read_index(
        str(INDEX_FILE)
    )


def load_metadata() -> list[dict]:

    if not METADATA_FILE.exists():

        raise FileNotFoundError(
            "Metadata file not found. "
            "Run ingestion first."
        )

    data = json.loads(
        METADATA_FILE.read_text(
            encoding="utf-8"
        )
    )

    return data["chunks"]


# ---------------------------------------------------------
# Retrieval
# ---------------------------------------------------------

def retrieve_chunks(
    question: str,
    top_k: int = TOP_K,
) -> list[dict]:

    index = load_index()

    metadata = load_metadata()

    model = get_embedding_model()

    query_embedding = model.encode(
        [question],
        normalize_embeddings=True,
    )

    query_embedding = query_embedding.astype(
        "float32"
    )

    scores, indices = index.search(
        query_embedding,
        min(
            top_k,
            index.ntotal,
        ),
    )

    retrieved = []

    for score, idx in zip(
        scores[0],
        indices[0],
    ):

        if idx < 0:
            continue

        if idx >= len(metadata):
            continue

        chunk = metadata[idx].copy()

        chunk["score"] = float(
            score
        )

        retrieved.append(
            chunk
        )

    return retrieved


# ---------------------------------------------------------
# LLM
# ---------------------------------------------------------

def call_llm(
    system_prompt: str,
    user_prompt: str,
) -> dict:

    if LLM_PROVIDER == "anthropic":

        return _call_anthropic(
            system_prompt,
            user_prompt,
        )

    if LLM_PROVIDER == "openai":

        return _call_openai(
            system_prompt,
            user_prompt,
        )

    raise ValueError(
        f"Unknown LLM_PROVIDER: {LLM_PROVIDER}"
    )


# ---------------------------------------------------------
# Anthropic
# ---------------------------------------------------------

def _call_anthropic(
    system_prompt: str,
    user_prompt: str,
) -> dict:

    import anthropic

    client = anthropic.Anthropic()

    model = os.getenv(
        "ANTHROPIC_MODEL",
        "claude-sonnet-4-5",
    )

    response = client.messages.create(
        model=model,
        max_tokens=1000,
        temperature=0,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": user_prompt,
            }
        ],
    )

    raw_text = response.content[0].text

    return _parse_json_response(
        raw_text
    )


# ---------------------------------------------------------
# OpenAI
# ---------------------------------------------------------

def _call_openai(
    system_prompt: str,
    user_prompt: str,
) -> dict:

    from openai import OpenAI

    client = OpenAI()

    model = os.getenv(
        "OPENAI_MODEL",
        "gpt-4o-mini",
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        response_format={
            "type": "json_object"
        },
        temperature=0,
    )

    raw_text = (
        response
        .choices[0]
        .message
        .content
    )

    return _parse_json_response(
        raw_text
    )


# ---------------------------------------------------------
# JSON parsing
# ---------------------------------------------------------

def _parse_json_response(
    raw_text: str,
) -> dict:

    cleaned = raw_text.strip()

    if cleaned.startswith("```"):

        cleaned = cleaned.split(
            "```",
            2,
        )[1]

        if cleaned.startswith("json"):

            cleaned = cleaned[4:]

    return json.loads(
        cleaned.strip()
    )


# ---------------------------------------------------------
# Complete RAG pipeline
# ---------------------------------------------------------

async def answer_question(
    question: str,
) -> AskResponse:

    chunks = retrieve_chunks(
        question
    )

    if (
        not chunks
        or chunks[0]["score"]
        < SIMILARITY_THRESHOLD
    ):

        return AskResponse(
            answer=(
                "I couldn't find information about "
                "that in the current company documents."
            ),
            sources=[],
            fallback=True,
            suggested_contact="HR",
        )

    user_prompt = build_user_prompt(
        question,
        chunks,
    )

    result = call_llm(
        SYSTEM_PROMPT,
        user_prompt,
    )

    return AskResponse(
        answer=result["answer"],
        sources=[
            Source(**source)
            for source in result.get(
                "sources",
                [],
            )
        ],
        fallback=result.get(
            "fallback",
            False,
        ),
        suggested_contact=result.get(
            "suggested_contact"
        ),
    )