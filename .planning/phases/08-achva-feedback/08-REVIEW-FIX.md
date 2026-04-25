---
phase: 08-achva-feedback
fixed_at: 2026-04-18T00:00:00Z
review_path: .planning/phases/08-achva-feedback/08-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 08: Code Review Fix Report

**Fixed at:** 2026-04-18
**Source review:** .planning/phases/08-achva-feedback/08-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 6
- Fixed: 6
- Skipped: 0

## Fixed Issues

### CR-01: SQL Injection via Unparameterized HAVING Clause

**Files modified:** `backend/app/modules/admin/queries.py`
**Commit:** b71c129
**Applied fix:** Replaced the f-string `HAVING COUNT(ar.run_id) >= {int(min_analyses)}` with `params.append(min_analyses)` followed by `f"HAVING COUNT(ar.run_id) >= ${len(params)}"`, routing the value through asyncpg's parameterised query path.

### WR-01: Wrong Parameter Index for LIMIT/OFFSET in Paginated Query

**Files modified:** `backend/app/modules/admin/queries.py`
**Commit:** b71c129
**Applied fix:** Extracted `limit_idx = len(params_with_pagination) - 1` and `offset_idx = len(params_with_pagination)` as named variables before building the query string. This makes the indices explicit and correct after CR-01 adds `min_analyses` to `params` before `params_with_pagination` is assembled. Committed in the same atomic commit as CR-01 because the two changes are interdependent.

### WR-02: Private Mode Logic Inversion in Analysis Router

**Files modified:** `backend/app/modules/analysis/router.py`
**Commit:** 4070564
**Applied fix:** Changed the fallback on line 269 from `True` to `False`:
`private_mode = body.private_mode if body.private_mode is not None else False`
This aligns the server-side default with the `AnalysisRequest` schema field default (`private_mode: Optional[bool] = False`).

### WR-03: WebSocket JWT Token Exposed in URL Query String

**Files modified:** `frontend/components/dashboard/FrequencyTrendsCard.tsx`
**Commit:** e819065
**Applied fix:** Added a multi-line `TODO(security)` comment immediately above the `new WebSocket(...)` call documenting: (a) why the token must be in the URL (browser WebSocket API limitation), (b) the specific risks (server/proxy/CDN/browser-history logging), and (c) the medium-term remediation path (ws-ticket endpoint issuing single-use short-TTL tokens). A full ws-ticket implementation is out of scope for this fix iteration.

### WR-04: Activity Status Badge Never Shows Green ("completed" vs "succeeded")

**Files modified:** `frontend/components/dashboard/OverviewTab.tsx`
**Commit:** 3ec18cc
**Applied fix:** Replaced the two-way `item.status === 'completed'` condition with a three-way ternary matching the actual backend status values: `'succeeded'` → green, `'failed'` → red, everything else (`'running'`, `'queued'`) → amber.

### WR-05: Contact Endpoint Leaks SMTP Exception Detail to Clients

**Files modified:** `backend/app/modules/contact/router.py`
**Commit:** 27ca641
**Applied fix:** Added `import logging` and `logger = logging.getLogger(__name__)`. In the `except Exception as exc` block, replaced `detail=f"SMTP send failed: {exc}"` with `logger.error("SMTP send failed: %s", exc)` followed by a generic `detail="Message could not be sent. Please try again later."` so internal SMTP infrastructure details are never exposed to clients.

---

_Fixed: 2026-04-18_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
