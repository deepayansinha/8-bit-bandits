"""
Retrieval + Generation pipeline for OnboardBot.
"""

import json
import os
import re
from pathlib import Path
from dotenv import load_dotenv

from app.ingest import (
    get_embedding_model,
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

TOP_K = int(os.getenv("TOP_K", "4"))
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.20"))
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto")


def load_metadata() -> list[dict]:
    if not METADATA_FILE.exists():
        # Auto-trigger ingestion if index doesn't exist yet
        from app.ingest import run_ingestion
        run_ingestion()

    if not METADATA_FILE.exists():
        raise FileNotFoundError("Metadata file not found. Run ingestion first.")

    data = json.loads(METADATA_FILE.read_text(encoding="utf-8"))
    return data["chunks"]


def score_text_relevance(question: str, text: str) -> float:
    """Fallback term-frequency & n-gram overlap similarity score."""
    q_words = set(re.findall(r"\w+", question.lower()))
    if not q_words:
        return 0.0
    t_words = set(re.findall(r"\w+", text.lower()))
    matches = q_words.intersection(t_words)
    score = len(matches) / len(q_words)

    # Bonus for exact phrases
    q_clean = question.lower().strip()
    if q_clean in text.lower():
        score += 0.5
    return score


def retrieve_chunks(question: str, top_k: int = TOP_K) -> list[dict]:
    metadata = load_metadata()
    model = get_embedding_model()

    if model:
        try:
            import faiss
            if INDEX_FILE.exists():
                index = faiss.read_index(str(INDEX_FILE))
                query_emb = model.encode([question], normalize_embeddings=True).astype("float32")
                scores, indices = index.search(query_emb, min(top_k, index.ntotal))

                retrieved = []
                for score, idx in zip(scores[0], indices[0]):
                    if idx >= 0 and idx < len(metadata):
                        chunk = metadata[idx].copy()
                        chunk["score"] = float(score)
                        retrieved.append(chunk)
                if retrieved:
                    return retrieved
        except Exception as e:
            print(f"FAISS search fallback: {e}")

    # NumPy / TF-IDF Keyword Matcher fallback
    scored_chunks = []
    for chunk in metadata:
        s = score_text_relevance(question, chunk["text"] + " " + (chunk.get("section") or ""))
        if s > 0:
            c = chunk.copy()
            c["score"] = float(s)
            scored_chunks.append(c)

    scored_chunks.sort(key=lambda x: x["score"], reverse=True)
    return scored_chunks[:top_k]


def call_llm(system_prompt: str, user_prompt: str) -> dict:
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    if gemini_key or LLM_PROVIDER == "gemini":
        try:
            return _call_gemini(system_prompt, user_prompt, gemini_key)
        except Exception as e:
            print(f"Gemini API call failed: {e}")

    if openai_key or LLM_PROVIDER == "openai":
        try:
            return _call_openai(system_prompt, user_prompt)
        except Exception as e:
            print(f"OpenAI API call failed: {e}")

    if anthropic_key or LLM_PROVIDER == "anthropic":
        try:
            return _call_anthropic(system_prompt, user_prompt)
        except Exception as e:
            print(f"Anthropic API call failed: {e}")

    # Smart local fallback when no external LLM key is configured
    return _local_extractive_answer(user_prompt)


def _call_gemini(system_prompt: str, user_prompt: str, api_key: str) -> dict:
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=system_prompt
    )
    res = model.generate_content(
        user_prompt,
        generation_config={"response_mime_type": "application/json"}
    )
    return _parse_json_response(res.text)


def _call_anthropic(system_prompt: str, user_prompt: str) -> dict:
    import anthropic
    client = anthropic.Anthropic()
    model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
    response = client.messages.create(
        model=model,
        max_tokens=1000,
        temperature=0,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return _parse_json_response(response.content[0].text)


def _call_openai(system_prompt: str, user_prompt: str) -> dict:
    from openai import OpenAI
    client = OpenAI()
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return _parse_json_response(response.choices[0].message.content)


def _local_extractive_answer(user_prompt: str) -> dict:
    """Smart local fallback answer generator."""
    # Extract excerpts from prompt
    excerpts = re.findall(r"\[Excerpt \d+\]\nSource: ([^\n]+)\nSection: ([^\n]+)\n\n([\s\S]+?)(?=\n\[Excerpt|\Z)", user_prompt)
    if not excerpts:
        return {
            "answer": "I couldn't find relevant information in the company documents for your question.",
            "sources": [],
            "fallback": True,
            "suggested_contact": "HR"
        }

    sources = []
    answers = []
    for doc, sec, text in excerpts[:2]:
        sources.append({"doc": doc, "section": sec})
        cleaned_text = text.strip().replace("\n", " ")
        answers.append(cleaned_text)

    full_answer = " ".join(answers)
    if len(full_answer) > 300:
        full_answer = full_answer[:300] + "..."

    return {
        "answer": f"According to company documentation: {full_answer}",
        "sources": sources,
        "fallback": False,
        "suggested_contact": None
    }


def _parse_json_response(raw_text: str) -> dict:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```", 2)[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    return json.loads(cleaned.strip())


async def answer_question(question: str) -> AskResponse:
    chunks = retrieve_chunks(question)

    if not chunks or (chunks[0]["score"] < SIMILARITY_THRESHOLD and chunks[0]["score"] < 0.1):
        return AskResponse(
            answer="I couldn't find information about that in the current company documents.",
            sources=[],
            fallback=True,
            suggested_contact="HR or IT Support",
        )

    user_prompt = build_user_prompt(question, chunks)
    result = call_llm(SYSTEM_PROMPT, user_prompt)

    return AskResponse(
        answer=result.get("answer", "No answer found."),
        sources=[Source(**s) for s in result.get("sources", [])],
        fallback=result.get("fallback", False),
        suggested_contact=result.get("suggested_contact"),
    )