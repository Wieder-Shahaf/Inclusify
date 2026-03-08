# Phase 1: Infrastructure Foundation - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Establish containerized services with database connectivity ready for development. This includes Docker builds for frontend and backend, Azure infrastructure provisioning (ACR, PostgreSQL), and activating the existing asyncpg repository layer.

</domain>

<decisions>
## Implementation Decisions

### Docker Setup
- Single `docker-compose.yml` with profiles for dev/prod (not separate files)
- Include PostgreSQL container for local dev (`docker compose up` gives everything)
- Multi-stage builds for frontend (build stage compiles Next.js, final stage copies .next/standalone)
- Hot-reload via volume mounts for local development

### Azure Provisioning
- PostgreSQL tier: Burstable B1ms (1 vCore, 2GB RAM, ~$15/month, student credits friendly)
- Secrets management: Container Apps secrets (not Key Vault)
- DB authentication: Password auth (not Managed Identity)
- Infrastructure provisioning: Azure CLI scripts (`az` commands in bash scripts)

### Database Pooling
- Pool size: min=2, max=10 (conservative for B1ms tier, fits within 50 connection limit)
- Acquire timeout: 5 seconds fail-fast (quick failure on pool exhaustion)
- Retry logic: Simple retry once on connection reset (handles Azure maintenance/failover)
- Initialization: App startup via FastAPI lifespan handler (fail fast if DB unreachable)

### Health Checks
- Depth: Deep check (ping DB connection, report pool stats, return 503 if DB unreachable)
- Response format: JSON with overall status, component status (DB), pool stats, version
- Timeout: 3 seconds for DB check
- Version info: Include git commit SHA and build timestamp

### Claude's Discretion
- Exact Dockerfile base images and Node/Python versions
- Volume mount paths and compose service names
- Azure resource naming conventions
- Health check endpoint path (/health vs /healthz)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/db/connection.py`: asyncpg connection helper (needs pool activation)
- `backend/app/db/deps.py`: FastAPI dependency for DB connection (planned via `request.app.state.db_pool`)
- `backend/app/db/repository.py`: Full repository layer with CRUD operations (commented out, ready to activate)
- `db/schema.sql`: Production-ready PostgreSQL schema (303 lines, 11 tables)
- `db/seed.sql`: Seed data for development

### Established Patterns
- Environment variables: `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD` already used in connection.py
- CORS: Already configured in `backend/app/main.py` for localhost:3000
- Async/await: Full async architecture in backend (FastAPI + asyncpg)

### Integration Points
- `backend/app/main.py`: FastAPI app initialization, add lifespan handler for pool
- `frontend/next.config.ts`: Add Docker-compatible environment handling
- `frontend/lib/api/client.ts`: Already uses `NEXT_PUBLIC_API_URL` for backend connection

</code_context>

<specifics>
## Specific Ideas

- "docker compose up gives you everything" - no external dependencies for local dev
- Fail-fast philosophy for DB issues (5s timeout, startup check)
- Version info in health check for debugging deployed versions

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope

</deferred>

---

*Phase: 01-infrastructure-foundation*
*Context gathered: 2026-03-08*
