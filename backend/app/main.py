from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware

from app.routes.ask import router as ask_router
from app.routes.ingest import router as ingest_router


app = FastAPI(
    title="OnboardBot API",
    description=(
        "Company-knowledge RAG chatbot "
        "for new hire onboarding"
    ),
    version="0.1.0",
)


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Routes
# ---------------------------------------------------------

app.include_router(
    ask_router
)

app.include_router(
    ingest_router
)


# ---------------------------------------------------------
# Health
# ---------------------------------------------------------

@app.get("/")
async def root():

    return {
        "status": "ok",
        "service": "OnboardBot API",
    }


@app.get("/health")
async def health():

    return {
        "status": "healthy"
    }