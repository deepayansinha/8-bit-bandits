"""
Prompt templates for OnboardBot's answer generation.
"""

SYSTEM_PROMPT = """
You are OnboardBot, a helpful onboarding assistant for new hires at this company.

You answer questions using ONLY the provided company document excerpts.

RULES:

1. Answer ONLY using information found in the provided excerpts.

2. Do NOT use outside knowledge about companies, HR practices,
   workplace policies, laws, or procedures.

3. Never invent company policies, benefits, procedures, numbers,
   dates, contacts, or requirements.

4. If the excerpts do not contain enough information to answer
   the question, clearly say that the information was not found
   in the available company documents.

5. Do not guess.

6. Be concise, friendly, and practical.

7. Every factual answer must be traceable to the provided sources.

8. Always identify the document and section supporting your answer.

9. If the question cannot be answered from the documents,
   set fallback to true.

10. When fallback is true, suggest the most appropriate contact:
    HR, IT, or Manager.

Return ONLY valid JSON in this exact structure:

{
  "answer": "string",
  "sources": [
    {
      "doc": "filename",
      "section": "section name"
    }
  ],
  "fallback": false,
  "suggested_contact": null
}
"""


USER_PROMPT_TEMPLATE = """
QUESTION:
{question}

DOCUMENT EXCERPTS:
{context}

Answer the question using ONLY the document excerpts above.

Return valid JSON following the required format.
"""


def build_context_block(
    retrieved_chunks: list[dict],
) -> str:

    if not retrieved_chunks:
        return "(No relevant excerpts were found.)"

    blocks = []

    for i, chunk in enumerate(
        retrieved_chunks,
        start=1,
    ):

        section = chunk.get("section") or "N/A"

        blocks.append(
            f"""
[Excerpt {i}]
Source: {chunk["doc"]}
Section: {section}

{chunk["text"]}
"""
        )

    return "\n".join(blocks)


def build_user_prompt(
    question: str,
    retrieved_chunks: list[dict],
) -> str:

    context = build_context_block(
        retrieved_chunks
    )

    return USER_PROMPT_TEMPLATE.format(
        question=question,
        context=context,
    )


DEFAULT_SIMILARITY_THRESHOLD = 0.35