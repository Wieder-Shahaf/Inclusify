---
phase: 02-core-services
plan: 01
subsystem: auth
tags: [jwt, fastapi-users, redis, sqlalchemy, pydantic]

# Dependency graph
requires:
  - phase: 01-infrastructure-foundation
    provides: asyncpg pool, Docker configs, health check
provides:
  - JWT authentication with FastAPI Users 13.x
  - User registration and login endpoints
  - Protected route middleware (current_active_user)
  - Redis refresh token storage
  - SQLAlchemy User model compatible with existing schema
affects: [02-rbac, 03-analysis, frontend-auth]

# Tech tracking
tech-stack:
  added: [fastapi-users, pwdlib, python-jose, redis, sqlalchemy, aiosqlite]
  patterns: [JWT with role claims, Bearer token auth, Redis token storage]

key-files:
  created:
    - backend/app/auth/__init__.py
    - backend/app/auth/schemas.py
    - backend/app/auth/backend.py
    - backend/app/auth/manager.py
    - backend/app/auth/users.py
    - backend/app/db/models.py
    - backend/app/core/redis.py
    - backend/tests/test_auth.py
    - backend/tests/test_auth_schemas.py
    - infra/docker/docker-compose.yml
  modified:
    - backend/app/core/config.py
    - backend/app/main.py
    - backend/requirements.txt

key-decisions:
  - "Used SQLAlchemy Uuid type instead of PostgreSQL UUID for SQLite test compatibility"
  - "Removed FK constraint on org_id (enforced at PostgreSQL level, not SQLAlchemy)"
  - "JWT role claim added via custom JWTStrategyWithRole.write_token override"
  - "Redis optional - auth works without it, logs warning on connection failure"

patterns-established:
  - "TDD for auth modules: schema tests first, then implementation"
  - "Integration tests use file-based SQLite with mock Redis/asyncpg"
  - "Settings use Pydantic v2 model_config instead of class Config"

requirements-completed: [AUTH-01]

# Metrics
duration: 9min
completed: 2026-03-09
---

# Phase 02 Plan 01: JWT Authentication Summary

**JWT auth with FastAPI Users 13.x, Redis-backed refresh tokens, role-enhanced claims, and protected route middleware**

## Performance

- **Duration:** 9 min
- **Started:** 2026-03-09T10:00:05Z
- **Completed:** 2026-03-09T10:08:43Z
- **Tasks:** 2
- **Files modified:** 13

## Accomplishments

- Complete auth module with FastAPI Users 13.x integration
- User registration, login, logout endpoints at /auth/jwt/*
- Protected route dependency (current_active_user) for securing endpoints
- JWT tokens include user role in claims
- Redis manager for refresh token storage with TTL
- Docker compose with Redis, PostgreSQL, backend, frontend services
- 14 passing tests (schema validation, JWT strategy, full auth flow)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create auth module with FastAPI Users integration (TDD)**
   - `da3dcf9` - test(02-01): add failing tests for auth schemas and JWT strategy (RED)
   - `b54afee` - feat(02-01): implement auth module with FastAPI Users 13.x (GREEN)

2. **Task 2: Add Redis refresh token storage and wire to main app**
   - `e5578c0` - feat(02-01): add Redis refresh token storage and wire auth routes

## Files Created/Modified

- `backend/app/auth/__init__.py` - Auth module package
- `backend/app/auth/schemas.py` - UserCreate/UserRead/UserUpdate with validation
- `backend/app/auth/backend.py` - JWTStrategyWithRole, auth_backend
- `backend/app/auth/manager.py` - UserManager with lifecycle hooks
- `backend/app/auth/users.py` - FastAPI Users instance, routers, current_active_user
- `backend/app/db/models.py` - SQLAlchemy User model
- `backend/app/core/config.py` - Settings with JWT_SECRET, REDIS_URL, DATABASE_URL
- `backend/app/core/redis.py` - RedisManager for refresh tokens
- `backend/app/main.py` - Lifespan with Redis init, auth routers mounted
- `backend/requirements.txt` - Added auth dependencies
- `infra/docker/docker-compose.yml` - Full stack with Redis service
- `backend/tests/test_auth_schemas.py` - TDD unit tests
- `backend/tests/test_auth.py` - Integration tests

## Decisions Made

1. **SQLAlchemy Uuid type over PostgreSQL UUID**: Enables SQLite for testing while PostgreSQL uses native UUID in production
2. **org_id without FK constraint**: The organizations table is managed by schema.sql (asyncpg), not SQLAlchemy. FK enforced at DB level only.
3. **Redis optional**: Auth continues working without Redis (warning logged), graceful degradation for local dev without Docker
4. **Pydantic v2 model_config**: Updated Settings to use SettingsConfigDict instead of deprecated class Config

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed JWT read_token returning string instead of User**
- **Found during:** Task 2 (test_users_me_with_token failing)
- **Issue:** Custom read_token returned user_id string, but FastAPI Users expects User object from parent
- **Fix:** Removed custom read_token, let parent JWTStrategy handle user fetching
- **Files modified:** backend/app/auth/backend.py
- **Verification:** All 14 tests pass
- **Committed in:** e5578c0

**2. [Rule 3 - Blocking] Fixed PostgreSQL UUID incompatible with SQLite**
- **Found during:** Task 2 (SQLite test DB creation)
- **Issue:** sqlalchemy.dialects.postgresql.UUID not renderable by SQLite compiler
- **Fix:** Changed to sqlalchemy.Uuid which works with both databases
- **Files modified:** backend/app/db/models.py
- **Verification:** Tests run with SQLite, production will use PostgreSQL UUID
- **Committed in:** e5578c0

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both fixes essential for tests to pass. No scope creep.

## Issues Encountered

- Initial pwdlib version (1.0.0) not found - downgraded to 0.2.0 in requirements
- PyMuPDF (fitz) not in test venv - installed to allow app import during tests

## User Setup Required

None - no external service configuration required. Redis and PostgreSQL are containerized via docker-compose.

## Next Phase Readiness

- Auth foundation complete, ready for RBAC (02-02)
- current_active_user dependency exported for protecting any route
- User model has role field, ready for permission checks
- Docker compose provides full local dev environment

## Self-Check: PASSED

All 10 created files verified present.
All 3 task commits verified in git log (da3dcf9, b54afee, e5578c0).

---
*Phase: 02-core-services*
*Completed: 2026-03-09*
