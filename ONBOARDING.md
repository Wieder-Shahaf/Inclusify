# Inclusify — Developer Onboarding Guide

Everything you need to start contributing code from your own PC.

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Clone the Repo](#2-clone-the-repo)
3. [Environment File Setup](#3-environment-file-setup)
4. [Docker Compose Setup](#4-docker-compose-setup)
5. [Verify Everything Works](#5-verify-everything-works)
6. [Daily Workflow](#6-daily-workflow)
7. [Getting Tasks from Trello](#7-getting-tasks-from-trello)
8. [Branch & Commit Strategy](#8-branch--commit-strategy)
9. [CI Pipeline](#9-ci-pipeline)
10. [Role Quick Reference](#10-role-quick-reference)
11. [Azure Services Overview](#11-azure-services-overview)
12. [Troubleshooting](#12-troubleshooting)
13. [Useful Links](#13-useful-links)

---

## 1. Prerequisites

| Tool | Version | Who needs it | macOS | Windows |
|------|---------|-------------|-------|---------|
| Git | Any recent | Everyone | `brew install git` | [git-scm.com](https://git-scm.com) (includes Git Bash) |
| Docker Desktop | Latest | Everyone (recommended path) | [Download](https://www.docker.com/products/docker-desktop/) | [Download](https://www.docker.com/products/docker-desktop/) (enable WSL 2 backend) |
| Node.js | >= 18 | Frontend devs | [nodejs.org](https://nodejs.org) | [nodejs.org](https://nodejs.org) |
| Python | >= 3.11 | Backend devs | [python.org](https://www.python.org) | [python.org](https://www.python.org) (check "Add to PATH" during install) |

> If you're using Docker Compose (recommended), you only need Git + Docker Desktop.
>
> **Windows users:** Use **Git Bash** (installed with Git) or **WSL 2** for all terminal commands in this guide. PowerShell and CMD will work for most commands but some syntax differs.

---

## 2. Clone the Repo

**SSH (preferred):**

```bash
git clone git@github.com:Wieder-Shahaf/inclusify.git
cd inclusify
```

**HTTPS (if you haven't set up SSH keys):**

```bash
git clone https://github.com/Wieder-Shahaf/inclusify.git
cd inclusify
```

---

## 3. Environment File Setup

The `.env` file contains database credentials, API keys, and other secrets.

**Option A — Download from OneDrive (easiest):**

1. Go to the team OneDrive shared folder
2. Download the `env.team` file
3. Place it at the repo root: `inclusify/env.team`
4. Rename the file as: `.env`

**Option B — If you can't access OneDrive:**

```bash
# macOS / Linux / Git Bash
cp .env.example .env

# Windows PowerShell
Copy-Item .env.example .env
```

This creates a `.env` from the template, but it has **placeholder values** — you'll need to ask Shahaf for the real credentials (Google OAuth, JWT secret, etc.) and fill them in manually.

> **Note:** `frontend/.env.local` is already committed with correct defaults — you don't need to touch it.

---

## 4. Docker Compose Setup

This is the easiest way to get everything running. One command starts PostgreSQL, the backend, and the frontend.

**Important:** When using Docker, `PGHOST` must be `postgres` (the Docker service name), not `localhost`. The `env.team` file from OneDrive already has this set correctly. If you created your `.env` manually, make sure `PGHOST=postgres`.

**Start all services:**

```bash
docker compose --profile dev up
```

This starts:
- **PostgreSQL** on port 5432 (auto-initializes schema + seed data)
- **Backend (FastAPI)** on port 8000
- **Frontend (Next.js)** on port 3000

Hot-reload is enabled via volume mounts — edit code and see changes immediately.

**Run in background:**

```bash
docker compose --profile dev up -d
```

**View logs:**

```bash
docker compose logs -f           # all services
docker compose logs -f backend   # backend only
docker compose logs -f frontend  # frontend only
```

**Stop services:**

```bash
docker compose --profile dev down
```

---

## 5. Verify Everything Works

Run through this checklist after setup:

**Health check:**

```bash
curl http://localhost:8000/
# Expected: {"message":"Inclusify API is running","status":"OK"}
```

> **Windows:** `curl` works in PowerShell and Git Bash. Alternatively, just open the URL in your browser.

**Swagger UI:**

Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser — you should see the interactive API docs.

**Frontend:**

Open [http://localhost:3000](http://localhost:3000) — you should see the Inclusify landing page.

**Test the analysis endpoint:**

```bash
# macOS / Linux / Git Bash
curl -X POST http://localhost:8000/api/v1/analysis/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "The homosexual lifestyle is a choice.", "language": "en", "private_mode": true}'
```

```powershell
# Windows PowerShell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/v1/analysis/analyze `
  -ContentType "application/json" `
  -Body '{"text": "The homosexual lifestyle is a choice.", "language": "en", "private_mode": true}'
```

You should get a JSON response with detected issues.

---

## 6. Daily Workflow

```bash
# 1. Pull latest changes
git checkout main
git pull origin main

# 2. Start services
docker compose --profile dev up -d

# 3. Create/switch to your feature branch
git checkout -b feature/lama-docling

# 4. Work on your changes...

# 5. Before pushing, check your code
cd frontend && npm run lint           # frontend
cd backend && ruff check .            # backend

# 6. Commit and push
git add <your-files>
git commit -m "feat(scope): describe what you did"
git push -u origin feature/lama-docling

# 7. Open a Pull Request on GitHub against main
```

---

## 7. Getting Tasks from Trello

Our task board: **[Trello Board](https://trello.com/invite/b/692586a826763eea004c4cc6/ATTIebaedfacb5a27e927a6e7b608ea23943B1C2F6AA/g07finalprojectinformationsystems)**

---

## 8. Branch & Commit Strategy

**Base branch:** `main` (this is where all PRs should target)

**Branch naming:**

```
feature/short-description     # new features
fix/short-description         # bug fixes
docs/short-description        # documentation
refactor/short-description    # code refactoring
```

**Creating a branch:**

```bash
git checkout main
git pull origin main
git checkout -b feature/lama-docling
```

**Commit message format:**

```
type(scope): subject
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

Examples:

```
feat(analysis): add Hebrew rule-based detection
fix(upload): handle empty PDF files gracefully
docs(api): update endpoint documentation
refactor(db): extract query builder helper
```

**Rules:**
- Do NOT add "Co-Authored-By" lines to commits (Some LLMs like Cluade, Gemini, GPT do that automatically in the commit description)
- Keep commits focused — one logical change per commit
- Push your branch and open a PR against `main`

---

## 9. CI Pipeline

Every push and PR triggers GitHub Actions CI automatically.

**What CI checks:**
- `ruff check` — Python linting (backend)
- `pytest` — Python tests (backend)
- `eslint` — TypeScript/JS linting (frontend)
- `next build` — Next.js build verification (frontend)
- Sanity checks

If CI fails on your PR, check the Actions tab for details: [GitHub Actions](https://github.com/Wieder-Shahaf/inclusify/actions)

Fix the issues locally and push again.

---

## 10. Role Quick Reference

| Team Member | Primary Areas | Key Directories | Common Commands |
|-------------|--------------|-----------------|-----------------|
| **Adan** | Frontend, DB | `frontend/`, `db/` | `npm run dev`, `npm run lint` |
| **Rasha** | Backend, Infra | `backend/`, `infra/` | `uvicorn app.main:app --reload`, `ruff check .` |
| **Lama** | Doc Pipeline | `backend/app/modules/ingestion/` | Docling, PDF upload testing |
| **Barak** | ML, Inference | `ml/`, `backend/app/modules/analysis/` | `python inference_demo.py`, vLLM |
| **Shahaf** | PM, Full Stack | Everything | All of the above |

**Tips by role:**

- **Adan:** The canonical DB schema is `db/schema.sql`, not `frontend/prisma/schema.prisma`. Always edit `schema.sql` for DB changes.
- **Rasha:** Use `az acr build` for pushing Docker images — it's faster than building locally and pushing.
- **Lama:** The ingestion module is at `backend/app/modules/ingestion/`. Docling is the document parser (replacing PyMuPDF).
- **Barak:** LoRA adapters are in `ml/LoRA_Adapters/`. The inference demo at `ml/inference_demo.py` works locally for testing.

---

## 11. Azure Services Overview

These are deployed and managed. You don't need to set these up — just be aware they exist.

| Service | Purpose | Details |
|---------|---------|---------|
| **Azure Container Apps** | Hosts frontend + backend containers | Auto-scaled, HTTPS |
| **Azure Container Registry (ACR)** | Stores Docker images | `inclusifyacr.azurecr.io` |
| **Azure PostgreSQL Flexible Server** | Production database | SSL required, `db/schema.sql` is source of truth |
| **Azure VM (T4 GPU)** | vLLM inference server | `52.224.246.238:8001` — runs the fine-tuned model |

---

## 12. Troubleshooting

### Port already in use (5432, 3000, or 8000)

**macOS / Linux:**

```bash
lsof -i :5432    # find what's using the port
kill -9 <PID>    # kill it
```

If port 5432 is taken, you likely have a local PostgreSQL running:

```bash
brew services stop postgresql@16
```

**Windows (PowerShell as Admin):**

```powershell
netstat -ano | findstr :5432    # find what's using the port
taskkill /PID <PID> /F          # kill it
```

Or stop PostgreSQL via the Windows Services app (`services.msc`).

### `PGHOST` must be `postgres`

In Docker Compose, `PGHOST` must be `postgres` (the Docker service name). If you see "connection refused" errors, check your `.env` has `PGHOST=postgres`.

### Docker build fails on Apple Silicon (M1/M2/M3)

Make sure Docker Desktop has Rosetta emulation enabled:
Docker Desktop → Settings → General → "Use Rosetta for x86_64/amd64 emulation on Apple Silicon"

### Database connection failures

```bash
# Check if PostgreSQL is running
docker compose ps
```

### React hydration errors (#418)

Never use `localStorage` or `window` in `useState` initializers. Wrap them in `useEffect` instead. See commit `4b53522` for the fix pattern.

### npm install fails

Try with legacy peer deps:

```bash
cd frontend
npm install --legacy-peer-deps
```

### Backend won't start — module not found

Make sure you're in the right directory and your venv is activated:

```bash
# macOS / Linux / Git Bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

```powershell
# Windows PowerShell
cd backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

### Windows: "running scripts is disabled on this system"

If PowerShell blocks venv activation, run this once as Admin:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## 13. Useful Links

| Resource | URL |
|----------|-----|
| GitHub Repo | [github.com/Wieder-Shahaf/inclusify](https://github.com/Wieder-Shahaf/inclusify) |
| GitHub Actions (CI) | [github.com/Wieder-Shahaf/inclusify/actions](https://github.com/Wieder-Shahaf/inclusify/actions) |
| Local Swagger UI | [localhost:8000/docs](http://localhost:8000/docs) |
| Local Frontend | [localhost:3000](http://localhost:3000) |
| DB Schema | `db/schema.sql` |
| Production Frontend | `https://inclusify-frontend.azurecontainerapps.io` |
| Production Backend | `https://inclusify-backend.azurecontainerapps.io` |
| vLLM GPU VM | `52.224.246.238:8001` |
