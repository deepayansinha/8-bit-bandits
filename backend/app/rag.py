"""
OWNER: Person B

Retrieval + generation: given a question, retrieve relevant chunks and
generate a grounded, cited answer (or an honest fallback).

TODO for Person B:
1. Implement `retrieve_chunks()` — embed the question, query the vector
   store built by ingest.py, return top-k chunks with similarity scores
2. Implement `call_llm()` — send the prompt (from prompts.py) to
   Claude or OpenAI, parse the JSON response
3. Wire `answer_question()` together and swap it into routes/ask.py,
   replacing the stub
"""

import os
import json
from dotenv import load_dotenv

from app.prompts import SYSTEM_PROMPT, build_user_prompt, DEFAULT_SIMILARITY_THRESHOLD
from app.schemas import AskResponse, Source

load_dotenv()

TOP_K = int(os.getenv("TOP_K", 4))
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", DEFAULT_SIMILARITY_THRESHOLD))
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic")


def retrieve_chunks(question: str, top_k: int = TOP_K) -> list[dict]:
    """
    Embed the question and retrieve the top_k most similar chunks from
    the vector store built by ingest.py.

    Returns: [{"doc": str, "section": str | None, "text": str, "score": float}, ...]
    sorted by descending similarity score.
    """
    raise NotImplementedError("Person B: implement retrieval from vector store")


def call_llm(system_prompt: str, user_prompt: str) -> dict:
    """
    Call the configured LLM provider and parse its JSON response.

    Expected to return a dict matching AskResponse's shape:
        {"answer": str, "sources": [...], "fallback": bool, "suggested_contact": str|None}

    TIP: strip markdown code fences (```json ... ```) before json.loads(),
    models sometimes wrap JSON output even when told not to.
    """
    if LLM_PROVIDER == "anthropic":
        return _call_anthropic(system_prompt, user_prompt)
    elif LLM_PROVIDER == "openai":
        return _call_openai(system_prompt, user_prompt)
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER}")


def _call_anthropic(system_prompt: str, user_prompt: str) -> dict:
    # import anthropic
    # client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    # response = client.messages.create(
    #     model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
    #     max_tokens=1000,
    #     system=system_prompt,
    #     messages=[{"role": "user", "content": user_prompt}],
    # )
    # raw_text = response.content[0].text
    # return _parse_json_response(raw_text)
    raise NotImplementedError("Person B: implement Anthropic call")


def _call_openai(system_prompt: str, user_prompt: str) -> dict:
    # from openai import OpenAI
    # client = OpenAI()  # reads OPENAI_API_KEY from env
    # response = client.chat.completions.create(
    #     model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    #     messages=[
    #         {"role": "system", "content": system_prompt},
    #         {"role": "user", "content": user_prompt},
    #     ],
    #     response_format={"type": "json_object"},
    # )
    # raw_text = response.choices[0].message.content
    # return _parse_json_response(raw_text)
    raise NotImplementedError("Person B: implement OpenAI call")


def _parse_json_response(raw_text: str) -> dict:
    """Strip code fences if present, then parse JSON."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    return json.loads(cleaned.strip())


async def answer_question(question: str) -> AskResponse:
    """
    Full RAG flow: retrieve -> (threshold check) -> generate -> return AskResponse.
    This is what routes/ask.py should call once retrieval + generation are ready.
    """
    chunks = retrieve_chunks(question)

    # Skip the LLM call entirely if nothing relevant was found —
    # cheaper and guarantees an honest fallback instead of a stretched answer.
    if not chunks or chunks[0]["score"] < SIMILARITY_THRESHOLD:
        return AskResponse(
            answer="I don't have information on that in the current docs. "
                   "You should check with HR directly.",
            sources=[],
            fallback=True,
            suggested_contact="HR",
        )

    user_prompt = build_user_prompt(question, chunks)
    result = call_llm(SYSTEM_PROMPT, user_prompt)

    return AskResponse(
        answer=result["answer"],
        sources=[Source(**s) for s in result.get("sources", [])],
        fallback=result.get("fallback", False),
        suggested_contact=result.get("suggested_contact"),
    )
