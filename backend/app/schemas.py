"""
API contract for OnboardBot.
Everyone on the team should code against these shapes.
If you need to change a field, shout in the group chat first —
frontend and backend both depend on this staying stable.
"""

from pydantic import BaseModel, Field
from typing import Optional


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="The new hire's question")


class Source(BaseModel):
    doc: str = Field(..., description="Source document filename, e.g. 'Leave Policy.pdf'")
    section: Optional[str] = Field(None, description="Section/heading within the doc, if known")


class AskResponse(BaseModel):
    answer: str
    sources: list[Source] = []
    fallback: bool = False
    suggested_contact: Optional[str] = None  # e.g. "HR", "IT", "Manager"


class IngestStatus(BaseModel):
    status: str
    documents_indexed: int
    chunks_created: int
