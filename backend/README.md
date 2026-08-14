# OnboardBot 🤖

**AI in Workplace — VibeForge Hackathon Submission**

OnboardBot is a company-knowledge RAG chatbot that helps new hires get instant, cited answers
from internal docs (HR policy, IT setup, code of conduct, benefits, etc.) instead of pinging
five different people on Slack. If it doesn't know the answer, it says so honestly and points
the new hire to the right team instead of hallucinating.

## Why this matters
New hires waste hours in their first weeks hunting for basic answers scattered across PDFs,
wikis, and people's inboxes. OnboardBot centralizes that knowledge into a single chat interface
with **source-cited answers** and **honest fallbacks** when the docs don't cover something.

## Tech Stack
- **Backend:** FastAPI (Python)
- **Vector Store:** FAISS / ChromaDB
- **LLM:** Claude / OpenAI API (swappable)
- **Frontend:** React (or plain HTML/CSS/JS)
- **Embeddings:** OpenAI / Sentence-Transformers

## Project Structure
```
onboardbot/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app entrypoint
│   │   ├── ingest.py        # Doc loading, chunking, embedding
│   │   ├── rag.py           # Retrieval + LLM answer generation
│   │   ├── prompts.py       # Prompt templates (grounding + fallback)
│   │   ├── schemas.py       # Pydantic request/response models
│   │   └── routes/
│   │       └── ask.py       # /ask endpoint
│   ├── data/
│   │   └── docs/            # Sample company policy docs
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   ├── public/
│   └── package.json
└── README.md
```

## Team & Ownership
| Person | Owns | Key files |
|---|---|---|
| **A — Ingestion & Vector Pipeline** | Doc parsing, chunking, embeddings, vector store | `backend/app/ingest.py`, `backend/data/docs/` |
| **B — RAG & Backend** | Retrieval logic, LLM prompt, fallback handling, API | `backend/app/rag.py`, `backend/app/prompts.py`, `backend/app/routes/ask.py` |
| **C — Frontend & Deployment** | Chat UI, citation display, hosting, demo video | `frontend/`, deployment configs |

## Setup

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env      # add your API key
python -m app.ingest       # build the vector index from data/docs
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## API Contract

**POST** `/ask`
```json
{ "question": "How many sick days do I get?" }
```

**Response**
```json
{
  "answer": "You get 12 paid sick days per year, which reset every January 1st.",
  "sources": [
    { "doc": "Leave Policy.pdf", "section": "3.2 Sick Leave" }
  ],
  "fallback": false
}
```

When the docs don't cover the question:
```json
{
  "answer": "I don't have information on that in the current docs. You should check with HR directly.",
  "sources": [],
  "fallback": true,
  "suggested_contact": "HR"
}
```

## Demo Video Script (< 2 min)
1. Problem statement (10s)
2. Show docs loaded into the system (20s)
3. Ask a well-covered question → cited answer (30s)
4. Ask an out-of-scope question → graceful fallback (30s)
5. Close with stack + team name (10s)

## License
Built for VibeForge Hackathon 2026.
