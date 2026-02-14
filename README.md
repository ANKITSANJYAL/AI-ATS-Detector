# DocGuard & CareerMatch

**Professional AI-powered document analysis and ATS scoring platform built with Google-standard practices.**

## 🚀 Features

### 🛡️ AI Document Guard
Forensic linguistic analysis to detect AI-generated content with enterprise-grade accuracy.

- **Multi-dimensional analysis**: Sentence complexity, vocabulary diversity, coherence scoring
- **High accuracy**: Advanced LLM-powered feature extraction
- **Detailed reports**: Confidence scores and flagged sections

### 🎯 Strategic Career Match
ATS compatibility scoring with semantic analysis and actionable recommendations.

- **Semantic matching**: AI-powered similarity analysis beyond keyword matching
- **Skills gap analysis**: Identify missing qualifications
- **Actionable insights**: Specific recommendations to improve match scores

## 🏗️ Architecture

### Zero File Clutter
- **Database-first**: All data stored in PostgreSQL/Redis
- **Self-documenting**: OpenAPI/Swagger with Pydantic Field descriptions
- **No junk files**: No .txt, .log, or unnecessary .md files

### Service-Agent Pattern
```
┌─────────────┐
│  Next.js    │  ← Material 3 UI
│  Frontend   │
└──────┬──────┘
       │
┌──────▼──────┐
│   FastAPI   │  ← Self-documenting REST API
│   Backend   │
└──────┬──────┘
       │
┌──────▼──────┐
│  Agents     │  ← AI Detection & ATS Scoring
│ Orchestrator│
└──────┬──────┘
       │
┌──────▼──────┐
│ MCP Server  │  ← Filesystem, DB, Fetch tools
└─────────────┘
```

### Technology Stack

**Backend:**
- FastAPI 0.109+ (Python 3.11+)
- Pydantic 2.5+ for type safety
- OpenAI / Anthropic LLMs
- Redis for caching & job queue
- PostgreSQL for persistent storage
- Celery for async processing

**Frontend:**
- Next.js 14+ with TypeScript
- Clerk authentication
- TailwindCSS + Material 3 design
- Axios for API calls

**MCP Server:**
- TypeScript with Express
- Model Context Protocol SDK
- PostgreSQL client

## 📦 Installation

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your credentials

# Run server
uvicorn app.main:app --reload
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Set environment variables
cp .env.example .env.local
# Edit .env.local with your Clerk keys

# Run development server
npm run dev
```

### MCP Server Setup

```bash
cd mcp_server

# Install dependencies
npm install

# Build TypeScript
npm run build

# Run server
npm start
```

## 🔑 Environment Variables

### Backend (.env)
```bash
# Application
ENVIRONMENT=development
DEBUG=true

# Database
POSTGRES_DSN=postgresql://user:pass@localhost:5432/docguard
REDIS_DSN=redis://localhost:6379/0

# LLM APIs
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Authentication
CLERK_SECRET_KEY=sk_...

# Billing
STRIPE_API_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

### Frontend (.env.local)
```bash
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 🧪 Testing

### Run Test Suite
```bash
cd backend
pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov-report=html

# Run validation tests (Spearman's Rho)
pytest tests/test_ats_scorer.py::TestATSScorerValidation -v
```

### Validation Protocol
The ATS scorer is validated using **Spearman's Rho correlation**:
- Measures rank correlation between predicted and ground-truth scores
- Success threshold: ρ > 0.7
- Results output to console only (no files created)

## 📚 API Documentation

Once the backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

All endpoints are self-documented with:
- Request/response schemas
- Field descriptions
- Example payloads
- Error responses

### Key Endpoints

```
POST /api/v1/documents/upload       # Upload document
POST /api/v1/documents/detect       # AI detection analysis
POST /api/v1/documents/score        # ATS scoring analysis
POST /api/v1/jobs/                  # Create job description
POST /api/v1/webhooks/stripe        # Stripe webhooks
GET  /health                        # Health check
```

## 💳 Billing Integration

**Metered Billing via Stripe:**
- Usage automatically tracked per analysis
- Billing events sent to Stripe API
- Webhook handlers for payment events
- No file-based logging of usage

## 🚢 Deployment

### Backend (Docker)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]
```

### Frontend (Vercel)
```bash
# Deploy to Vercel
vercel --prod

# Or use Vercel GitHub integration
```

### Environment
- Backend: Railway, Render, or AWS ECS
- Frontend: Vercel or Netlify
- Database: Supabase or AWS RDS
- Redis: Upstash or AWS ElastiCache

## 🎯 Type Safety

**100% Type Coverage:**
- Backend: Pydantic models + Python type hints
- Frontend: TypeScript strict mode
- MCP Server: TypeScript with strict checks

## 🔒 Security

- JWT authentication via Clerk
- Rate limiting (60 req/min/user)
- Input validation via Pydantic
- CORS configuration
- Webhook signature verification

## 📊 Monitoring

Structured logging compatible with:
- Google Cloud Logging
- Datadog
- New Relic
- CloudWatch

## 🤝 Contributing

1. Follow Google Python Style Guide
2. Use Black for formatting
3. Add Pydantic Field descriptions
4. Update tests for new features
5. No file-based outputs

## 📄 License

MIT License - See LICENSE file for details

## 🙋 Support

For issues or questions:
- Open a GitHub issue
- Check API documentation at `/docs`
- Review test suite for examples

---

**Built with modern best practices: Type-safe, self-documenting, database-first, zero clutter.**
