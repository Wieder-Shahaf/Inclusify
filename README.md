# Inclusify

**LGBTQ+ Inclusive Language Analyzer for Academic Texts**

AI-powered platform developed for the Achva LGBT organization. Detects LGBTQphobic, outdated, biased, or pathologizing language in Hebrew and English academic texts — with severity-graded alerts, explanations, inclusive alternatives, and downloadable reports.

![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-blue?logo=typescript&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=next.js)
![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-316192?logo=postgresql&logoColor=white)

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | Next.js 16 (App Router), TypeScript, Tailwind v4, Framer Motion, next-intl |
| **Backend** | FastAPI, Python 3.11, Pydantic v2, asyncpg |
| **Database** | PostgreSQL 16 |
| **ML/AI** | QLoRA fine-tuned Qwen2.5-3B-Instruct, vLLM, Docling |
| **Infrastructure** | Microsoft Azure, Docker, GitHub Actions |

---

## Quick Start

### Prerequisites

- Node.js >= 18, Python >= 3.11, PostgreSQL >= 14

### Database

```bash
createdb inclusify
psql inclusify -f db/schema.sql
psql inclusify -f db/seed.sql
```

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in DB + Azure credentials
uvicorn app.main:app --reload --port 8000
```

API runs at **http://localhost:8000** — docs at `/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App runs at **http://localhost:3000**

---

## API Endpoints

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| `GET` | `/` | Health check | Live |
| `POST` | `/api/v1/ingestion/upload` | Upload PDF/DOCX for text extraction | Live |
| `POST` | `/api/v1/analysis/analyze` | Analyze text for inclusive language | Live (rule-based) |
| `GET` | `/api/v1/admin/analytics` | Usage analytics | Live |
| `GET` | `/api/v1/admin/users` | User management | Live |
| `GET` | `/api/v1/admin/model-metrics` | Model performance metrics | Live |

---

## Project Structure

```
inclusify/
├── frontend/              # Next.js 16 App Router
│   ├── app/[locale]/     # Locale routing (en, he)
│   ├── components/       # UI components
│   ├── lib/              # API client, utilities
│   └── messages/         # i18n translations
│
├── backend/              # FastAPI application
│   ├── app/
│   │   ├── main.py
│   │   ├── core/         # Config, security, middleware
│   │   ├── db/           # Database connection & repositories
│   │   └── modules/      # analysis, ingestion, admin
│   └── tests/
│
├── ml/                   # ML pipelines
│   ├── LoRA_Adapters/   # Fine-tuned model adapters
│   ├── notebooks/
│   └── inference_demo.py
│
├── db/                   # schema.sql + seed.sql (canonical)
├── data/                 # Training datasets
├── docs/                 # Requirements, architecture, threat model
└── scripts/              # Dev utilities
```

---

## Configuration

**`backend/.env`**
```env
DATABASE_URL=postgresql://user:password@localhost:5432/inclusify
AZURE_ML_ENDPOINT=https://your-endpoint.azure.com
AZURE_ML_API_KEY=your_api_key
SECRET_KEY=your-secret-key
CORS_ORIGINS=http://localhost:3000
```

**`frontend/.env.local`**
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_ENABLE_PRIVATE_MODE=true
```

---

## Development

```bash
# Backend tests
cd backend && pytest

# Backend linting
ruff check . && mypy app/

# Frontend linting
cd frontend && npm run lint
```

---

## Project Timeline

| Date | Milestone |
|------|-----------|
| Dec 2025 | Project kickoff, requirements |
| Jan 2026 | ML fine-tuning, POC validation |
| Feb 2026 | Frontend MVP, backend API |
| Mar 2026 | DB integration, vLLM deployment |
| **Apr 15, 2026** | Second results presentation |
| **Jul 8, 2026** | Final presentation (Part B) |
| **Aug 6, 2026** | Documents & fixes submission |

---

## Team

Developed by **Shahaf Wieder, Barak Sharon, Rasha Daher, Lama Zarka, Adan Daxa**  
in partnership with [Achva LGBT Organization](https://achva-lgbt.org.il/) as a final academic project.
