# INCLUSIFY

LGBTQ+ Inclusive Language Analyzer for Academic Texts.

## Monorepo Structure

```
inclusify/
├── frontend/    # Web UI (Next.js + TypeScript)
├── backend/     # API service (FastAPI + Python)
├── ml/          # Data collection & training pipelines
├── shared/      # Shared schemas/utils
├── infra/       # Deployment & Docker configs
└── docs/        # Requirements, architecture, threat model
```

---

## Quick Start

### Prerequisites

- **Node.js** >= 18.0.0
- **Python** >= 3.9
- **npm** or **yarn**

### 1. Install Dependencies

```bash
# Install frontend dependencies (from root)
npm install

# Install backend dependencies
cd backend
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
cd ..
```

---

## Running the Application

### Frontend (Next.js)

From the root directory:
```bash
npm run dev
```

Or from the frontend directory:
```bash
cd frontend
npm run dev
```

The frontend will be available at **http://localhost:3000**

### Backend (FastAPI)

From the backend directory:
```bash
cd backend
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
python -m uvicorn app.main:app --reload --port 8000
```

Or using the shorthand:
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

The backend will be available at **http://localhost:8000**

- API docs (Swagger): http://localhost:8000/docs
- Alternative docs (ReDoc): http://localhost:8000/redoc

### Running Both Together

Open two terminal windows:

**Terminal 1 - Frontend:**
```bash
npm run dev
```

**Terminal 2 - Backend:**
```bash
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| POST | `/api/v1/ingestion/upload` | Upload PDF and extract text |
| POST | `/api/v1/analysis/analyze` | Analyze text for inclusive language |

### Example: Analyze Text

```bash
curl -X POST http://localhost:8000/api/v1/analysis/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "The text to analyze"}'
```

---

## Frontend Features

- **Next.js 16** with App Router
- **TypeScript** for type safety
- **Tailwind CSS v4** for styling
- **next-intl** for internationalization (English & Hebrew with RTL support)
- **shadcn/ui** for accessible components
- **Text highlights** with clickable annotations that open a side panel

## Backend Features

- **FastAPI** with async support
- **PyMuPDF** for PDF text extraction
- **Pydantic** for request/response validation
- Auto-generated API documentation

---

## Available Scripts

### From Root

| Command | Description |
|---------|-------------|
| `npm run dev` | Start frontend dev server |
| `npm run build` | Build frontend for production |
| `npm run start` | Start frontend production server |
| `npm run lint` | Lint frontend code |

### From Backend Directory

| Command | Description |
|---------|-------------|
| `uvicorn app.main:app --reload` | Start backend dev server |
| `uvicorn app.main:app` | Start backend production server |
| `pytest` | Run tests (when available) |

---

## Project Structure

### Frontend
```
frontend/
├── app/[locale]/          # Locale-based routing (en, he)
│   ├── page.tsx           # Home page
│   ├── analyze/           # Text analysis page
│   ├── glossary/          # Glossary page
│   └── admin/             # Admin dashboard
├── components/            # React components
├── i18n/                  # Internationalization config
├── messages/              # Translation files (en.json, he.json)
└── lib/                   # Utilities
```

### Backend
```
backend/
├── app/
│   ├── main.py            # FastAPI app entry point
│   ├── core/
│   │   └── config.py      # Configuration settings
│   └── modules/
│       ├── analysis/      # Text analysis endpoints
│       │   └── router.py
│       └── ingestion/     # File upload endpoints
│           └── router.py
├── tests/                 # Test files
└── requirements.txt       # Python dependencies
```

---

## Environment Variables

Create a `.env` file in the backend directory for configuration:

```env
# Backend .env (backend/.env)
AZURE_ENDPOINT=your_azure_endpoint
AZURE_API_KEY=your_api_key
DEBUG=true
```

---

## Troubleshooting

### Port already in use

Frontend (3000):
```bash
lsof -i :3000 | grep LISTEN | awk '{print $2}' | xargs kill -9
```

Backend (8000):
```bash
lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill -9
```

### Python virtual environment issues

```bash
cd backend
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

