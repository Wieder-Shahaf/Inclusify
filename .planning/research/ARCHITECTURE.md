# Architecture Patterns

**Project:** Inclusify - LGBTQ+ Inclusive Language Analyzer
**Researched:** 2026-03-08
**Confidence:** HIGH

## Executive Summary

Production LLM-powered web applications follow a microservices-oriented architecture with clear component boundaries. **Critical insight:** LLM inference MUST be isolated as a separate service (not embedded in the API), document processing uses async patterns, and auth combines stateless JWT with Redis-backed token management.

---

## Component Boundaries

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│    Frontend     │      │     Backend     │      │      vLLM       │
│   (Next.js)     │─────▶│    (FastAPI)    │─────▶│   (GPU VM)      │
│   Port 3000     │ HTTP │    Port 8000    │ HTTP │   Port 8001     │
└─────────────────┘      └────────┬────────┘      └─────────────────┘
                                  │
           ┌──────────────────────┼──────────────────────┐
           │                      │                      │
           ▼                      ▼                      ▼
    ┌─────────────┐        ┌─────────────┐        ┌─────────────┐
    │ PostgreSQL  │        │    Redis    │        │   Docling   │
    │  (asyncpg)  │        │  (sessions) │        │  (parsing)  │
    └─────────────┘        └─────────────┘        └─────────────┘
```

| Component | Responsibility | Communication |
|-----------|---------------|---------------|
| Next.js Frontend | UI, routing, SSR | HTTP → Backend |
| FastAPI Backend | Orchestration, business logic | HTTP → vLLM, asyncpg → DB |
| vLLM Service | LLM inference with LoRA | OpenAI-compatible HTTP |
| PostgreSQL | Persistence (users, docs, findings) | asyncpg pool |
| Redis | Sessions, token revocation, cache | aioredis |
| Docling | Document parsing (PDF/DOCX) | In-process async |

---

## Data Flows

### Flow 1: Document Upload

```
User uploads PDF
       │
       ▼
┌──────────────────┐
│ POST /upload     │
│ (FastAPI)        │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Docling.convert()│   ← Async with run_in_executor for large files
│ (extract text)   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Return text      │
│ + metadata       │
└──────────────────┘
```

### Flow 2: Text Analysis

```
User submits text for analysis
       │
       ▼
┌──────────────────┐
│ POST /analyze    │
│ (FastAPI)        │
└────────┬─────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌────────────┐
│ Rule-  │ │ vLLM HTTP  │   ← httpx.AsyncClient with 30s timeout
│ based  │ │ /completions│
└───┬────┘ └─────┬──────┘
    │            │
    └──────┬─────┘
           │
           ▼
    ┌─────────────┐
    │ Merge results│   ← Rule-based + LLM combined
    │ (dedupe)     │
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │ Store in DB │   ← asyncpg (if not private mode)
    │ Return JSON │
    └─────────────┘
```

### Flow 3: Authentication

```
Login request
       │
       ▼
┌──────────────────┐
│ POST /auth/login │
│ Validate creds   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Generate JWT     │   ← Access token (15min), Refresh token (7d)
│ Store refresh in │
│ Redis + HttpOnly │
│ cookie           │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Return access    │   ← Frontend stores in memory only (not localStorage)
│ token in body    │
└──────────────────┘
```

---

## Core Patterns

### Pattern 1: vLLM Integration

```python
import httpx

class VLLMClient:
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)

    async def analyze(self, text: str, adapter: str = "inclusify") -> dict:
        response = await self.client.post(
            f"{self.base_url}/v1/completions",
            json={
                "model": "lightblue/suzume-llama-3-8B-multilingual",
                "prompt": f"Analyze for inclusive language:\n\n{text}",
                "max_tokens": 1024,
                "temperature": 0.1,
                # LoRA adapter selection
                "extra_body": {"lora_request": {"lora_name": adapter}}
            }
        )
        return response.json()
```

**Key points:**
- 30s timeout prevents cascading failures
- LoRA adapter selected per-request
- Fallback to rule-based if vLLM fails

### Pattern 2: Docling Document Parsing

```python
from docling.document_converter import DocumentConverter
import asyncio

converter = DocumentConverter()

async def parse_document(file_path: str) -> str:
    loop = asyncio.get_event_loop()
    # Run CPU-bound parsing in thread pool
    result = await loop.run_in_executor(
        None,
        lambda: converter.convert(file_path)
    )
    return result.document.export_to_markdown()
```

**Key points:**
- Use `run_in_executor` for CPU-bound parsing
- Large files (>5MB) should use background task queue
- Return task_id for polling

### Pattern 3: JWT + Redis Authentication

```python
from datetime import timedelta
import redis.asyncio as redis

ACCESS_TOKEN_EXPIRE = timedelta(minutes=15)
REFRESH_TOKEN_EXPIRE = timedelta(days=7)

async def create_tokens(user_id: str, redis_client: redis.Redis):
    access_token = create_jwt(user_id, expires=ACCESS_TOKEN_EXPIRE)
    refresh_token = create_jwt(user_id, expires=REFRESH_TOKEN_EXPIRE, type="refresh")

    # Store refresh token in Redis (for revocation)
    await redis_client.setex(
        f"refresh:{refresh_token}",
        int(REFRESH_TOKEN_EXPIRE.total_seconds()),
        user_id
    )

    return access_token, refresh_token
```

**Key points:**
- Access tokens: 15min, stored in memory (React state)
- Refresh tokens: 7 days, HttpOnly cookie + Redis
- Revocation: Delete from Redis on logout

### Pattern 4: asyncpg Connection Pool

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
import asyncpg

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create pool on startup
    app.state.pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=10,
        max_size=20,
        command_timeout=30,
    )
    yield
    # Close pool on shutdown
    await app.state.pool.close()

app = FastAPI(lifespan=lifespan)

# In routes
async def get_db(request: Request) -> asyncpg.Connection:
    async with request.app.state.pool.acquire() as conn:
        yield conn
```

**Key points:**
- Use lifespan (not deprecated startup/shutdown events)
- Pool size: 10-20 for typical load
- Acquire connection per request, release on completion

### Pattern 5: Docker Multi-Stage Builds

**FastAPI Dockerfile:**
```dockerfile
# Build stage
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Runtime stage
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY ./app ./app
ENV PATH=/root/.local/bin:$PATH
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

**Next.js Dockerfile:**
```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
USER nextjs
CMD ["node", "server.js"]
```

**Key points:**
- Multi-stage reduces image size 3-10x
- Next.js standalone mode: ~150MB vs 1GB+
- Non-root user for security

---

## Build Order

Phases ordered by dependencies:

```
Phase 1 (Parallel - No Dependencies)
├── Database schema activation
├── Docker multi-stage builds
└── Azure infrastructure (ACR, PostgreSQL, Redis)

Phase 2 (Depends on Phase 1)
├── JWT authentication with Redis
├── asyncpg connection pool integration
└── Docling document parsing (parallel with auth)

Phase 3 (Depends on Phase 2, Sequential)
├── vLLM deployment on Azure GPU VM
├── vLLM client integration in FastAPI
└── Hybrid detection (rule + LLM merge)

Phase 4 (Depends on Phase 3)
├── Frontend API wiring (remove demo mode)
├── E2E testing with all services
└── Azure Container Apps deployment
```

---

## Anti-Patterns to Avoid

### 1. Embedding Model in FastAPI Process

**Bad:**
```python
model = AutoModelForCausalLM.from_pretrained(...)  # In FastAPI

@app.post("/analyze")
def analyze(text: str):
    return model.generate(text)  # Blocks worker
```

**Why:** Blocks API workers, no batching, VRAM leaks.

**Good:** Separate vLLM service with HTTP API.

### 2. Synchronous Document Parsing

**Bad:**
```python
@router.post("/upload")
def upload_file(file: UploadFile):
    doc = docling.convert(file)  # Blocks for 2-10 seconds
```

**Why:** Blocks entire worker thread.

**Good:** Async with `run_in_executor` or background task.

### 3. Access Tokens in localStorage

**Bad:** Frontend stores JWT in `localStorage`

**Why:** XSS vulnerable - any script can read it.

**Good:** Access tokens in memory, refresh tokens in HttpOnly cookies.

### 4. Single Connection Per Request

**Bad:**
```python
conn = await asyncpg.connect(DATABASE_URL)  # New connection every time
```

**Why:** 50-100ms overhead per connection, exceeds pool limits.

**Good:** Connection pool with lifespan management.

### 5. vLLM Requests Without Timeout

**Bad:**
```python
response = await client.post(url, json=data)  # No timeout
```

**Why:** Hangs if vLLM crashes, cascading failures.

**Good:** 30s timeout + fallback to rule-based.

---

## Scaling Considerations

### 100 Users (MVP)

| Component | Config | Cost |
|-----------|--------|------|
| FastAPI | 1 container, 2 replicas | ~$30/mo |
| vLLM | 1 T4 VM | ~$270/mo |
| PostgreSQL | Flexible B1ms | ~$12/mo |
| Frontend | 1 container | ~$15/mo |

**Total:** ~$300-350/month

### 1K Users (Growth)

| Component | Config |
|-----------|--------|
| FastAPI | 5-10 replicas (autoscale) |
| vLLM | 1-2 GPU VMs |
| PostgreSQL | 4 vCores, read replicas |
| Redis | Standard tier, 1GB |

**Bottleneck:** vLLM GPU capacity (add second VM if >100 req/min)

### 10K Users (Scale)

- Multi-region Container Apps
- 5-10 GPU VMs with load balancer
- PostgreSQL with Citus sharding
- Redis Cluster
- API Gateway (Azure API Management)

---

## Production Readiness Checklist

- [ ] Health check endpoints (GET /health, GET /ready)
- [ ] Structured logging (JSON format)
- [ ] Request tracing (correlation IDs)
- [ ] Graceful shutdown
- [ ] Circuit breakers for external services
- [ ] Connection pool timeouts
- [ ] Rate limiting at API gateway
- [ ] HTTPS everywhere
- [ ] Non-root container users
- [ ] Azure Key Vault for secrets

---

## Sources

- vLLM Documentation: https://docs.vllm.ai/
- FastAPI Best Practices: https://fastapi.tiangolo.com/
- asyncpg Usage: https://magicstack.github.io/asyncpg/
- Docling Project: https://docling-project.github.io/
- Azure Container Apps: https://learn.microsoft.com/azure/container-apps/

---

*Last updated: 2026-03-08*
