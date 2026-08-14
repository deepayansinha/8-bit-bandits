from fastapi import APIRouter, HTTPException

from app.ingest import run_ingestion
from app.schemas import IngestStatus


router = APIRouter(
    prefix="/ingest",
    tags=["Documents"],
)


@router.post(
    "",
    response_model=IngestStatus,
)
async def ingest_documents():

    try:

        result = run_ingestion()

        return result

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Ingestion failed: {exc}",
        )