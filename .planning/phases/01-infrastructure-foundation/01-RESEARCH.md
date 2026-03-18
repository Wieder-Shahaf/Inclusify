# Phase 1: Infrastructure Foundation - Research

**Researched:** 2026-03-09
**Domain:** Docker containerization, Azure infrastructure, asyncpg database pooling
**Confidence:** HIGH

## Summary

This phase establishes the containerized development and deployment foundation for Inclusify. The core work involves creating Docker multi-stage builds for both Next.js 16 and FastAPI services, implementing asyncpg connection pooling with FastAPI's lifespan handler, and provisioning Azure Container Registry plus PostgreSQL Flexible Server.

The existing codebase already has the database layer written but inactive (`backend/app/db/repository.py`, `deps.py`, `connection.py`). The main work is activating the pool, adding the lifespan handler, and wrapping everything in Docker. Azure provisioning uses CLI scripts (`az` commands) per user decision, avoiding Terraform complexity.

**Primary recommendation:** Use single `docker-compose.yml` with profiles, FastAPI lifespan handler for asyncpg pool, and Azure CLI bash scripts for infrastructure provisioning.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Single `docker-compose.yml` with profiles for dev/prod (not separate files)
- Include PostgreSQL container for local dev (`docker compose up` gives everything)
- Multi-stage builds for frontend (build stage compiles Next.js, final stage copies .next/standalone)
- Hot-reload via volume mounts for local development
- PostgreSQL tier: Burstable B1ms (1 vCore, 2GB RAM, ~$15/month, student credits friendly)
- Secrets management: Container Apps secrets (not Key Vault)
- DB authentication: Password auth (not Managed Identity)
- Infrastructure provisioning: Azure CLI scripts (`az` commands in bash scripts)
- Pool size: min=2, max=10 (conservative for B1ms tier, fits within 50 connection limit)
- Acquire timeout: 5 seconds fail-fast (quick failure on pool exhaustion)
- Retry logic: Simple retry once on connection reset (handles Azure maintenance/failover)
- Initialization: App startup via FastAPI lifespan handler (fail fast if DB unreachable)
- Health check depth: Deep check (ping DB, report pool stats, return 503 if DB unreachable)
- Response format: JSON with overall status, component status (DB), pool stats, version
- Health check timeout: 3 seconds for DB check
- Version info: Include git commit SHA and build timestamp

### Claude's Discretion
- Exact Dockerfile base images and Node/Python versions
- Volume mount paths and compose service names
- Azure resource naming conventions
- Health check endpoint path (/health vs /healthz)

### Deferred Ideas (OUT OF SCOPE)
None - discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INFRA-01 | Docker containerization (frontend + backend) | Multi-stage Dockerfile patterns documented; Docker Compose profiles pattern verified; base images and version recommendations provided |
| INFRA-02 | Azure deployment foundation (ACR + PostgreSQL) | Azure CLI commands for ACR and PostgreSQL Flexible Server documented; B1ms tier confirmed available; firewall and connection string formats provided |
| DB-01 | Database connected to backend (activate existing asyncpg layer) | FastAPI lifespan handler pattern documented; asyncpg pool configuration verified; existing `deps.py` and `repository.py` ready to activate |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| asyncpg | 0.30.0 | PostgreSQL async driver | Already in requirements.txt; built-in pooling, no external PgBouncer needed |
| FastAPI | 0.109.0 | Backend framework | Already in requirements.txt; lifespan handler for pool management |
| Next.js | 16.0.10 | Frontend framework | Already in package.json; standalone output mode for Docker optimization |
| Docker | 27.x | Containerization | Multi-stage builds, compose profiles |
| PostgreSQL | 16 | Database | Supported on Azure Flexible Server; pgcrypto extension in schema.sql |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-dotenv | 1.0.1 | Environment loading | Already in requirements.txt; local development |
| pydantic-settings | 2.1.0 | Config management | Already in requirements.txt; type-safe environment parsing |

### Docker Base Images

| Image | Size | Purpose | Notes |
|-------|------|---------|-------|
| python:3.12-slim | ~121MB | FastAPI backend | Debian-based slim variant; good balance of size and compatibility |
| node:22-slim | ~226MB | Next.js build stage | LTS version for 2026; Alpine has native module issues with some deps |
| node:22-slim | ~226MB | Next.js runtime | Same as build; standalone output minimizes runtime footprint |
| postgres:16-alpine | ~90MB | Local dev database | Matches Azure PostgreSQL 16 version |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| python:3.12-slim | python:3.12-alpine | Alpine is smaller (~57MB) but has musl issues with some Python packages; asyncpg builds fine but adds build-time complexity |
| node:22-slim | node:22-alpine | Alpine has native module issues with sharp, lightningcss; not worth the ~40MB savings |
| postgres:16-alpine | postgres:16 | Full image is ~400MB; Alpine is fine for dev |

**Installation:**
```bash
# Backend dependencies (existing)
pip install -r backend/requirements.txt

# Frontend dependencies (existing)
cd frontend && npm install
```

## Architecture Patterns

### Recommended Project Structure
```
infra/
├── docker/
│   ├── backend.Dockerfile       # FastAPI multi-stage
│   ├── frontend.Dockerfile      # Next.js multi-stage
│   └── .dockerignore           # Shared ignore patterns
├── scripts/
│   ├── azure-setup.sh          # ACR + PostgreSQL provisioning
│   ├── azure-teardown.sh       # Resource cleanup
│   └── local-init.sh           # Local dev setup helper
└── docker-compose.yml          # Root level, profiles for dev/prod
```

### Pattern 1: FastAPI Lifespan Handler for asyncpg Pool

**What:** Use contextmanager-based lifespan to create/close pool at app startup/shutdown
**When to use:** Always for asyncpg connection management in FastAPI
**Example:**
```python
# Source: https://fastapi.tiangolo.com/advanced/events/
from contextlib import asynccontextmanager
from fastapi import FastAPI
import asyncpg
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create pool
    app.state.db_pool = await asyncpg.create_pool(
        host=os.environ["PGHOST"],
        port=int(os.environ.get("PGPORT", 5432)),
        database=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        min_size=2,
        max_size=10,
        command_timeout=60,
        ssl="require" if os.environ.get("PGSSL") else None,
    )
    yield
    # Shutdown: close pool
    await app.state.db_pool.close()

app = FastAPI(lifespan=lifespan)
```

### Pattern 2: Connection Dependency with Timeout

**What:** FastAPI dependency that acquires connection from pool with timeout
**When to use:** Every route that needs database access
**Example:**
```python
# Source: Existing backend/app/db/deps.py pattern
from fastapi import Request, HTTPException
from typing import AsyncGenerator
import asyncpg
import asyncio

async def get_db(request: Request) -> AsyncGenerator[asyncpg.Connection, None]:
    pool = request.app.state.db_pool
    try:
        async with asyncio.timeout(5):  # 5s acquire timeout
            async with pool.acquire() as conn:
                yield conn
    except asyncio.TimeoutError:
        raise HTTPException(503, "Database connection pool exhausted")
```

### Pattern 3: Docker Compose Profiles

**What:** Single compose file with services tagged by profile
**When to use:** Dev vs prod service differentiation
**Example:**
```yaml
# Source: https://docs.docker.com/compose/how-tos/production/
services:
  backend:
    profiles: ["dev", "prod"]
    build:
      context: .
      dockerfile: infra/docker/backend.Dockerfile
    volumes:
      - ./backend:/app  # Dev only via override or conditional

  postgres:
    profiles: ["dev"]  # Only in dev; prod uses Azure
    image: postgres:16-alpine

  frontend:
    profiles: ["dev", "prod"]
    build:
      context: .
      dockerfile: infra/docker/frontend.Dockerfile
```

### Pattern 4: Next.js Standalone Multi-Stage Build

**What:** Three-stage Dockerfile: deps, builder, runner
**When to use:** Production Next.js containers
**Example:**
```dockerfile
# Source: https://github.com/vercel/next.js/tree/canary/examples/with-docker
# Stage 1: Dependencies
FROM node:22-slim AS deps
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci --only=production

# Stage 2: Builder
FROM node:22-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY frontend/ .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# Stage 3: Runner
FROM node:22-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
```

### Pattern 5: Health Check with Pool Stats

**What:** Deep health endpoint that validates DB connectivity and reports pool status
**When to use:** Container orchestration readiness/liveness probes
**Example:**
```python
# Source: Combined from https://www.index.dev/blog/how-to-implement-health-check-in-python
import os
import asyncio
from datetime import datetime
from fastapi import APIRouter, Request

router = APIRouter()

@router.get("/health")
async def health_check(request: Request):
    pool = request.app.state.db_pool
    db_status = "unhealthy"
    db_latency_ms = None

    try:
        start = datetime.now()
        async with asyncio.timeout(3):  # 3s timeout per CONTEXT.md
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
        db_latency_ms = (datetime.now() - start).total_seconds() * 1000
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    overall = "healthy" if db_status == "healthy" else "unhealthy"
    status_code = 200 if overall == "healthy" else 503

    return {
        "status": overall,
        "components": {
            "database": {
                "status": db_status,
                "latency_ms": db_latency_ms,
            }
        },
        "pool": {
            "size": pool.get_size(),
            "free": pool.get_idle_size(),
            "used": pool.get_size() - pool.get_idle_size(),
            "min": pool.get_min_size(),
            "max": pool.get_max_size(),
        },
        "version": {
            "commit": os.environ.get("GIT_COMMIT", "unknown"),
            "build_time": os.environ.get("BUILD_TIME", "unknown"),
        }
    }
```

### Anti-Patterns to Avoid

- **Creating connections per request:** Use pool, never `asyncpg.connect()` in routes
- **Forgetting to close pool:** Always use lifespan handler, not manual startup/shutdown
- **Hardcoding credentials:** Use environment variables; never commit secrets
- **Ignoring acquire timeout:** Without timeout, requests hang forever on pool exhaustion
- **Using `ssl=True` locally:** Local postgres container doesn't have SSL; conditionally enable

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Connection pooling | Custom pool class | asyncpg.create_pool() | Built-in, battle-tested, handles connection lifecycle |
| Health checks | Custom ping logic | Pool's `get_size()`, `get_idle_size()` | Pool tracks its own state accurately |
| Env config | os.environ parsing | pydantic-settings | Type validation, default values, .env loading |
| Docker orchestration | Shell script coordination | docker compose | Dependency ordering, health checks, networking |
| Azure provisioning | Portal clicks | Azure CLI scripts | Reproducible, version-controlled, scriptable |

**Key insight:** asyncpg's built-in pool is production-ready. Don't add PgBouncer or SQLAlchemy unless you need their specific features (query building, connection multiplexing at scale).

## Common Pitfalls

### Pitfall 1: asyncpg Pool Exhaustion (PITFALLS.md #4)
**What goes wrong:** All connections in use, new requests hang or timeout
**Why it happens:** Long-running queries hold connections; no acquire timeout configured
**How to avoid:**
- Set `min_size=2, max_size=10` (conservative for B1ms)
- Use 5s acquire timeout in `get_db` dependency
- Monitor pool stats via health endpoint
**Warning signs:** Health check shows `free: 0`, requests timing out

### Pitfall 2: SSL Mismatch Local vs Azure
**What goes wrong:** Connection fails with SSL errors
**Why it happens:** Local postgres has no SSL; Azure requires it
**How to avoid:**
- Conditionally set `ssl="require"` based on environment variable
- Use `PGSSL=require` in Azure, omit locally
**Warning signs:** "SSL connection is required" error locally

### Pitfall 3: Next.js Standalone Missing Static Files
**What goes wrong:** 404 on images, CSS, JS files
**Why it happens:** `.next/static` not copied to standalone output
**How to avoid:**
- Copy both `.next/standalone` AND `.next/static` in Dockerfile
- Also copy `public/` directory
**Warning signs:** Console errors for static assets, unstyled pages

### Pitfall 4: Docker Build Cache Invalidation
**What goes wrong:** Full rebuild on every code change
**Why it happens:** COPY order invalidates layer cache
**How to avoid:**
- Copy package.json/requirements.txt first, install deps
- Copy source code last
**Warning signs:** Slow builds even for small changes

### Pitfall 5: Azure PostgreSQL Firewall Blocking
**What goes wrong:** Connection timeout from Container Apps
**Why it happens:** Firewall doesn't allow Azure services
**How to avoid:**
- Use `--public-access 0.0.0.0` to allow all Azure services
- Or configure specific IP ranges for Container Apps subnet
**Warning signs:** Connection timeout, not authentication error

### Pitfall 6: Frontend Can't Reach Backend in Docker
**What goes wrong:** CORS errors or connection refused
**Why it happens:** Using `localhost` which resolves differently in containers
**How to avoid:**
- Use Docker service names (`backend:8000`) for server-side
- Keep `localhost:8000` for client-side (browser)
- Set `NEXT_PUBLIC_API_URL` appropriately per environment
**Warning signs:** "Connection refused" or CORS errors

## Code Examples

### asyncpg Pool Configuration (Production)
```python
# Source: https://magicstack.github.io/asyncpg/current/api/index.html
await asyncpg.create_pool(
    dsn=None,  # Use individual params for clarity
    host=os.environ["PGHOST"],
    port=int(os.environ.get("PGPORT", 5432)),
    database=os.environ["PGDATABASE"],
    user=os.environ["PGUSER"],
    password=os.environ["PGPASSWORD"],
    min_size=2,                           # Minimum idle connections
    max_size=10,                          # Maximum connections (B1ms has 50 limit)
    max_queries=50000,                    # Queries before connection replacement
    max_inactive_connection_lifetime=300.0,  # 5 min idle timeout
    command_timeout=60,                   # Query timeout
    ssl="require" if os.environ.get("PGSSL") else None,
)
```

### Azure CLI: Create Container Registry
```bash
# Source: https://learn.microsoft.com/en-us/azure/container-registry/container-registry-get-started-azure-cli
RESOURCE_GROUP="inclusify-rg"
ACR_NAME="inclusifyacr"  # Must be globally unique, lowercase alphanumeric

az group create --name $RESOURCE_GROUP --location eastus

az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --sku Basic \
  --admin-enabled true

# Get login credentials
az acr credential show --name $ACR_NAME
```

### Azure CLI: Create PostgreSQL Flexible Server
```bash
# Source: https://learn.microsoft.com/en-us/azure/postgresql/configure-maintain/quickstart-create-server
RESOURCE_GROUP="inclusify-rg"
PG_SERVER="inclusify-db"
PG_USER="inclusifyadmin"
PG_PASSWORD="<secure-password>"

az postgres flexible-server create \
  --resource-group $RESOURCE_GROUP \
  --name $PG_SERVER \
  --location eastus \
  --admin-user $PG_USER \
  --admin-password $PG_PASSWORD \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --storage-size 32 \
  --version 16 \
  --public-access 0.0.0.0

# Create database
az postgres flexible-server db create \
  --resource-group $RESOURCE_GROUP \
  --server-name $PG_SERVER \
  --database-name inclusify

# Connection string format:
# host=$PG_SERVER.postgres.database.azure.com port=5432 dbname=inclusify user=$PG_USER password=$PG_PASSWORD sslmode=require
```

### next.config.ts with Standalone Output
```typescript
// Source: https://nextjs.org/docs/app/getting-started/deploying
import type { NextConfig } from "next";
import createNextIntlPlugin from 'next-intl/plugin';

const withNextIntl = createNextIntlPlugin('./i18n/request.ts');

const nextConfig: NextConfig = {
  output: "standalone",  // Required for Docker optimization
};

export default withNextIntl(nextConfig);
```

### Docker Compose with Profiles
```yaml
# docker-compose.yml
version: "3.9"

services:
  postgres:
    image: postgres:16-alpine
    profiles: ["dev"]
    environment:
      POSTGRES_DB: inclusify
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: devpassword
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./db/schema.sql:/docker-entrypoint-initdb.d/01-schema.sql
      - ./db/seed.sql:/docker-entrypoint-initdb.d/02-seed.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    profiles: ["dev", "prod"]
    build:
      context: .
      dockerfile: infra/docker/backend.Dockerfile
      target: ${BUILD_TARGET:-development}
    environment:
      - PGHOST=${PGHOST:-postgres}
      - PGPORT=${PGPORT:-5432}
      - PGDATABASE=${PGDATABASE:-inclusify}
      - PGUSER=${PGUSER:-postgres}
      - PGPASSWORD=${PGPASSWORD:-devpassword}
      - PGSSL=${PGSSL:-}
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  frontend:
    profiles: ["dev", "prod"]
    build:
      context: .
      dockerfile: infra/docker/frontend.Dockerfile
      target: ${BUILD_TARGET:-development}
    environment:
      - NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL:-http://localhost:8000}
    ports:
      - "3000:3000"
    depends_on:
      - backend

volumes:
  postgres_data:
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| startup/shutdown events | lifespan handler | FastAPI 0.95+ (2023) | Cleaner resource management |
| PgBouncer for pooling | asyncpg built-in pool | Always available | One less component to manage |
| Separate compose files | Compose profiles | Compose v2 (2022) | Single source of truth |
| Full Python images | python:X-slim | Always available | ~900MB to ~121MB |
| Manual Next.js copy | standalone output | Next.js 12+ (2021) | Minimal runtime footprint |
| Azure Portal provisioning | Azure CLI scripts | Always available | Reproducible infrastructure |

**Deprecated/outdated:**
- FastAPI `@app.on_event("startup")` / `@app.on_event("shutdown")`: Use lifespan handler instead
- `asyncpg.connect()` per request: Always use pool
- Docker Compose v1 syntax: Use version "3.9" or omit (Compose v2 auto-detects)

## Open Questions

1. **Container Apps vs Azure VM for backend**
   - What we know: Container Apps is simpler (no VM management), supports secrets
   - What's unclear: Pricing for sustained load; cold start impact
   - Recommendation: Start with Container Apps; revisit if cold starts are problematic

2. **Local PostgreSQL data persistence**
   - What we know: Named volume `postgres_data` persists across restarts
   - What's unclear: Should schema be auto-applied on container start?
   - Recommendation: Use init scripts in `/docker-entrypoint-initdb.d/`; they only run on first start

3. **Frontend environment variables at build vs runtime**
   - What we know: `NEXT_PUBLIC_*` vars are baked in at build time
   - What's unclear: How to handle different API URLs for staging vs prod from same image
   - Recommendation: For now, build separate images per environment; consider runtime config later

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x (to be installed) |
| Config file | None - see Wave 0 |
| Quick run command | `pytest backend/tests/ -x -q` |
| Full suite command | `pytest backend/tests/ -v --tb=short` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-01 | Docker build succeeds | integration | `docker compose build` | N/A (compose file) |
| INFRA-01 | Containers start | integration | `docker compose up -d --wait` | N/A (compose file) |
| INFRA-02 | ACR accepts push | manual | `az acr login && docker push` | N/A (manual) |
| INFRA-02 | PostgreSQL accessible | manual | `psql` connection test | N/A (manual) |
| DB-01 | Pool creates on startup | unit | `pytest backend/tests/test_db_pool.py -x` | Wave 0 |
| DB-01 | Health check returns 200 | integration | `curl http://localhost:8000/health` | N/A (curl) |
| DB-01 | Repository queries work | unit | `pytest backend/tests/test_repository.py -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `docker compose build && docker compose up -d --wait && curl localhost:8000/health`
- **Per wave merge:** Full docker compose up, health check, sample query
- **Phase gate:** All services running, health check 200, DB query succeeds

### Wave 0 Gaps

- [ ] `backend/tests/` directory - create directory structure
- [ ] `backend/tests/conftest.py` - shared fixtures (test pool, mock app)
- [ ] `backend/tests/test_db_pool.py` - pool creation, acquire/release
- [ ] `backend/tests/test_health.py` - health endpoint validation
- [ ] `backend/pyproject.toml` or `pytest.ini` - pytest configuration
- [ ] pytest in requirements.txt - `pytest>=8.0.0`, `pytest-asyncio>=0.23.0`, `httpx>=0.26.0`

## Sources

### Primary (HIGH confidence)
- [asyncpg API Reference](https://magicstack.github.io/asyncpg/current/api/index.html) - create_pool parameters, pool methods
- [FastAPI Lifespan Events](https://fastapi.tiangolo.com/advanced/events/) - lifespan handler pattern
- [Next.js Deploying](https://nextjs.org/docs/app/getting-started/deploying) - standalone output configuration
- [Azure Container Registry CLI](https://learn.microsoft.com/en-us/azure/container-registry/container-registry-get-started-azure-cli) - az acr commands
- [Azure PostgreSQL Quickstart](https://learn.microsoft.com/en-us/azure/postgresql/configure-maintain/quickstart-create-server) - az postgres commands, B1ms tier
- [Docker Compose Production](https://docs.docker.com/compose/how-tos/production/) - profiles pattern

### Secondary (MEDIUM confidence)
- [Next.js Docker Example](https://github.com/vercel/next.js/tree/canary/examples/with-docker) - multi-stage Dockerfile pattern
- [FastAPI asyncpg Discussion #9520](https://github.com/fastapi/fastapi/discussions/9520) - lifespan + pool pattern
- [Docker Compose Profiles Guide](https://collabnix.com/leveraging-compose-profiles-for-dev-prod-test-and-staging-environments/) - profile usage patterns

### Tertiary (LOW confidence)
- None - all findings verified with primary sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - existing requirements.txt and package.json versions verified
- Architecture: HIGH - patterns from official FastAPI and Next.js documentation
- Pitfalls: HIGH - documented issues from asyncpg GitHub and verified in Azure docs
- Azure CLI: HIGH - commands from official Microsoft Learn documentation

**Research date:** 2026-03-09
**Valid until:** 2026-04-09 (30 days - stable technologies)
