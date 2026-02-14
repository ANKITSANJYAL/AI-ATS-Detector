# DocGuard & CareerMatch

A full-stack SaaS platform for AI-generated content detection and ATS (Applicant Tracking System) resume scoring.

## Overview

**AI Content Detector** — Upload a document and get a sentence-level breakdown of which parts are likely AI-generated vs. human-written. Uses a multi-model ensemble (RoBERTa + ChatGPT detector) with Platt calibration and per-sentence linguistic feature analysis.

**ATS Resume Scorer** — Upload a resume and a job description to get an ATS compatibility score. Uses LLM-based skill extraction, semantic similarity via embeddings, keyword matching, format analysis, and gap analysis with actionable recommendations.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, TypeScript, TailwindCSS, Clerk Auth |
| Backend | FastAPI, Python 3.11+, Pydantic v2 |
| Database | PostgreSQL (async via SQLAlchemy + asyncpg) |
| Cache | Redis |
| AI/ML | RoBERTa transformer, OpenAI GPT-4 Turbo, sentence embeddings |
| MCP Server | TypeScript, Model Context Protocol SDK |

## Project Structure

```
backend/          FastAPI application
  app/
    agents/       DetectorAgent, ATSScorerAgent, Orchestrator
    api/v1/       REST endpoints (upload, detect, score)
    services/     AIClassifier, DocumentProcessor, LLMClient, Redis
    models/       Pydantic schemas
    db/           SQLAlchemy ORM models and session
frontend/         Next.js application
  app/
    ai-detector/  Upload and results page
    ats-checker/  Resume scoring page
    components/   AIDetectorResults, ATSResults
mcp_server/       MCP server with filesystem, postgres, and fetch tools
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Redis
- An OpenAI API key

## Setup

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Fill in POSTGRES_DSN, REDIS_DSN, OPENAI_API_KEY, and CLERK_SECRET_KEY
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
# Fill in NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY and CLERK_SECRET_KEY
npm run dev
```

### 3. MCP Server (optional)

```bash
cd mcp_server
npm install
npm run build
npm start
```

## Environment Variables

**Backend** (`backend/.env`):

```
POSTGRES_DSN=postgresql://user:pass@localhost:5432/docguard
REDIS_DSN=redis://localhost:6379/0
OPENAI_API_KEY=sk-...
CLERK_SECRET_KEY=sk_...
ENVIRONMENT=development
DEBUG=true
```

**Frontend** (`frontend/.env.local`):

```
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## API

Once the backend is running, interactive documentation is available at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

Key endpoints:

```
POST /api/v1/documents/upload    Upload a document (PDF, DOCX, TXT, image)
POST /api/v1/documents/detect    Run AI content detection
POST /api/v1/documents/score     Run ATS resume scoring
GET  /health                     Health check
```

## Testing

```bash
cd backend
pytest tests/ -v
```

## License

MIT
