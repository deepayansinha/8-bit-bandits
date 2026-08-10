"""
/ask endpoint.

STATUS: Currently STUBBED with fake responses so the frontend can be built
against a stable contract right away. Person B: replace the body of
`ask_question` with a real call into rag.py once retrieval + LLM generation
are wired up. Keep the response shape identical to AskResponse.
"""

from fastapi import APIRouter
from app.schemas import AskRequest, AskResponse, Source

router = APIRouter()

# --- Fake canned responses for demo/dev purposes -----------------------
# Simple keyword match so the frontend team can see different states
# (normal answer vs fallback) while the real RAG pipeline isn't ready yet.
_FAKE_RESPONSES = {
    "sick": AskResponse(
        answer="You get 12 paid sick days per year, which reset every January 1st. "
               "Unused sick days do not carry over to the next year.",
        sources=[Source(doc="Leave Policy.pdf", section="3.2 Sick Leave")],
        fallback=False,
    ),
    "wifi": AskResponse(
        answer="I don't have information on that in the current docs. "
               "You should check with IT directly.",
        sources=[],
        fallback=True,
        suggested_contact="IT",
    ),
    "laptop": AskResponse(
        answer="New hires receive a company laptop on Day 1 during IT orientation. "
               "You'll need to set up your work email and VPN before your first standup.",
        sources=[Source(doc="IT Setup Guide.pdf", section="1. Day One Checklist")],
        fallback=False,
    ),
}

_DEFAULT_FALLBACK = AskResponse(
    answer="I don't have information on that in the current docs. "
           "You should check with HR directly.",
    sources=[],
    fallback=True,
    suggested_contact="HR",
)


@router.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest) -> AskResponse:
    question_lower = request.question.lower()

    for keyword, response in _FAKE_RESPONSES.items():
        if keyword in question_lower:
            return response

    return _DEFAULT_FALLBACK

    # --- Real implementation (Person B, replace above once ready) ------
    # from app.rag import answer_question
    # return await answer_question(request.question)
