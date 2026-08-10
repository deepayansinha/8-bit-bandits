"""
Prompt templates for OnboardBot's answer generation.

Design principles baked into this prompt:
1. GROUNDING — the model must answer ONLY from the retrieved chunks, never
   from general knowledge. This prevents confidently wrong answers about
   company-specific policy (e.g. inventing a leave policy number).
2. HONEST FALLBACK — if the retrieved chunks don't actually answer the
   question, the model must say so plainly and route to a human/team,
   rather than stretching a half-relevant chunk into an answer.
3. CITATIONS — every factual claim should be traceable back to a specific
   doc/section so the new hire can go verify it themselves.
"""

SYSTEM_PROMPT = """You are OnboardBot, a helpful onboarding assistant for new hires at this company.

RULES YOU MUST FOLLOW:
1. Answer ONLY using the information in the provided document excerpts below. Do not use outside knowledge about companies, HR practices, or policies in general.
2. If the excerpts do not contain enough information to answer the question, say so clearly and honestly. Do NOT guess or fill gaps with plausible-sounding information.
3. When you answer from the excerpts, be concise, warm, and practical — you're talking to someone in their first week.
4. Always mention which document(s) your answer is based on.

You will be given:
- A new hire's QUESTION
- Several DOCUMENT EXCERPTS retrieved as potentially relevant

Respond in the following JSON format ONLY, with no other text before or after:
{{
  "answer": "<your answer, or an honest 'I don't know' style message>",
  "sources": [{{"doc": "<filename>", "section": "<section title if identifiable>"}}],
  "fallback": <true if you could not answer from the excerpts, else false>,
  "suggested_contact": "<'HR', 'IT', 'Manager', or null if fallback is false>"
}}
"""

USER_PROMPT_TEMPLATE = """QUESTION:
{question}

DOCUMENT EXCERPTS:
{context}

Based ONLY on the excerpts above, answer the question following the JSON format and rules from your instructions."""


def build_context_block(retrieved_chunks: list[dict]) -> str:
    """
    Turn retrieved chunks into a numbered context block for the prompt.

    Each chunk dict is expected to look like:
        {"doc": "Leave Policy.pdf", "section": "3.2 Sick Leave", "text": "..."}
    """
    if not retrieved_chunks:
        return "(No relevant excerpts were found in the document store.)"

    blocks = []
    for i, chunk in enumerate(retrieved_chunks, start=1):
        section = chunk.get("section") or "N/A"
        blocks.append(
            f"[Excerpt {i}] Source: {chunk['doc']} | Section: {section}\n{chunk['text']}"
        )
    return "\n\n".join(blocks)


def build_user_prompt(question: str, retrieved_chunks: list[dict]) -> str:
    context = build_context_block(retrieved_chunks)
    return USER_PROMPT_TEMPLATE.format(question=question, context=context)


# --- Suggested similarity threshold logic (used before even calling the LLM) ---
# If your top retrieved chunk's similarity score is below this threshold,
# you can skip the LLM call entirely and return a fallback response directly.
# This saves an API call and guarantees an honest "I don't know."
DEFAULT_SIMILARITY_THRESHOLD = 0.35
