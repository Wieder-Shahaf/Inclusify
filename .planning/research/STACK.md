# Stack Research

**Project:** Inclusify - LGBTQ+ Inclusive Language Analyzer
**Researched:** 2026-03-08
**Confidence:** HIGH

## Executive Summary

Production NLP analysis platforms in 2026 converge on a specific stack pattern: FastAPI with asyncpg for the backend, Next.js with standalone output for frontend, vLLM for LLM inference, and Azure Container Apps for deployment. This research validates version selections and identifies anti-patterns to avoid.

---

## Backend Stack

### Core Framework

| Technology | Version | Purpose | Confidence |
|------------|---------|---------|------------|
| **FastAPI** | 0.109.0+ | REST API framework | HIGH |
| **Pydantic** | 2.10.0+ | Data validation | HIGH |
| **uvicorn** | 0.30.0+ | ASGI server | HIGH |
| **asyncpg** | 0.30.0+ | PostgreSQL async driver | HIGH |

### Authentication

| Technology | Version | Purpose | Notes |
|------------|---------|---------|-------|
| **FastAPI Users** | 13.x | User management | Migrated from passlib to pwdlib |
| **pwdlib** | 1.0.0+ | Password hashing (Argon2) | Replaces deprecated passlib |
| **python-jose** | 3.3.0+ | JWT encoding/decoding | With cryptography backend |
| **fastapi-sso** | 0.20.0 | Optional SSO (Google/Microsoft) | Feb 2026 release |

### Document Processing

| Technology | Version | Purpose | Notes |
|------------|---------|---------|-------|
| **Docling** | 2.76.0+ | PDF/DOCX parsing | Replaces PyMuPDF, superior layout preservation |

### LLM Inference

| Technology | Version | Purpose | Notes |
|------------|---------|---------|-------|
| **vLLM** | 0.17.0 | LLM serving with LoRA | March 2026 release, native adapter support |

**vLLM Deployment Command (T4 GPU):**
```bash
docker run --gpus all \
  -v /path/to/adapters:/adapters \
  -p 8001:8000 \
  vllm/vllm-openai:v0.17.0 \
  --model lightblue/suzume-llama-3-8B-multilingual \
  --enable-lora \
  --lora-modules inclusify=/adapters/inclusify-lora \
  --dtype float \
  --max-model-len 4096
```

**Critical:** Use `--dtype=float` for T4 GPU (compute 7.5). T4 does NOT support bfloat16.

---

## Frontend Stack

### Framework & Build

| Technology | Version | Purpose | Confidence |
|------------|---------|---------|------------|
| **Next.js** | 16.x | React framework | HIGH |
| **React** | 19.x | UI library | HIGH |
| **TypeScript** | 5.x | Type safety | HIGH |
| **Tailwind CSS** | v4 | Styling | HIGH |

### Docker Build (Multi-Stage)

```dockerfile
# Stage 1: Builder
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: Runner
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs
USER nextjs

EXPOSE 3000
CMD ["node", "server.js"]
```

**Key:** Add `output: 'standalone'` to `next.config.ts` for optimized Docker images.

---

## Database Stack

### PostgreSQL Configuration

| Component | Recommendation | Notes |
|-----------|---------------|-------|
| **Azure PostgreSQL** | Flexible Server | Managed service with auto-backup |
| **Version** | 16+ | Latest features, performance |
| **Authentication** | Managed Identity | No passwords in connection strings |

### Connection Pooling (asyncpg)

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
import asyncpg

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=10,
        max_size=20,
        command_timeout=30,
    )
    yield
    await app.state.pool.close()

app = FastAPI(lifespan=lifespan)
```

---

## Infrastructure Stack

### Azure Services

| Service | Purpose | Configuration |
|---------|---------|---------------|
| **Container Apps** | Frontend + Backend | Serverless containers, auto-scaling |
| **Container Registry** | Docker images | Private registry for builds |
| **PostgreSQL Flexible** | Database | Managed, HA, auto-backups |
| **Key Vault** | Secrets | API keys, DB passwords, SSO config |
| **GPU VM (NC-series)** | vLLM | T4 GPU for inference |

### Deployment Architecture

```
                    ┌─────────────────────────┐
                    │  Azure Container Apps   │
                    │  (Frontend + Backend)   │
                    └───────────┬─────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐      ┌───────────────┐      ┌───────────────┐
│  PostgreSQL   │      │   Key Vault   │      │  T4 GPU VM    │
│  (Flexible)   │      │   (Secrets)   │      │  (vLLM)       │
└───────────────┘      └───────────────┘      └───────────────┘
```

---

## Anti-Patterns to Avoid

| Anti-Pattern | Why Avoid | Use Instead |
|--------------|-----------|-------------|
| **passlib** | Deprecated, breaks in Python 3.13 | pwdlib with Argon2 |
| **PyMuPDF** | Inferior layout preservation | Docling 2.76.0+ |
| **psycopg2 (sync)** | Blocks async event loop | asyncpg 0.30.0+ |
| **--dtype=bfloat16 on T4** | T4 is compute 7.5, needs 8.0+ | `--dtype=float` |
| **vllm:latest tag** | API breaks between versions | Pin to v0.17.0 |
| **Secrets in .env (git)** | Security risk | Azure Key Vault |
| **Single uvicorn worker** | No CPU parallelism | `--workers 4` |
| **AKS for 3 services** | Overkill, steep learning curve | Container Apps |
| **PgBouncer** | asyncpg has built-in pooling | asyncpg.create_pool() |
| **localStorage for tokens** | XSS vulnerable | HttpOnly cookies + memory |

---

## Installation Commands

### Backend (Python 3.11+)

```bash
# Core
pip install fastapi==0.109.0 uvicorn[standard]==0.30.0 pydantic==2.10.0

# Database
pip install asyncpg==0.30.0

# Auth
pip install 'fastapi-users[sqlalchemy]==13.0.0' pwdlib[argon2]==1.0.0 python-jose[cryptography]==3.3.0

# SSO (optional)
pip install fastapi-sso==0.20.0

# Document parsing
pip install docling==2.76.0

# HTTP client
pip install httpx==0.26.0

# Azure
pip install azure-identity==1.19.0
```

### vLLM (T4 VM)

```bash
docker pull vllm/vllm-openai:v0.17.0
```

---

## Version Pins

**DO pin (breaking changes):**
- `vllm==0.17.0`
- `fastapi-users>=13.0.0,<14.0.0`
- `docling>=2.76.0`

**DO NOT pin (security updates):**
- `uvicorn` - latest minor
- `asyncpg` - latest minor
- `httpx` - latest minor

---

## Sources

- vLLM Documentation: https://docs.vllm.ai/
- Docling Project: https://github.com/docling-project
- FastAPI Users v13: https://github.com/fastapi-users/fastapi-users
- Azure Container Apps: https://learn.microsoft.com/azure/container-apps/
- asyncpg Usage: https://magicstack.github.io/asyncpg/

---

*Last updated: 2026-03-08*
