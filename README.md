# DocGuard & CareerMatch

A full-stack SaaS platform for AI-generated content detection and ATS resume scoring.

Built with FastAPI, Next.js 14, PostgreSQL, Redis, and a multi-model ML ensemble.

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Local Development Setup](#local-development-setup)
  - [1. Clone the Repository](#1-clone-the-repository)
  - [2. Start PostgreSQL and Redis](#2-start-postgresql-and-redis)
  - [3. Backend Setup](#3-backend-setup)
  - [4. Frontend Setup](#4-frontend-setup)
  - [5. Verify Everything Works](#5-verify-everything-works)
- [Docker Deployment](#docker-deployment)
- [Environment Variables Reference](#environment-variables-reference)
- [Database Migrations](#database-migrations)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [MCP Server (Optional)](#mcp-server-optional)
- [License](#license)

## Overview

### AI Document Guard

Upload a document (PDF, DOCX, or plain text) and get a sentence-level breakdown of
which parts are AI-generated versus human-written.

- Multi-model ensemble using RoBERTa-based transformers with Platt calibration
- Per-sentence linguistic feature analysis (vocabulary diversity, formality, complexity)
- Exportable reports in CSV and text format

### Strategic Career Match

Upload a resume and a job description to get an ATS compatibility score with
actionable recommendations.

- Keyword gap analysis to identify missing skills
- Section completeness and ATS parsability scoring
- Prioritized improvement suggestions

## Tech Stack

| Layer          | Technology                                                     |
| -------------- | -------------------------------------------------------------- |
| Frontend       | Next.js 14 (App Router), TypeScript, TailwindCSS, Clerk Auth  |
| Backend        | FastAPI, Python 3.11+, Pydantic v2                             |
| Database       | PostgreSQL 16, async via SQLAlchemy 2.0 + asyncpg              |
| Migrations     | Alembic                                                        |
| Cache          | Redis 7 (caching, rate limiting)                               |
| AI/ML          | RoBERTa transformer ensemble, OpenAI GPT-4 Turbo               |
| Billing        | Stripe (metered subscriptions)                                 |
| Auth           | Clerk (JWT verification)                                       |
| Infrastructure | Docker Compose, Nginx reverse proxy                            |

## Project Structure

```
.
├── backend/                    FastAPI application
│   ├── app/
│   │   ├── agents/             DetectorAgent, ATSScorerAgent, Orchestrator
│   │   ├── api/v1/             REST endpoints
│   │   ├── core/               Config, logging, dependencies
│   │   ├── db/                 SQLAlchemy ORM models and session
│   │   ├── middleware/         Usage tracking, API versioning
│   │   ├── models/             Pydantic request/response schemas
│   │   └── services/           AIClassifier, LLMClient, Redis, Billing
│   ├── alembic/                Database migrations
│   ├── tests/                  Integration and unit tests
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                   Next.js 14 application
│   ├── app/
│   │   ├── ai-detector/        Upload and detection results
│   │   ├── ats-checker/        Resume scoring
│   │   ├── dashboard/          Analytics dashboard
│   │   ├── pricing/            Subscription plans
│   │   ├── components/         Shared UI components
│   │   └── lib/                Config, export utilities
│   ├── Dockerfile
│   └── package.json
├── mcp_server/                 Model Context Protocol server (optional)
├── nginx/                      Reverse proxy config (Docker only)
├── docker-compose.yml          Full-stack orchestration
└── docs/                       Architecture documentation
```

## Prerequisites

Install these before proceeding. The versions listed are the minimum tested versions.

| Dependency | Version | Install                                              |
| ---------- | ------- | ---------------------------------------------------- |
| Python     | 3.11+   | https://www.python.org/downloads/                    |
| Node.js    | 18+     | https://nodejs.org/                                  |
| PostgreSQL | 14+     | `brew install postgresql@16` (macOS) or see below    |
| Redis      | 6+      | `brew install redis` (macOS) or see below            |
| Git        | 2.0+    | https://git-scm.com/                                 |

**PostgreSQL install options:**

```bash
# macOS
brew install postgresql@16
brew services start postgresql@16

# Ubuntu / Debian
sudo apt update && sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql

# Windows
# Download the installer from https://www.postgresql.org/download/windows/
```

**Redis install options:**

```bash
# macOS
brew install redis
brew services start redis

# Ubuntu / Debian
sudo apt update && sudo apt install redis-server
sudo systemctl start redis-server

# Windows (WSL recommended)
# Use WSL2 and follow the Ubuntu instructions above.
```

## Local Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/ANKITSANJYAL/AI-ATS-Detector.git
cd AI-ATS-Detector
```

### 2. Start PostgreSQL and Redis

Make sure both services are running, then create the application database.

```bash
# Verify PostgreSQL is running
pg_isready
# Expected output: /tmp:5432 - accepting connections

# Verify Redis is running
redis-cli ping
# Expected output: PONG
```

Create the database and user. If `psql postgres` fails with a role error, try
`psql -U postgres` (Linux) or `sudo -u postgres psql` instead.

```bash
psql postgres -c "CREATE USER docguard WITH PASSWORD 'docguard_secret';"
psql postgres -c "CREATE DATABASE docguard OWNER docguard;"
psql postgres -c "GRANT ALL PRIVILEGES ON DATABASE docguard TO docguard;"
```

### 3. Backend Setup

```bash
cd backend
```

**Create and activate a virtual environment:**

```bash
python3 -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows
```

**Install Python dependencies:**

```bash
pip install -r requirements.txt
```

The `torch` package is approximately 2 GB. If `pip install` is slow or fails
on torch, install the CPU-only build first:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

**Configure environment variables:**

```bash
cp .env.example .env
```

Open `backend/.env` in a text editor and set the required values:

```dotenv
# Required — must match the database created in step 2
POSTGRES_DSN=postgresql://docguard:docguard_secret@localhost:5432/docguard
REDIS_DSN=redis://localhost:6379/0

# Development mode — bypasses Clerk authentication so you can test
# without a Clerk account. Remove or set to false in production.
ENVIRONMENT=development
DEBUG=true

# Required only for ATS resume scoring (uses GPT-4 for analysis).
# AI content detection works without this key.
OPENAI_API_KEY=sk-your-openai-key-here
```

All other variables in `.env.example` (Stripe, Sentry, Anthropic) are optional
and can be left at their placeholder values for local development.

**Run database migrations:**

```bash
alembic upgrade head
```

This creates the required tables: `documents`, `detection_results`, `ats_results`,
and `billing_records`. If this command fails, see
[Troubleshooting](#alembic-upgrade-head-fails-with-connection-refused).

**Start the backend server:**

```bash
uvicorn app.main:app --reload --port 8000
```

On first startup the server downloads two ML models (~500 MB each) from
Hugging Face. You will see log output like:

```
Loading AI detection model: roberta-base-openai-detector
Loaded model: roberta-base-openai-detector
Loading AI detection model: Hello-SimpleAI/chatgpt-detector-roberta
Loaded model: Hello-SimpleAI/chatgpt-detector-roberta
AI detection models pre-warmed
Application startup complete
```

Wait until you see `Application startup complete` before using the API.

### 4. Frontend Setup

Open a **new terminal** (keep the backend running in the previous one).

```bash
cd frontend

npm install

cp .env.example .env.local
```

Open `frontend/.env.local` and verify:

```dotenv
NEXT_PUBLIC_API_URL=http://localhost:8000

# Clerk keys — leave as placeholders if you do not have a Clerk account.
# The AI Detector and ATS Checker pages are public routes and work without
# authentication. Sign-in and sign-up pages will not function without valid keys.
# Get free keys at https://clerk.com if needed.
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_your-key
CLERK_SECRET_KEY=sk_test_your-key
```

Start the dev server:

```bash
npm run dev
```

The frontend is now available at [http://localhost:3000](http://localhost:3000).

### 5. Verify Everything Works

1. Open [http://localhost:8000/health](http://localhost:8000/health). You should see
   a JSON response with `"status": "healthy"` or `"status": "degraded"`.

2. Open [http://localhost:8000/docs](http://localhost:8000/docs) for the interactive
   Swagger UI.

3. Open [http://localhost:3000](http://localhost:3000) for the frontend.

4. Navigate to the AI Detector page, upload a PDF or DOCX file, and confirm that
   you get sentence-level results with real confidence percentages (not 50% on
   every sentence).

## Docker Deployment

Docker Compose runs the full stack (PostgreSQL, Redis, backend, frontend, Nginx)
with a single command. You do not need to install PostgreSQL or Redis locally when
using Docker.

```bash
# Copy environment files
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

Edit `backend/.env` and set at minimum your `OPENAI_API_KEY` (for ATS scoring).
The Docker Compose file automatically configures `POSTGRES_DSN`, `REDIS_DSN`, and
`ENVIRONMENT` for the backend container, so you do not need to change those.

```bash
# Build and start all services
docker compose up --build -d

# Watch backend logs during first startup (model download takes a few minutes)
docker compose logs -f backend
```

Wait until the backend logs show `Application startup complete`.

| Service    | URL                   | Description                 |
| ---------- | --------------------- | --------------------------- |
| Nginx      | http://localhost      | Reverse proxy (port 80)     |
| Backend    | http://localhost:8000 | FastAPI API server           |
| Frontend   | http://localhost:3000 | Next.js application          |
| PostgreSQL | localhost:5432        | Database (user: `docguard`) |
| Redis      | localhost:6379        | Cache                        |

To stop all services:

```bash
docker compose down          # Stop containers, keep data
docker compose down -v       # Stop and delete all data (resets database)
```

**Note:** The nginx service mounts `./nginx/ssl/` for TLS certificates. For local
testing this directory is empty (contains only a `.gitkeep`). If nginx fails to
start, you can safely comment out the nginx service in `docker-compose.yml` and
access the backend and frontend directly on ports 8000 and 3000.

## Environment Variables Reference

### Backend (`backend/.env`)

| Variable                         | Required   | Default                    | Description                                      |
| -------------------------------- | ---------- | -------------------------- | ------------------------------------------------ |
| `POSTGRES_DSN`                   | Yes        | -                          | PostgreSQL connection string                      |
| `REDIS_DSN`                      | Yes        | `redis://localhost:6379/0` | Redis connection string                           |
| `OPENAI_API_KEY`                 | For ATS    | -                          | OpenAI API key (required for ATS scoring only)    |
| `ENVIRONMENT`                    | No         | `development`              | `development`, `staging`, or `production`         |
| `DEBUG`                          | No         | `false`                    | `true` skips Clerk auth in development mode       |
| `CLERK_SECRET_KEY`               | Production | -                          | Clerk secret key for JWT verification             |
| `CLERK_DOMAIN`                   | Production | -                          | Clerk domain (e.g., `your-app.clerk.accounts.dev`)|
| `STRIPE_API_KEY`                 | No         | -                          | Stripe secret key for billing                     |
| `STRIPE_WEBHOOK_SECRET`          | No         | -                          | Stripe webhook signing secret                     |
| `STRIPE_PRICE_ID_AI_DETECTION`   | No         | -                          | Stripe metered price ID for AI detection          |
| `STRIPE_PRICE_ID_ATS_SCORING`    | No         | -                          | Stripe metered price ID for ATS scoring           |
| `SENTRY_DSN`                     | No         | -                          | Sentry DSN for error tracking                     |
| `ANTHROPIC_API_KEY`              | No         | -                          | Anthropic API key (alternative LLM provider)      |
| `LOG_LEVEL`                      | No         | `INFO`                     | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`   |

### Frontend (`frontend/.env.local`)

| Variable                            | Required   | Default                 | Description                    |
| ----------------------------------- | ---------- | ----------------------- | ------------------------------ |
| `NEXT_PUBLIC_API_URL`               | Yes        | `http://localhost:8000` | Backend API URL                |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | For auth   | -                       | Clerk publishable key          |
| `CLERK_SECRET_KEY`                  | For auth   | -                       | Clerk secret key               |
| `NEXT_PUBLIC_SENTRY_DSN`            | No         | -                       | Sentry DSN for frontend errors |

## Database Migrations

Migrations are managed by Alembic. Run all commands from the `backend/` directory
with the virtual environment activated.

```bash
cd backend
source .venv/bin/activate

# Apply all pending migrations
alembic upgrade head

# Create a new migration after changing db/models.py
alembic revision --autogenerate -m "description of change"

# Roll back the last migration
alembic downgrade -1

# View migration history
alembic history
```

Alembic reads the database URL from `backend/.env` via `app.core.config`. You do
not need to edit `alembic.ini` directly.

## API Reference

Interactive documentation is available when the backend is running:

- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Endpoints

| Method | Path                            | Description                          |
| ------ | ------------------------------- | ------------------------------------ |
| POST   | `/api/v1/documents/upload`      | Upload a document (PDF, DOCX, TXT)   |
| POST   | `/api/v1/documents/detect`      | Run AI content detection             |
| POST   | `/api/v1/documents/score`       | Run ATS resume scoring               |
| GET    | `/api/v1/documents/history`     | Fetch analysis history               |
| GET    | `/api/v1/billing/status`        | Subscription status                  |
| POST   | `/api/v1/billing/checkout`      | Create Stripe checkout session       |
| GET    | `/health`                       | Health check                         |

### Response Headers

All responses include:

| Header                  | Description                        |
| ----------------------- | ---------------------------------- |
| `X-API-Version`         | Current API version                |
| `X-Request-ID`          | Unique request trace ID            |
| `X-Process-Time`        | Request duration in seconds        |
| `X-RateLimit-Limit`     | Rate limit ceiling                 |
| `X-RateLimit-Remaining` | Remaining requests in window       |

## Testing

### Backend

```bash
cd backend
source .venv/bin/activate

pytest tests/ -v --tb=short
pytest tests/ -v --cov=app --cov-report=html    # with coverage report
```

Tests require running PostgreSQL and Redis instances.

### Frontend

```bash
cd frontend

npm test                     # Run Jest tests
npm run test:coverage        # Run with coverage
```

## Troubleshooting

### `pip install` fails or hangs on torch

`torch` is approximately 2 GB. Install the CPU-only variant to reduce download
size and avoid CUDA-related build issues:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

### `alembic upgrade head` fails with "connection refused"

PostgreSQL is not running or the connection string in `backend/.env` is wrong.

```bash
# Check that PostgreSQL is running
pg_isready

# Verify your .env has the correct DSN
grep POSTGRES_DSN backend/.env

# Test the connection directly
psql postgresql://docguard:docguard_secret@localhost:5432/docguard -c "SELECT 1;"
```

### `alembic upgrade head` fails with "database docguard does not exist"

Create the database first. See [step 2](#2-start-postgresql-and-redis) above.

### Backend logs show "No AI detection models loaded"

The `transformers` and `torch` packages are missing from the Python environment.

```bash
cd backend
source .venv/bin/activate

# Check if they are installed
pip list | grep -E "transformers|torch"

# Install if missing
pip install transformers torch sentencepiece
```

### Backend logs show "Redis connection failed" or health check returns unhealthy

Redis is not running.

```bash
redis-cli ping    # Should print PONG

# Start Redis
brew services start redis            # macOS
sudo systemctl start redis-server    # Ubuntu / Debian
```

### Frontend shows network errors or CORS errors

The backend is not running, or the API URL in the frontend config is wrong.

```bash
# Check that the backend is reachable
curl http://localhost:8000/health

# Verify the frontend .env.local
grep NEXT_PUBLIC_API_URL frontend/.env.local
# Expected: NEXT_PUBLIC_API_URL=http://localhost:8000
```

### `psql: FATAL: role "docguard" does not exist`

The database user was not created. The command depends on your PostgreSQL setup:

```bash
# macOS (Homebrew — default superuser is your OS username)
psql postgres -c "CREATE USER docguard WITH PASSWORD 'docguard_secret';"

# Linux (default superuser is "postgres")
sudo -u postgres psql -c "CREATE USER docguard WITH PASSWORD 'docguard_secret';"
```

### Docker: nginx fails to start

The nginx service expects TLS certificates in `./nginx/ssl/`. For local testing
without TLS, comment out the nginx service in `docker-compose.yml` and access the
backend and frontend directly on ports 8000 and 3000.

### All AI detection results show 50% with "No models available"

The ML models did not load during backend startup. This usually means `transformers`
or `torch` is not installed. Restart the backend after installing them:

```bash
cd backend
source .venv/bin/activate
pip install transformers torch sentencepiece
uvicorn app.main:app --reload --port 8000
```

Watch the logs for `Loaded model:` and `AI detection models pre-warmed` messages.

## MCP Server (Optional)

The Model Context Protocol server provides filesystem, PostgreSQL, and HTTP fetch
tools for LLM agents. It is not required for the main application to function.

```bash
cd mcp_server
npm install
cp .env.example .env
# Edit .env — set DATABASE_URL to match your PostgreSQL setup

npm run build
npm start
```

The server starts on port 3001 by default.

## License

MIT