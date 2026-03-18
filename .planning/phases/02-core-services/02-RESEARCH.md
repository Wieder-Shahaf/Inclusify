# Phase 2: Core Services - Research

**Researched:** 2026-03-09
**Domain:** Authentication, Authorization, Document Parsing
**Confidence:** HIGH

## Summary

This phase implements JWT authentication with FastAPI Users 13.x, simple RBAC (user/admin roles), and Docling-based PDF parsing. The core challenge is integrating modern authentication patterns (pwdlib replacing deprecated passlib) with the existing asyncpg infrastructure while ensuring document processing doesn't crash the API server.

FastAPI Users 13.x is the clear choice for authentication - it provides JWT transport, password hashing with pwdlib/Argon2, and automatic hash migration from bcrypt. RBAC is implemented via JWT claims with role embedded at login time, avoiding per-request DB lookups. Docling replaces PyMuPDF with subprocess isolation to protect against memory exhaustion on large PDFs.

**Primary recommendation:** Use FastAPI Users 13.x for auth (NOT custom JWT), embed role in JWT claims, run Docling in subprocess with 60s timeout, and use redis-py async for refresh token storage.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Hard page limit: 50 pages maximum. Reject larger documents with clear error message.
- Error handling: Return specific error messages for password-protected ("PDF is password-protected") and corrupted PDFs ("PDF appears corrupted"). User should know exactly what's wrong.
- Progress UX: Indeterminate spinner with status text ("Extracting text..." -> "Analyzing content..."). No percentage progress.
- Isolation: Run Docling in subprocess with 60-second timeout. Kill process if exceeded. Protects API server from crashes.
- Authorization denial: Return 403 Forbidden with message ("Insufficient permissions"). Don't hide endpoints with 404.
- Role storage: Embed role in JWT claims. Fast checks without DB lookup. Role changes require new token (logout/login).
- Admin scope: View-only access to other users' documents/analyses. Admins can see but not edit/delete user content.
- Rate limiting: Skip for v1. Add later if abuse becomes a problem.

### Claude's Discretion
- JWT token lifetimes (access and refresh durations)
- Password complexity requirements
- Email verification flow (whether required at all)
- Redis connection pooling and error handling
- Docling subprocess communication mechanism

### Deferred Ideas (OUT OF SCOPE)
None - discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AUTH-01 | Authentication (email/password) | FastAPI Users 13.x with pwdlib/Argon2, JWT bearer transport, Redis-backed refresh tokens |
| AUTH-02 | Simple RBAC (user and admin roles) | JWT claims with role field, PermissionChecker dependency pattern, 403 responses |
| DOC-01 | Docling replaces PyMuPDF | Docling 2.77.0, subprocess isolation with 60s timeout, 50-page limit enforcement |
</phase_requirements>

## Standard Stack

### Core Authentication
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi-users | 13.0.0+ | User management, JWT | Industry standard, migrated from passlib to pwdlib |
| pwdlib[argon2] | 1.0.0+ | Password hashing | Replaces deprecated passlib, Argon2 default |
| python-jose[cryptography] | 3.3.0+ | JWT encoding/decoding | FastAPI ecosystem standard |
| redis | 5.0.0+ | Refresh token storage | redis.asyncio replaces deprecated aioredis |

### Document Processing
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| docling | 2.77.0+ | PDF/DOCX parsing | Superior layout preservation, replaces PyMuPDF |
| docling-jobkit | latest | Subprocess processing | Memory isolation for large documents |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic-settings | 2.1.0+ | Config management | Environment variable handling |
| email-validator | 2.0.0+ | Email validation | User registration |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| FastAPI Users | Custom JWT implementation | FastAPI Users handles edge cases, password migration |
| Redis | PostgreSQL for tokens | Redis faster for token ops, but adds infrastructure |
| Docling subprocess | In-process Docling | Memory safety vs. IPC complexity |

**Installation:**
```bash
# Authentication
pip install 'fastapi-users[sqlalchemy]==13.0.0' pwdlib[argon2]==1.0.0 python-jose[cryptography]==3.3.0 redis==5.0.0

# Document processing
pip install docling==2.77.0

# Email validation
pip install email-validator==2.1.0
```

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── auth/
│   ├── __init__.py
│   ├── backend.py      # JWT backend config
│   ├── manager.py      # UserManager with custom logic
│   ├── schemas.py      # UserRead, UserCreate, UserUpdate
│   ├── users.py        # FastAPI Users setup, routers
│   └── deps.py         # get_current_user, require_admin, require_role
├── modules/
│   └── ingestion/
│       ├── router.py   # Upload endpoint
│       ├── service.py  # Docling subprocess orchestration
│       └── schemas.py  # Upload response models
├── db/
│   ├── connection.py   # asyncpg pool (existing)
│   ├── deps.py         # get_db (existing), add auth deps
│   ├── models.py       # SQLAlchemy User model for FastAPI Users
│   └── repository.py   # User CRUD (extend existing)
└── core/
    ├── config.py       # Settings with Redis, JWT config
    └── redis.py        # Redis connection manager
```

### Pattern 1: FastAPI Users Integration
**What:** Configure FastAPI Users with SQLAlchemy async adapter
**When to use:** All authentication endpoints
**Example:**
```python
# Source: FastAPI Users official docs
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy
from fastapi_users.db import SQLAlchemyUserDatabase

# JWT Strategy with role in claims
class JWTStrategyWithRole(JWTStrategy):
    async def write_token(self, user) -> str:
        data = {"sub": str(user.id), "role": user.role, "aud": self.token_audience}
        return generate_jwt(data, self.secret, self.lifetime_seconds, algorithm=self.algorithm)

def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategyWithRole(
        secret=settings.JWT_SECRET,
        lifetime_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        token_audience=["fastapi-users:auth"]
    )

bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")
auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])
```

### Pattern 2: RBAC via JWT Claims Dependency
**What:** Check role from JWT claims without DB lookup
**When to use:** Protected endpoints requiring specific roles
**Example:**
```python
# Source: CONTEXT.md locked decision - role in JWT claims
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/jwt/login")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_role(required_role: str):
    """Dependency factory for role-based access"""
    async def role_checker(user: dict = Depends(get_current_user)):
        if user.get("role") not in [required_role, "site_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"  # Per CONTEXT.md
            )
        return user
    return role_checker

# Usage
@router.get("/admin/users", dependencies=[Depends(require_role("org_admin"))])
async def list_users():
    ...
```

### Pattern 3: Redis Refresh Token Storage
**What:** Store refresh tokens in Redis with automatic expiry
**When to use:** JWT refresh endpoint
**Example:**
```python
# Source: redis-py async documentation
import redis.asyncio as redis
from contextlib import asynccontextmanager

class RedisManager:
    def __init__(self, url: str, max_connections: int = 50):
        self.pool = redis.ConnectionPool.from_url(url, max_connections=max_connections)
        self.client = redis.Redis(connection_pool=self.pool)

    async def store_refresh_token(self, user_id: str, token: str, ttl_seconds: int):
        """Store refresh token with TTL"""
        key = f"refresh:{user_id}"
        await self.client.setex(key, ttl_seconds, token)

    async def validate_refresh_token(self, user_id: str, token: str) -> bool:
        """Validate and consume refresh token (one-time use)"""
        key = f"refresh:{user_id}"
        stored = await self.client.get(key)
        if stored and stored.decode() == token:
            await self.client.delete(key)  # Invalidate after use
            return True
        return False

    async def close(self):
        await self.client.close()
        await self.pool.disconnect()
```

### Pattern 4: Docling Subprocess Isolation
**What:** Run Docling in subprocess to protect API from memory exhaustion
**When to use:** PDF upload endpoint
**Example:**
```python
# Source: CONTEXT.md locked decision - 60s timeout, subprocess isolation
import asyncio
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from functools import partial

def _parse_pdf_sync(file_bytes: bytes, max_pages: int = 50) -> dict:
    """Sync function run in subprocess - imports Docling here to isolate memory"""
    from docling.document_converter import DocumentConverter
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    import tempfile
    import os

    # Write bytes to temp file
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(file_bytes)
        temp_path = f.name

    try:
        # Check page count first
        from pypdf import PdfReader
        reader = PdfReader(temp_path)
        page_count = len(reader.pages)

        if page_count > max_pages:
            return {"error": f"Document exceeds {max_pages} page limit ({page_count} pages)"}

        # Configure Docling
        options = PdfPipelineOptions()
        options.do_table_structure = True
        options.generate_page_images = False  # Memory optimization

        converter = DocumentConverter()
        result = converter.convert(temp_path)

        return {
            "text": result.document.export_to_markdown(),
            "page_count": page_count,
        }
    except Exception as e:
        error_msg = str(e).lower()
        if "password" in error_msg or "encrypted" in error_msg:
            return {"error": "PDF is password-protected"}
        elif "corrupt" in error_msg or "invalid" in error_msg:
            return {"error": "PDF appears corrupted"}
        return {"error": f"Failed to process PDF: {str(e)}"}
    finally:
        os.unlink(temp_path)

async def parse_pdf_async(file_bytes: bytes, timeout: int = 60) -> dict:
    """Async wrapper with timeout"""
    loop = asyncio.get_event_loop()
    with ProcessPoolExecutor(max_workers=1) as executor:
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(executor, partial(_parse_pdf_sync, file_bytes)),
                timeout=timeout
            )
            return result
        except asyncio.TimeoutError:
            return {"error": "Document processing timed out (60s limit)"}
```

### Anti-Patterns to Avoid
- **passlib usage:** Deprecated, breaks on Python 3.13. Use pwdlib[argon2].
- **Role in DB per request:** Defeats JWT statelessness. Embed role in JWT claims.
- **In-process Docling for uploads:** Memory exhaustion risk. Use subprocess.
- **localStorage for tokens:** XSS vulnerable. Use HttpOnly cookies for refresh tokens.
- **Fixed refresh token:** Race condition risk. Issue new refresh token on each use.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Password hashing | Custom bcrypt wrapper | pwdlib[argon2] | Timing attacks, salt generation, hash format |
| JWT lifecycle | Manual encode/decode | FastAPI Users JWT backend | Token rotation, blacklisting, audience validation |
| User management | Custom registration flow | FastAPI Users | Email verification, password reset, account verification |
| Token refresh | Simple token swap | Redis-backed with rotation | Race conditions, token reuse attacks |
| PDF layout extraction | Page-by-page text concat | Docling with table structure | Multi-column, tables, reading order |

**Key insight:** Authentication is security-critical. FastAPI Users 13.x handles passlib-to-pwdlib migration, hash auto-upgrade, and proper JWT lifecycle. Custom implementations invariably miss edge cases.

## Common Pitfalls

### Pitfall 1: passlib Breaks on Python 3.13
**What goes wrong:** FastAPI Users <13.0 uses passlib, which has deprecated modules removed in Python 3.13
**Why it happens:** passlib unmaintained since 2020
**How to avoid:** Use FastAPI Users 13.0+ which uses pwdlib
**Warning signs:** `ModuleNotFoundError: No module named 'passlib'` on startup

### Pitfall 2: Docling Memory Exhaustion
**What goes wrong:** Large PDFs (100+ pages) consume 8-16GB RAM, worker killed by OOM
**Why it happens:** Docling loads entire document structure in memory
**How to avoid:** 50-page limit (CONTEXT.md decision), subprocess isolation with timeout
**Warning signs:** Worker disappears mid-request, 502 errors during upload

### Pitfall 3: JWT Refresh Race Condition
**What goes wrong:** Multiple tabs refresh simultaneously, each invalidates other's token
**Why it happens:** Server issues new refresh token, invalidates old one
**How to avoid:** Redis cache with short TTL (1s) for in-flight refreshes, return same new token
**Warning signs:** Random logouts when multiple tabs open

### Pitfall 4: Role Changes Not Reflected
**What goes wrong:** Admin promotes user, but user still sees old permissions
**Why it happens:** Role embedded in JWT, doesn't update until new token
**How to avoid:** Document behavior clearly (CONTEXT.md: "Role changes require new token"), provide logout/login guidance
**Warning signs:** User complaints about permissions not updating

### Pitfall 5: Redis Connection Leaks
**What goes wrong:** Redis connections exhausted, auth endpoints fail
**Why it happens:** Not using connection pool, not closing connections properly
**How to avoid:** Use ConnectionPool with max_connections, close in lifespan shutdown
**Warning signs:** `ConnectionError: Error while reading from socket`, timeout on token operations

## Code Examples

### FastAPI Users SQLAlchemy Model
```python
# Source: FastAPI Users SQLAlchemy docs
from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String

class Base(DeclarativeBase):
    pass

class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "users"

    # Add role field for RBAC
    role: Mapped[str] = mapped_column(String(20), default="user")

    # Map to existing schema columns
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.org_id"))
```

### Upload Endpoint with Docling
```python
# Source: CONTEXT.md decisions + Docling patterns
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.modules.ingestion.service import parse_pdf_async

router = APIRouter()

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files supported")

    file_bytes = await file.read()

    # Enforce size limit (prevent DoS)
    if len(file_bytes) > 50 * 1024 * 1024:  # 50MB
        raise HTTPException(status_code=400, detail="File too large (50MB limit)")

    result = await parse_pdf_async(file_bytes, timeout=60)

    if "error" in result:
        # Return specific error messages per CONTEXT.md
        raise HTTPException(status_code=400, detail=result["error"])

    return {
        "filename": file.filename,
        "page_count": result["page_count"],
        "text_preview": result["text"][:500] + "...",
        "full_text_length": len(result["text"])
    }
```

### Redis Lifespan Integration
```python
# Source: FastAPI lifespan + redis.asyncio docs
from contextlib import asynccontextmanager
from fastapi import FastAPI
import redis.asyncio as redis

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create pools
    app.state.db_pool = await create_pool()
    app.state.redis = redis.Redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        max_connections=50
    )

    yield

    # Shutdown: close connections
    await app.state.db_pool.close()
    await app.state.redis.close()

app = FastAPI(lifespan=lifespan)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| passlib + bcrypt | pwdlib + Argon2 | FastAPI Users 13.0 (Mar 2025) | Must migrate for Python 3.13 compat |
| aioredis package | redis.asyncio | redis-py 4.2.0+ (2022) | aioredis deprecated, merged into redis-py |
| PyMuPDF | Docling | Project decision (2026) | Better layout preservation |
| Custom JWT | FastAPI Users JWT | FastAPI ecosystem standard | Handles edge cases, migrations |

**Deprecated/outdated:**
- passlib: Unmaintained, breaks Python 3.13+
- aioredis: Deprecated, use redis.asyncio instead
- PyMuPDF: Inferior layout preservation for academic papers

## Claude's Discretion Recommendations

Based on research, here are recommendations for discretionary items:

### JWT Token Lifetimes
- **Access token:** 15 minutes (industry standard for sensitive apps)
- **Refresh token:** 7 days (balances UX and security)
- **Rationale:** Short access tokens limit exposure, 7-day refresh avoids frequent re-login

### Password Complexity
- **Minimum:** 8 characters
- **Recommended:** No complexity rules, use zxcvbn strength meter
- **Rationale:** NIST 2024 guidance deprecates complexity rules in favor of length + breach checking

### Email Verification
- **Recommendation:** Skip for v1, add later
- **Rationale:** Academic tool, not public SaaS. Focus on core functionality first.

### Redis Connection Pooling
- **Max connections:** 50
- **Socket timeout:** 5s
- **Retry on timeout:** Once
- **Rationale:** Match asyncpg patterns established in Phase 1

### Docling Subprocess Communication
- **Mechanism:** ProcessPoolExecutor with 1 worker
- **IPC:** Return dict from sync function (pickle serialization)
- **Rationale:** Simple, debuggable, sufficient for single-document processing

## Open Questions

1. **SQLAlchemy vs Raw asyncpg for User Model**
   - What we know: FastAPI Users expects SQLAlchemy adapter
   - What's unclear: Project uses raw asyncpg (Phase 1), mixing ORMs adds complexity
   - Recommendation: Use SQLAlchemy for User model only (FastAPI Users requirement), keep asyncpg for other entities

2. **Existing users Table Compatibility**
   - What we know: db/schema.sql has users table with password_hash, sso_provider, role
   - What's unclear: FastAPI Users expects specific columns (hashed_password, is_active, etc.)
   - Recommendation: Add FastAPI Users columns via migration, keep existing columns

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0.0 + pytest-asyncio 0.23.0 |
| Config file | none - see Wave 0 |
| Quick run command | `pytest backend/tests/ -x --tb=short` |
| Full suite command | `pytest backend/tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-01a | User registration creates account | unit | `pytest backend/tests/test_auth.py::test_register -x` | Wave 0 |
| AUTH-01b | Login returns JWT tokens | unit | `pytest backend/tests/test_auth.py::test_login -x` | Wave 0 |
| AUTH-01c | Protected endpoint rejects invalid token | unit | `pytest backend/tests/test_auth.py::test_invalid_token -x` | Wave 0 |
| AUTH-01d | Refresh token returns new access token | unit | `pytest backend/tests/test_auth.py::test_refresh -x` | Wave 0 |
| AUTH-02a | Admin can access admin endpoints | unit | `pytest backend/tests/test_rbac.py::test_admin_access -x` | Wave 0 |
| AUTH-02b | User gets 403 on admin endpoints | unit | `pytest backend/tests/test_rbac.py::test_user_forbidden -x` | Wave 0 |
| DOC-01a | PDF upload extracts text | integration | `pytest backend/tests/test_docling.py::test_pdf_upload -x` | Wave 0 |
| DOC-01b | >50 page PDF rejected | unit | `pytest backend/tests/test_docling.py::test_page_limit -x` | Wave 0 |
| DOC-01c | Password-protected PDF returns error | unit | `pytest backend/tests/test_docling.py::test_password_protected -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest backend/tests/ -x --tb=short`
- **Per wave merge:** `pytest backend/tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_auth.py` - covers AUTH-01
- [ ] `backend/tests/test_rbac.py` - covers AUTH-02
- [ ] `backend/tests/test_docling.py` - covers DOC-01
- [ ] `pytest.ini` or `pyproject.toml [tool.pytest.asyncio_mode]` - asyncio mode config
- [ ] Mock fixtures for Redis and Docling subprocess

## Sources

### Primary (HIGH confidence)
- [FastAPI Users v13.0.0 Release](https://github.com/fastapi-users/fastapi-users/releases/tag/v13.0.0) - pwdlib migration, breaking changes
- [FastAPI Users SQLAlchemy Docs](https://fastapi-users.github.io/fastapi-users/latest/configuration/databases/sqlalchemy/) - database adapter setup
- [Docling PyPI](https://pypi.org/project/docling/) - version 2.77.0, Python 3.10+ requirement
- [redis-py Asyncio Examples](https://redis.readthedocs.io/en/stable/examples/asyncio_examples.html) - connection pool patterns

### Secondary (MEDIUM confidence)
- [pwdlib Introduction](https://www.francoisvoron.com/blog/introducing-pwdlib-a-modern-password-hash-helper-for-python) - author's blog on passlib replacement
- [FastAPI RBAC Documentation](https://app-generator.dev/docs/technologies/fastapi/rbac.html) - JWT claims with role pattern
- [Docling GitHub Issue #1256](https://github.com/docling-project/docling/issues/1256) - multiprocessing guidance

### Tertiary (LOW confidence)
- [JWT Refresh Race Condition](https://medium.com/@backendwithali/race-conditions-in-jwt-refresh-token-rotation-%EF%B8%8F-%EF%B8%8F-5293056146af) - mutex pattern for refresh
- [Token Expiry Best Practices](https://zuplo.com/learning-center/token-expiry-best-practices) - lifetime recommendations

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - FastAPI Users 13.x, pwdlib, Docling all verified from official sources
- Architecture: HIGH - patterns from official docs, CONTEXT.md decisions are clear
- Pitfalls: HIGH - documented in project PITFALLS.md, verified with current sources

**Research date:** 2026-03-09
**Valid until:** 2026-04-09 (30 days - stable ecosystem)
