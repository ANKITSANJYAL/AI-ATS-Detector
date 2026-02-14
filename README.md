# DocGuard & CareerMatch

A production-grade, full-stack SaaS platform for **AI-generated content detection** and **ATS resume scoring**.

Built with FastAPI, Next.js 14, PostgreSQL, Redis, multi-model ML ensemble, Stripe billing, and Docker-first deployment.

---

## Overview

### 🛡️ AI Document Guard
Upload a document and get a **sentence-level breakdown** of which parts are AI-generated vs. human-written.

- **Multi-model ensemble** — RoBERTa + ChatGPT Detector with Platt calibration
- **Per-sentence linguistic features** — perplexity, burstiness, vocabulary richness, syntactic analysis
- **Exportable reports** — CSV and text format downloads

### 🎯 Strategic Career Match
Upload a resume and job description to get an **ATS compatibility score** with actionable recommendations.

- **Semantic similarity** — sentence embeddings for skill matching
- **Keyword gap analysis** — identify missing skills and keywords
- **Format scoring** — section completeness, ATS parsability
- **Actionable recommendations** — prioritized improvement suggestions

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Next.js 14 (App Router), TypeScript, TailwindCSS, Clerk Auth |
| **Backend** | FastAPI, Python 3.11+, Pydantic v2, Gunicorn |
| **Database** | PostgreSQL 16 (async via SQLAlchemy 2.0 + asyncpg) |
| **Migrations** | Alembic |
| **Cache** | Redis 7 (caching, rate limiting) |
| **AI/ML** | RoBERTa transformer ensemble, OpenAI GPT-4 Turbo, sentence embeddings |
| **Billing** | Stripe (metered subscriptions, checkout, portal) |
| **Auth** | Clerk (JWT, RBAC) |
| **Monitoring** | Sentry (error tracking), structured JSON logging |
| **Infrastructure** | Docker Compose, Nginx reverse proxy, GitHub Actions CI/CD |
| **MCP Server** | TypeScript, Model Context Protocol SDK |

---

## Project Structure

```
├── backend/                 FastAPI application
│   ├── app/
│   │   ├── agents/          DetectorAgent, ATSScorerAgent, Orchestrator
│   │   ├── api/v1/          REST endpoints + billing
│   │   ├── core/            Config, logging, dependencies, sanitization
│   │   ├── db/              SQLAlchemy ORM models + session
│   │   ├── middleware/      Usage tracking, API versioning
│   │   ├── models/          Pydantic schemas
│   │   └── services/        AIClassifier, LLMClient, Billing, Redis, MCP
│   ├── alembic/             Database migrations
│   ├── tests/               Integration + unit tests
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                Next.js 14 application
│   ├── app/
│   │   ├── ai-detector/     Upload & detection results
│   │   ├── ats-checker/     Resume scoring
│   │   ├── dashboard/       Analytics dashboard
│   │   ├── pricing/         Subscription plans
│   │   ├── about/           About page
│   │   ├── contact/         Contact form
│   │   ├── components/      Shared UI components
│   │   └── lib/             Config, export, error utilities
│   ├── __tests__/           Jest tests
│   ├── Dockerfile
│   └── package.json
├── mcp_server/              Model Context Protocol server
│   ├── src/tools/           Filesystem, PostgreSQL, fetch tools
│   ├── Dockerfile
│   └── package.json
├── nginx/                   Reverse proxy config
├── docs/                    Architecture & DR docs
├── scripts/                 SDK generation, utilities
├── docker-compose.yml       Full-stack orchestration
└── .github/workflows/       CI/CD pipeline
```

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Redis 6+
- An OpenAI API key
- Docker & Docker Compose (for containerized deployment)

---

## Quick Start (Local Development)

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your POSTGRES_DSN, REDIS_DSN, OPENAI_API_KEY, CLERK_SECRET_KEY

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install

cp .env.example .env.local
# Edit .env.local with NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY, CLERK_SECRET_KEY, NEXT_PUBLIC_API_URL

npm run dev
```

### 3. MCP Server (optional)

```bash
cd mcp_server
npm install
npm run build
npm start
```

---

## Docker Deployment

Run the entire stack with one command:

```bash
# Copy and configure environment variables
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local

# Start all services
docker compose up --build -d
```

Services:
| Service | Port | Description |
|---------|------|-------------|
| `nginx` | 80, 443 | Reverse proxy + TLS termination |
| `backend` | 8000 | FastAPI API server |
| `frontend` | 3000 | Next.js application |
| `postgres` | 5432 | PostgreSQL database |
| `redis` | 6379 | Redis cache |
| `mcp_server` | 3001 | MCP tools server |

---

## Database Migrations

Migrations are managed by **Alembic**:

```bash
cd backend

# Create a new migration after model changes
alembic revision --autogenerate -m "description"

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `POSTGRES_DSN` | ✅ | PostgreSQL connection string |
| `REDIS_DSN` | ✅ | Redis connection string |
| `OPENAI_API_KEY` | ✅ | OpenAI API key |
| `CLERK_SECRET_KEY` | ✅ | Clerk authentication secret |
| `STRIPE_API_KEY` | ⬜ | Stripe billing (optional) |
| `STRIPE_WEBHOOK_SECRET` | ⬜ | Stripe webhook verification |
| `STRIPE_PRICE_ID_AI_DETECTION` | ⬜ | Stripe metered price ID |
| `STRIPE_PRICE_ID_ATS_SCORING` | ⬜ | Stripe metered price ID |
| `SENTRY_DSN` | ⬜ | Sentry error tracking |
| `ENVIRONMENT` | ⬜ | `development` / `staging` / `production` |

### Frontend (`frontend/.env.local`)

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | ✅ | Clerk publishable key |
| `CLERK_SECRET_KEY` | ✅ | Clerk secret key |
| `NEXT_PUBLIC_API_URL` | ✅ | Backend API URL |
| `NEXT_PUBLIC_SENTRY_DSN` | ⬜ | Sentry DSN for frontend |

---

## API

Interactive documentation available when the backend is running:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Key Endpoints

```
POST /api/v1/documents/upload       Upload a document (PDF, DOCX, TXT)
POST /api/v1/documents/detect       Run AI content detection
POST /api/v1/documents/score        Run ATS resume scoring
GET  /api/v1/documents/history      Fetch analysis history
GET  /api/v1/billing/status         Subscription status
POST /api/v1/billing/checkout       Create Stripe checkout session
GET  /health                        Health check
```

### Response Headers

All API responses include:
- `X-API-Version` — current API version
- `X-Request-ID` — unique request trace ID
- `X-Process-Time` — request processing time (seconds)
- `X-RateLimit-Limit` / `X-RateLimit-Remaining` — rate limit info

---

## CI/CD

GitHub Actions pipeline (`.github/workflows/ci.yml`) runs on every push/PR:

1. **Backend** — lint (ruff), type check (mypy), tests (pytest with PostgreSQL + Redis services)
2. **Frontend** — lint (next lint), type check (tsc), build verification
3. **Docker** — multi-service build verification
4. **Migrations** — Alembic schema check on PRs

---

## Testing

### Backend

```bash
cd backend
pytest tests/ -v --tb=short
pytest tests/ -v --cov=app --cov-report=html    # with coverage
```

### Frontend

```bash
cd frontend
npm test                    # run Jest tests
npm run test:coverage       # with coverage
```

---

## Monitoring & Observability

- **Sentry** — error tracking + performance monitoring (backend + frontend)
- **Structured JSON Logging** — production logs include `app`, `version`, `environment`, `request_id`, `severity`
- **Health Checks** — `/health` (backend) and `/api/health` (frontend)
- **Request Tracing** — `X-Request-ID` header propagated through all services

---

## Billing (Stripe)

- Three-tier subscription: **Free**, **Pro** ($19/mo), **Enterprise** ($99/mo)
- Metered usage billing for AI detection and ATS scoring
- Self-service portal for subscription management
- Usage tracking persisted to PostgreSQL

---

## Security

- **Input sanitization** — all filenames and text inputs sanitized against XSS
- **Rate limiting** — 60 req/min per user with Redis-backed atomic counting
- **CORS validation** — wildcard origins rejected in production
- **Authentication** — Clerk JWT verification on all protected endpoints
- **Security headers** — CSP, HSTS, X-Frame-Options via Nginx

---

## Backup & Disaster Recovery

See [docs/BACKUP_DR.md](docs/BACKUP_DR.md) for the full backup and disaster recovery strategy.

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`pytest` and `npm test`)
4. Commit with conventional commits (`feat:`, `fix:`, `docs:`)
5. Open a Pull Request

---

## License

MIT

---

*Built with ❤️ by the DocGuard Team*
