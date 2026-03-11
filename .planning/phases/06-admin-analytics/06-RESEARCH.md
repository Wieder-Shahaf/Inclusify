# Phase 6: Admin & Analytics - Research

**Researched:** 2026-03-11
**Domain:** Admin dashboard with analytics queries, user/org management views
**Confidence:** HIGH

## Summary

Phase 6 builds an admin dashboard for site administrators to view usage analytics and manage users/organizations (view-only in v1). The implementation consists of two main parts: (1) backend API endpoints with PostgreSQL aggregate queries for analytics data, and (2) a tabbed frontend dashboard replacing the current mock data implementation.

The existing codebase provides strong foundations: `AdminGuard` component enforces site_admin access, `require_admin` dependency handles backend authorization, the database schema includes all necessary tables (`users`, `organizations`, `documents`, `analysis_runs`), and the frontend already has a placeholder admin dashboard with mock data. The primary work involves replacing mock data with real API calls and implementing efficient aggregate queries.

**Primary recommendation:** Use asyncpg's raw SQL for analytics queries (faster than ORM for aggregates), implement pagination with LIMIT/OFFSET for activity tables, and leverage existing AuthGuard and RBAC patterns. Keep frontend data fetching in client components with SWR for caching.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- KPI cards at top + data table below (no charts)
- Tabbed navigation: Overview | Users | Organizations
- Default time range: Last 30 days
- Time range dropdown selector: 7 days, 30 days, 90 days, All time
- Recent activity table with pagination (20 items per page)
- 4 core metrics: Total users, Total analyses, Documents processed, Active users (in period)
- Active user = user with at least 1 analysis_run in the time period
- No trend indicators (Claude's discretion on implementation)
- Global stats only (no per-org breakdown)
- User table display: email, org, role, last login, status columns
- Search by email
- View-only (no create, edit, or deactivate in v1)
- Organization table: list orgs with user counts
- Activity table columns: user email, document name, date, status, issue count
- Only site_admin accesses /admin (org_admin treated as regular user in v1)
- Non-admin navigating to /admin sees 404

### Claude's Discretion
- KPI trend indicators (show or hide)
- Activity table column widths and sorting
- Empty state messaging
- Loading skeleton design
- Tab transition animations

### Deferred Ideas (OUT OF SCOPE)
- org_admin scoped access (see only their org)
- User creation/editing by admin
- Organization create/edit/configure
- User impersonation for support
- Trend indicators on KPI cards
- Per-organization analytics breakdown
- Charts/visualizations
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ADMIN-01 | Admin dashboard with real analytics | Aggregate queries for KPIs, asyncpg raw SQL patterns, time-range filtering with DATE_TRUNC |
| ADMIN-02 | Admin user/organization management | List endpoints with pagination, search by email filter, asyncpg fetchrow/fetch patterns |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| asyncpg | 0.29+ | PostgreSQL async driver | Already in use, optimal for aggregate queries without ORM overhead |
| FastAPI | 0.115+ | API framework | Already in use, Depends pattern for auth |
| Pydantic v2 | 2.9+ | Response schemas | Already in use, TypeAdapter for complex types |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| SWR | 2.2+ | Client-side data fetching | Frontend data loading with caching and revalidation |
| TanStack Table | 8.20+ | Table state management | If complex sorting/filtering needed (optional - may not need for view-only) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Raw asyncpg | SQLAlchemy 2.0 | ORM adds overhead for aggregate queries; raw SQL is clearer for analytics |
| SWR | React Query | SWR is simpler, already familiar pattern in Next.js ecosystem |
| TanStack Table | Native table | TanStack adds complexity; native table sufficient for view-only lists |

**Installation:**
```bash
# Backend: No new packages needed (asyncpg already installed)
# Frontend: SWR for data fetching
cd frontend && npm install swr
```

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── modules/
│   └── admin/
│       ├── __init__.py
│       ├── router.py         # Admin API endpoints
│       ├── schemas.py        # Pydantic response models
│       └── queries.py        # Raw SQL analytics queries
frontend/
├── app/[locale]/admin/
│   └── page.tsx              # Existing - update to use real data
├── components/dashboard/
│   ├── AdminDashboard.tsx    # Existing - refactor to tabs
│   ├── OverviewTab.tsx       # New - KPIs + activity
│   ├── UsersTab.tsx          # New - user list
│   └── OrganizationsTab.tsx  # New - org list
├── lib/api/
│   └── admin.ts              # Admin API client functions
```

### Pattern 1: Raw SQL for Analytics Queries
**What:** Use asyncpg's execute/fetch directly instead of ORM for aggregate queries
**When to use:** Always for COUNT/SUM/aggregate operations
**Example:**
```python
# Source: Established asyncpg pattern in backend/app/db/repository.py
async def get_analytics_kpis(conn: asyncpg.Connection, days: int) -> dict:
    """Fetch KPI metrics for admin dashboard."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Total users (all time)
    total_users = await conn.fetchval("SELECT COUNT(*) FROM users")

    # Active users (users with analysis_run in period)
    active_users = await conn.fetchval("""
        SELECT COUNT(DISTINCT d.user_id)
        FROM analysis_runs ar
        JOIN documents d ON ar.document_id = d.document_id
        WHERE ar.started_at >= $1
    """, cutoff)

    # Total analyses in period
    total_analyses = await conn.fetchval("""
        SELECT COUNT(*) FROM analysis_runs
        WHERE started_at >= $1
    """, cutoff)

    # Documents processed in period
    docs_processed = await conn.fetchval("""
        SELECT COUNT(DISTINCT document_id) FROM analysis_runs
        WHERE started_at >= $1 AND status = 'succeeded'
    """, cutoff)

    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_analyses": total_analyses,
        "documents_processed": docs_processed
    }
```

### Pattern 2: Paginated List Queries
**What:** LIMIT/OFFSET pagination with total count for admin tables
**When to use:** Users list, Organizations list, Activity table
**Example:**
```python
# Source: Standard PostgreSQL pagination pattern
async def get_users_paginated(
    conn: asyncpg.Connection,
    page: int = 1,
    page_size: int = 20,
    email_search: Optional[str] = None
) -> tuple[list[dict], int]:
    """Get paginated user list with optional email search."""
    offset = (page - 1) * page_size

    # Build WHERE clause for search
    where_clause = ""
    params = [page_size, offset]
    if email_search:
        where_clause = "WHERE u.email ILIKE $3"
        params.append(f"%{email_search}%")

    # Get total count
    count_sql = f"SELECT COUNT(*) FROM users u {where_clause}"
    total = await conn.fetchval(count_sql, *params[2:] if email_search else [])

    # Get page data
    query = f"""
        SELECT u.user_id, u.email, u.role, u.last_login_at, u.created_at,
               o.name as org_name
        FROM users u
        JOIN organizations o ON u.org_id = o.org_id
        {where_clause}
        ORDER BY u.created_at DESC
        LIMIT $1 OFFSET $2
    """
    rows = await conn.fetch(query, *params)

    return [dict(r) for r in rows], total
```

### Pattern 3: Admin Route Protection
**What:** Use existing require_admin dependency for all admin endpoints
**When to use:** Every admin API route
**Example:**
```python
# Source: backend/app/auth/deps.py
from app.auth.deps import require_admin

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])

@router.get("/analytics")
async def get_analytics(
    user: dict = Depends(require_admin),  # Returns 403 if not site_admin
    days: int = Query(default=30, ge=1, le=365),
    request: Request = None
):
    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        return await get_analytics_kpis(conn, days)
```

### Pattern 4: Frontend Data Fetching with SWR
**What:** Client-side data fetching with automatic caching and revalidation
**When to use:** All admin dashboard data
**Example:**
```typescript
// Source: SWR documentation pattern
import useSWR from 'swr';
import { fetchWithAuth } from '@/lib/api/client';

const fetcher = (url: string) =>
  fetchWithAuth(url).then(res => res.json());

export function useAdminKPIs(days: number) {
  const { data, error, isLoading, mutate } = useSWR(
    `/api/v1/admin/analytics?days=${days}`,
    fetcher,
    {
      revalidateOnFocus: false,
      dedupingInterval: 60000  // Cache for 60s
    }
  );

  return {
    kpis: data,
    isLoading,
    isError: error,
    refresh: mutate
  };
}
```

### Anti-Patterns to Avoid
- **N+1 queries:** Don't fetch user counts per org separately; use JOIN with GROUP BY
- **Client-side filtering of large datasets:** Always filter/paginate on server
- **Exposing internal IDs unnecessarily:** Return only needed fields in responses
- **Hardcoding time ranges:** Use query parameters for flexibility

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pagination state | Custom page tracking | URL search params + server | Shareable URLs, browser back works |
| Date range filtering | Complex date math | PostgreSQL DATE_TRUNC + interval | Database optimized, timezone-safe |
| Auth checking | Manual JWT parsing | Existing require_admin dependency | Already implemented, tested |
| Data caching | Custom cache | SWR with dedupingInterval | Handles race conditions, revalidation |

**Key insight:** The existing codebase already has authentication, authorization, and database patterns established. Phase 6 should follow these patterns exactly rather than introducing new approaches.

## Common Pitfalls

### Pitfall 1: Slow Aggregate Queries on Large Tables
**What goes wrong:** COUNT(*) scans entire table, becomes slow with millions of rows
**Why it happens:** No index support for COUNT, full table scan required
**How to avoid:** For v1 scale (hundreds of users), this is fine. For larger scale, pre-aggregate or use EXPLAIN ANALYZE to monitor
**Warning signs:** Query time > 100ms for simple counts

### Pitfall 2: Missing Index on Time-Based Filters
**What goes wrong:** WHERE started_at >= $1 scans full table
**Why it happens:** No index on timestamp columns used in analytics queries
**How to avoid:** Existing index `idx_runs_status` helps; may need `idx_runs_started_at` for time queries
**Warning signs:** EXPLAIN shows Seq Scan on analysis_runs for time filters

### Pitfall 3: Frontend Loading State Race Conditions
**What goes wrong:** Multiple rapid time-range changes cause stale data display
**Why it happens:** Async responses arrive out of order
**How to avoid:** SWR handles this automatically with request deduplication; use mutate() for manual refresh
**Warning signs:** KPI cards show data from wrong time range after rapid clicking

### Pitfall 4: Tab State Not Preserved on Navigation
**What goes wrong:** User switches tabs, navigates away, returns to default tab
**Why it happens:** Tab state stored only in React state
**How to avoid:** Store active tab in URL search params (?tab=users)
**Warning signs:** User complaints about losing place in admin dashboard

### Pitfall 5: Exposing Sensitive User Data
**What goes wrong:** Admin API returns password_hash or other sensitive fields
**Why it happens:** Using SELECT * or not defining explicit response schema
**How to avoid:** Always use Pydantic response models with explicit field list
**Warning signs:** password_hash visible in network tab

## Code Examples

Verified patterns from official sources:

### Admin Router Setup
```python
# backend/app/modules/admin/router.py
from fastapi import APIRouter, Depends, Query, Request
from app.auth.deps import require_admin
from .schemas import AnalyticsResponse, UsersListResponse, OrgsListResponse, ActivityResponse
from . import queries

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])

@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    user: dict = Depends(require_admin),
    days: int = Query(default=30, ge=1, le=365, description="Time range in days"),
    request: Request = None
):
    """Get KPI metrics for admin dashboard."""
    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        return await queries.get_analytics_kpis(conn, days)

@router.get("/users", response_model=UsersListResponse)
async def list_users(
    user: dict = Depends(require_admin),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str = Query(default=None, max_length=100),
    request: Request = None
):
    """Get paginated list of users."""
    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        users, total = await queries.get_users_paginated(conn, page, page_size, search)
        return {
            "users": users,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }

@router.get("/organizations", response_model=OrgsListResponse)
async def list_organizations(
    user: dict = Depends(require_admin),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    request: Request = None
):
    """Get paginated list of organizations with user counts."""
    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        orgs, total = await queries.get_orgs_paginated(conn, page, page_size)
        return {
            "organizations": orgs,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }

@router.get("/activity", response_model=ActivityResponse)
async def get_recent_activity(
    user: dict = Depends(require_admin),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    days: int = Query(default=30, ge=1, le=365),
    request: Request = None
):
    """Get recent analysis activity for admin dashboard."""
    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        activity, total = await queries.get_recent_activity(conn, page, page_size, days)
        return {
            "activity": activity,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
```

### Pydantic Response Schemas
```python
# backend/app/modules/admin/schemas.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

class AnalyticsResponse(BaseModel):
    total_users: int
    active_users: int
    total_analyses: int
    documents_processed: int

class UserItem(BaseModel):
    user_id: UUID
    email: str
    role: str
    org_name: str
    last_login_at: Optional[datetime]
    created_at: datetime

class UsersListResponse(BaseModel):
    users: list[UserItem]
    total: int
    page: int
    page_size: int
    total_pages: int

class OrgItem(BaseModel):
    org_id: UUID
    name: str
    slug: Optional[str]
    user_count: int
    created_at: datetime

class OrgsListResponse(BaseModel):
    organizations: list[OrgItem]
    total: int
    page: int
    page_size: int
    total_pages: int

class ActivityItem(BaseModel):
    run_id: UUID
    user_email: str
    document_name: Optional[str]
    started_at: datetime
    status: str
    issue_count: int

class ActivityResponse(BaseModel):
    activity: list[ActivityItem]
    total: int
    page: int
    page_size: int
    total_pages: int
```

### Activity Query with Finding Count
```python
# backend/app/modules/admin/queries.py (get_recent_activity)
async def get_recent_activity(
    conn: asyncpg.Connection,
    page: int,
    page_size: int,
    days: int
) -> tuple[list[dict], int]:
    """Get recent analysis runs with issue counts."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    offset = (page - 1) * page_size

    # Count total
    total = await conn.fetchval("""
        SELECT COUNT(*) FROM analysis_runs
        WHERE started_at >= $1
    """, cutoff)

    # Get activity with joined data
    rows = await conn.fetch("""
        SELECT
            ar.run_id,
            u.email as user_email,
            d.original_filename as document_name,
            ar.started_at,
            ar.status,
            (SELECT COUNT(*) FROM findings f WHERE f.run_id = ar.run_id) as issue_count
        FROM analysis_runs ar
        JOIN documents d ON ar.document_id = d.document_id
        LEFT JOIN users u ON d.user_id = u.user_id
        WHERE ar.started_at >= $1
        ORDER BY ar.started_at DESC
        LIMIT $2 OFFSET $3
    """, cutoff, page_size, offset)

    return [dict(r) for r in rows], total
```

### Frontend Tab Component Structure
```typescript
// frontend/components/dashboard/AdminDashboard.tsx (refactored)
'use client';

import { useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import OverviewTab from './OverviewTab';
import UsersTab from './UsersTab';
import OrganizationsTab from './OrganizationsTab';

type TabKey = 'overview' | 'users' | 'organizations';

export default function AdminDashboard({ translations }: Props) {
  const searchParams = useSearchParams();
  const router = useRouter();

  const activeTab = (searchParams.get('tab') as TabKey) || 'overview';

  const setActiveTab = (tab: TabKey) => {
    const params = new URLSearchParams(searchParams);
    params.set('tab', tab);
    router.push(`?${params.toString()}`);
  };

  const tabs = [
    { key: 'overview', label: translations.tabs.overview },
    { key: 'users', label: translations.tabs.users },
    { key: 'organizations', label: translations.tabs.organizations },
  ];

  return (
    <div className="py-4 px-2 space-y-4">
      {/* Tab Navigation */}
      <div className="flex border-b border-slate-200 dark:border-slate-700">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as TabKey)}
            className={cn(
              'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
              activeTab === tab.key
                ? 'border-pride-purple text-pride-purple'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && <OverviewTab translations={translations} />}
      {activeTab === 'users' && <UsersTab translations={translations} />}
      {activeTab === 'organizations' && <OrganizationsTab translations={translations} />}
    </div>
  );
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| ORM for analytics | Raw SQL aggregates | Always for analytics | 2-5x faster queries |
| Client-side pagination | Server-side with LIMIT/OFFSET | Standard practice | Handles large datasets |
| useEffect + useState | SWR/React Query | 2023+ | Better caching, less code |
| Manual auth checks | Dependency injection | FastAPI pattern | Consistent, testable |

**Deprecated/outdated:**
- Using `getServerSideProps` for admin data: App Router uses async Server Components or client fetching
- Chart libraries for simple metrics: KPI cards are sufficient per CONTEXT.md decision

## Open Questions

1. **Index Strategy for Time-Based Queries**
   - What we know: `idx_runs_status` exists; time-based WHERE needs indexing for scale
   - What's unclear: Whether current data volume requires additional index
   - Recommendation: Monitor query performance; add `CREATE INDEX idx_runs_started_at ON analysis_runs(started_at)` if queries > 50ms

2. **Caching Strategy**
   - What we know: SWR provides client-side caching with 60s deduping
   - What's unclear: Whether Redis server-side caching is needed for analytics
   - Recommendation: Start without server-side caching; add if dashboard is slow under load

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio |
| Config file | None - uses defaults with conftest.py |
| Quick run command | `cd backend && python -m pytest tests/test_admin.py -x` |
| Full suite command | `cd backend && python -m pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ADMIN-01 | KPI analytics endpoint returns counts | unit | `pytest tests/test_admin.py::test_analytics_kpis -x` | Wave 0 |
| ADMIN-01 | Time range filtering works | unit | `pytest tests/test_admin.py::test_analytics_time_range -x` | Wave 0 |
| ADMIN-02 | Users list endpoint paginated | unit | `pytest tests/test_admin.py::test_users_list_pagination -x` | Wave 0 |
| ADMIN-02 | Users search by email | unit | `pytest tests/test_admin.py::test_users_search -x` | Wave 0 |
| ADMIN-02 | Organizations list with user counts | unit | `pytest tests/test_admin.py::test_orgs_list -x` | Wave 0 |
| ADMIN-01/02 | Non-admin gets 403 | unit | `pytest tests/test_admin.py::test_admin_auth_required -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_admin.py -x`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_admin.py` - covers ADMIN-01, ADMIN-02 backend endpoints
- [ ] Mock data fixtures for admin tests in `tests/conftest.py`

## Sources

### Primary (HIGH confidence)
- Existing codebase: `backend/app/auth/deps.py` - RBAC pattern with require_admin
- Existing codebase: `backend/app/db/repository.py` - asyncpg query patterns
- Existing codebase: `frontend/components/auth/AuthGuard.tsx` - AdminGuard pattern
- Existing codebase: `db/schema.sql` - Database schema for users, orgs, analysis_runs, findings

### Secondary (MEDIUM confidence)
- [FastAPI async database patterns](https://oneuptime.com/blog/post/2026-02-02-fastapi-async-database/view) - asyncpg best practices 2026
- [PostgreSQL DATE_TRUNC](https://www.datacamp.com/doc/postgresql/date_trunc) - Time-based aggregation
- [shadcn DataTable pagination](https://ui.shadcn.com/docs/components/radix/data-table) - Pagination UI patterns
- [SWR documentation](https://swr.vercel.app/) - Client-side data fetching

### Tertiary (LOW confidence)
- Web search results for FastAPI admin panels - general patterns only

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already in use in codebase
- Architecture: HIGH - follows established patterns from existing routers
- Pitfalls: MEDIUM - based on general PostgreSQL/FastAPI experience
- Frontend patterns: MEDIUM - SWR is standard but not yet in this codebase

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (30 days - stable patterns)
