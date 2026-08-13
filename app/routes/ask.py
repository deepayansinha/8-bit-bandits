from fastapi import APIRouter, HTTPException

from app.rag import answer_question
from app.schemas import (
    AskRequest,
    AskResponse,
)


router = APIRouter(
    prefix="/ask",
    tags=["Chat"],
)


@router.post(
    "",
    response_model=AskResponse,
)
async def ask(
    request: AskRequest,
):

    question = request.question.strip()

    if not question:

        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty.",
        )

    try:

        return await answer_question(
            question
        )

    except FileNotFoundError as exc:

        raise HTTPException(
            status_code=503,
            detail=str(exc),
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"RAG pipeline failed: {exc}",
        )