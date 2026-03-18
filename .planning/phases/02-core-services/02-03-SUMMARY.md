---
phase: 02-core-services
plan: 03
subsystem: rbac
tags: [rbac, fastapi, jwt, authorization, middleware]

# Dependency graph
requires:
  - phase: 02-core-services
    plan: 01
    provides: JWT auth with role claims, current_active_user dependency
provides:
  - RBAC dependency factories (require_role, require_admin, require_org_admin)
  - Role hierarchy enforcement (site_admin > org_admin > user)
  - Protected API endpoints requiring authentication
affects: [03-analysis, frontend-api, admin-dashboard]

# Tech tracking
tech-stack:
  added: []
  patterns: [role hierarchy, dependency factory, JWT claims authorization]

key-files:
  created:
    - backend/app/auth/deps.py
    - backend/tests/test_rbac.py
  modified:
    - backend/app/modules/analysis/router.py
    - backend/app/modules/ingestion/router.py

key-decisions:
  - "Role hierarchy using numeric levels (3 > 2 > 1) for easy comparison"
  - "JWT audience passed as string to jose.jwt.decode (not list)"
  - "403 Forbidden with 'Insufficient permissions' per CONTEXT.md"
  - "401 for missing/invalid tokens, 403 for insufficient role"

patterns-established:
  - "require_role() factory returns dependency for route-level RBAC"
  - "Dependencies can return user dict for downstream use"
  - "TDD for authorization: test all role combinations"

requirements-completed: [AUTH-02]

# Metrics
duration: 2min
completed: 2026-03-09
---

# Phase 02 Plan 03: RBAC Middleware Summary

**Role-based access control using JWT claims with require_role() dependency factory and protected API endpoints**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-09T10:12:18Z
- **Completed:** 2026-03-09T10:14:30Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Created RBAC dependency factories in backend/app/auth/deps.py
- Role hierarchy: site_admin (3) > org_admin (2) > user (1)
- require_role() factory for route-level authorization
- get_current_user_from_token() for JWT claim extraction
- Convenience dependencies: require_admin, require_org_admin, require_authenticated
- Protected /api/v1/analysis/analyze endpoint with current_active_user
- Protected /api/v1/ingestion/upload endpoint with current_active_user
- 10 comprehensive RBAC tests covering all role combinations

## Task Commits

Each task was committed atomically:

1. **Task 1: Create RBAC dependency factories (TDD)**
   - `e018e48` - feat(02-03): add RBAC deps with require_role factory (TDD)

2. **Task 2: Protect existing API endpoints with authentication**
   - `745044d` - feat(02-03): protect analysis and ingestion endpoints with auth

## Files Created/Modified

- `backend/app/auth/deps.py` - RBAC dependencies with role hierarchy
- `backend/tests/test_rbac.py` - 10 tests for role-based access control
- `backend/app/modules/analysis/router.py` - Added current_active_user dependency
- `backend/app/modules/ingestion/router.py` - Added current_active_user dependency

## Key Exports

From `backend/app/auth/deps.py`:
```python
from app.auth.deps import (
    require_role,           # Factory: require_role("site_admin")
    require_admin,          # Convenience: site_admin only
    require_org_admin,      # Convenience: org_admin or higher
    require_authenticated,  # Convenience: any authenticated user
    get_current_user_from_token,  # Returns JWT claims dict
    ROLE_HIERARCHY,         # {"site_admin": 3, "org_admin": 2, "user": 1}
)
```

## Usage Examples

```python
# Route-level protection (no access to user data)
@router.get("/admin", dependencies=[Depends(require_admin)])
async def admin_endpoint():
    return {"message": "admin only"}

# With user data access
@router.get("/profile")
async def get_profile(user: dict = Depends(require_role("user"))):
    return {"user_id": user["sub"], "role": user["role"]}
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] JWT audience parameter type**
- **Found during:** Task 1 (tests failing with 401)
- **Issue:** jose.jwt.decode expects audience as string, not list
- **Fix:** Changed `audience=["fastapi-users:auth"]` to `audience="fastapi-users:auth"`
- **Files modified:** backend/app/auth/deps.py
- **Verification:** All 10 tests pass
- **Committed in:** e018e48

---

**Total deviations:** 1 auto-fixed (bug)
**Impact on plan:** Minor fix during TDD cycle. No scope creep.

## Issues Encountered

None - plan executed smoothly.

## User Setup Required

None - authentication infrastructure was already set up in Plan 01.

## Next Phase Readiness

- RBAC foundation complete, ready for admin-specific endpoints
- require_role() can be used with any role level
- Analysis and ingestion endpoints now require authentication
- Frontend will need to pass Bearer token for API calls

## Self-Check: PASSED

All 4 files verified present:
- backend/app/auth/deps.py - FOUND
- backend/tests/test_rbac.py - FOUND
- backend/app/modules/analysis/router.py - FOUND (modified)
- backend/app/modules/ingestion/router.py - FOUND (modified)

All 2 task commits verified in git log:
- e018e48 - FOUND
- 745044d - FOUND

---
*Phase: 02-core-services*
*Completed: 2026-03-09*
