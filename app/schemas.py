"""
API contract for OnboardBot.

Frontend and backend should code against these shapes.
"""

from typing import Optional

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        description="The new hire's question",
    )


class Source(BaseModel):
    doc: str = Field(
        ...,
        description="Source document filename",
    )

    section: Optional[str] = Field(
        None,
        description="Section/heading within the document",
    )


class AskResponse(BaseModel):
    answer: str

    sources: list[Source] = []

    fallback: bool = False

    suggested_contact: Optional[str] = None


class IngestStatus(BaseModel):
    status: str

    documents_indexed: int

    chunks_created: int


class DocumentUploadResponse(BaseModel):
    status: str

    filename: str

    documents_indexed: int

    chunks_created: int