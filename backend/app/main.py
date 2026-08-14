from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.ask import router as ask_router
from app.routes.ingest import router as ingest_router

app = FastAPI(
    title="OnboardBot API",
    description="Company-knowledge RAG chatbot for new hire onboarding",
    version="0.1.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Primary Routers
app.include_router(ask_router)
app.include_router(ingest_router)

# Vercel API prefix routers (/api/ask, /api/ingest)
app.include_router(ask_router, prefix="/api")
app.include_router(ingest_router, prefix="/api")


@app.get("/")
@app.get("/api")
async def root():
    return {
        "status": "ok",
        "service": "OnboardBot API",
        "version": "0.1.0",
    }


@app.get("/health")
@app.get("/api/health")
async def health():
    return {"status": "healthy"}