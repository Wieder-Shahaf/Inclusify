# Phase 6: Admin & Analytics - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Build admin dashboard for site administrators to view usage analytics and manage users/organizations (view-only). This phase delivers:
- Overview tab with KPI cards and recent activity table
- Users tab with searchable user list (view-only)
- Organizations tab with org list and user counts (view-only)
- Backend API endpoints for analytics queries
- Admin-only route protection (site_admin role required)

</domain>

<decisions>
## Implementation Decisions

### Dashboard Layout
- KPI cards at top + data table below (no charts)
- Tabbed navigation: Overview | Users | Organizations
- Default time range: Last 30 days
- Time range dropdown selector: 7 days, 30 days, 90 days, All time
- Recent activity table with pagination (20 items per page)

### KPI Metrics
- 4 core metrics: Total users, Total analyses, Documents processed, Active users (in period)
- Active user = user with at least 1 analysis_run in the time period
- No trend indicators (Claude's discretion on implementation)
- Global stats only (no per-org breakdown)

### User Management
- Table display: email, org, role, last login, status columns
- Search by email
- View-only (no create, edit, or deactivate in v1)
- Invite-only user creation (users self-register via invite, admin doesn't create accounts)

### Organization Management
- View-only: list orgs with user counts
- No create/edit/configure in v1

### Recent Activity Table
- Columns: user email, document name, date, status, issue count
- Pagination with page numbers (20 items per page)

### Admin Roles
- Only site_admin accesses /admin (org_admin treated as regular user in v1)
- Non-admin navigating to /admin sees 404 (matches Phase 05.3 decision)
- No impersonation feature in v1

### Claude's Discretion
- KPI trend indicators (show or hide)
- Activity table column widths and sorting
- Empty state messaging
- Loading skeleton design
- Tab transition animations

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/app/[locale]/admin/page.tsx`: Placeholder exists, ready to build
- `frontend/components/Navbar.tsx`: Admin link already hidden for non-admins
- `backend/app/auth/`: RBAC middleware with role checking exists
- `backend/app/db/repository.py`: Repository pattern for DB queries
- `db/schema.sql`: users, organizations, documents, analysis_runs tables exist
- `frontend/components/ui/`: shadcn-style components (dialog, sheet) available

### Established Patterns
- Backend: FastAPI routers in `backend/app/routers/` or `backend/app/modules/`
- Backend: Pydantic v2 models for request/response validation
- Frontend: next-intl for i18n, messages in `frontend/messages/{locale}.json`
- Frontend: Tailwind v4 + cn() utility for styling
- API pattern: `/api/v1/` prefix, async functions, asyncpg queries

### Integration Points
- `frontend/app/[locale]/admin/page.tsx`: Expand into tabbed dashboard
- `backend/app/main.py`: Mount new admin router
- `backend/app/db/repository.py`: Add analytics query functions
- Auth middleware: Use existing `Depends(current_active_user)` + role check

</code_context>

<specifics>
## Specific Ideas

- "Recent activity" table shows what's happening at a glance - operational view
- Pagination feels right for admin data - predictable, not infinite scroll
- site_admin only keeps v1 simple - org_admin can be enabled later
- View-only for users/orgs is sufficient for v1 monitoring needs

</specifics>

<deferred>
## Deferred Ideas

- org_admin scoped access (see only their org) - enable when multi-tenant use case emerges
- User creation/editing by admin - users self-register for now
- Organization create/edit/configure - seed data sufficient for v1
- User impersonation for support - security complexity, add later if needed
- Trend indicators on KPI cards - can add when more historical data exists
- Per-organization analytics breakdown - global stats sufficient for v1
- Charts/visualizations - tables and KPI cards cover v1 needs

</deferred>

---

*Phase: 06-admin-analytics*
*Context gathered: 2026-03-11*
