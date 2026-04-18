---
phase: 08-achva-feedback
reviewed: 2026-04-18T00:00:00Z
depth: standard
files_reviewed: 25
files_reviewed_list:
  - backend/app/db/models.py
  - backend/app/main.py
  - backend/app/modules/admin/queries.py
  - backend/app/modules/admin/router.py
  - backend/app/modules/admin/schemas.py
  - backend/app/modules/analysis/router.py
  - backend/app/modules/contact/__init__.py
  - backend/app/modules/contact/router.py
  - backend/tests/test_admin_queries.py
  - backend/tests/test_admin_ws.py
  - backend/tests/test_contact.py
  - frontend/__tests__/ProfileSetupModal.test.tsx
  - frontend/__tests__/analyze.test.tsx
  - frontend/__tests__/exportReport.test.ts
  - frontend/app/[locale]/analyze/page.tsx
  - frontend/components/ContactModal.tsx
  - frontend/components/Navbar.tsx
  - frontend/components/ProfileSetupModal.tsx
  - frontend/components/dashboard/FrequencyTrendsCard.tsx
  - frontend/components/dashboard/OverviewTab.tsx
  - frontend/components/dashboard/SimpleBarChart.tsx
  - frontend/lib/api/admin.ts
  - frontend/lib/api/contact.ts
  - frontend/lib/exportReport.ts
  - frontend/messages/en.json
  - frontend/messages/he.json
findings:
  critical: 1
  warning: 5
  info: 5
  total: 11
status: issues_found
---

# Phase 08: Code Review Report

**Reviewed:** 2026-04-18
**Depth:** standard
**Files Reviewed:** 25
**Status:** issues_found

## Summary

This phase introduces the Achva feedback features: the Profile Setup Modal, Contact form (backend + frontend), exportReport PDF utility with base64 return mode, LLM-down health banner on results, admin frequency trends card with WebSocket live updates, and related i18n strings. The implementation is generally solid — the security model for the contact endpoint is correct (recipients always come from DB, not user input), the WebSocket auth logic is well-structured, and the i18n files are symmetric between en/he. One SQL injection vector was found in the admin queries layer. Several warnings exist around incorrect parameter indexing, a logic inversion in private-mode handling, token exposure, and a status value mismatch.

---

## Critical Issues

### CR-01: SQL Injection via Unparameterized HAVING Clause

**File:** `backend/app/modules/admin/queries.py:92`
**Issue:** The `min_analyses` filter is interpolated directly into the SQL string with `f"HAVING COUNT(ar.run_id) >= {int(min_analyses)}"`. Although `int()` coercion eliminates string injection, this is the wrong pattern — if the coercion were ever relaxed or the value came through a different path, this becomes exploitable. Additionally, the value is not passed as a bound parameter, which bypasses the asyncpg parameterised query security model entirely. The correct fix uses a proper `$N` placeholder.

**Fix:**
```python
# In get_users_paginated — instead of f-string interpolation, add to params and use $N:
if min_analyses is not None and min_analyses > 0:
    params.append(min_analyses)
    having_clause = f"HAVING COUNT(ar.run_id) >= ${len(params)}"
```
This ensures the value travels through asyncpg's parameterised path even after future refactors.

---

## Warnings

### WR-01: Wrong Parameter Index for LIMIT/OFFSET in Paginated Query

**File:** `backend/app/modules/admin/queries.py:116`
**Issue:** The `LIMIT $N OFFSET $M` indices are computed as `len(params_with_pagination) - 1` and `len(params_with_pagination)`. `params_with_pagination` is built by appending `page_size` then `offset`, so after appending both, `len(params_with_pagination)` equals the 1-based index of `offset`. The LIMIT index `len(...) - 1` correctly points to `page_size` and the OFFSET index `len(...)` correctly points to `offset` — but only when no `having_clause` is used. When `having_clause` is active, the HAVING value is **not** added to `params_with_pagination` (it is interpolated via f-string), so the indices are still correct by accident. However, if CR-01 is fixed by adding `min_analyses` to `params`, the LIMIT/OFFSET indices must be recalculated. This is a latent off-by-one that will surface immediately on CR-01 fix.

**Fix:** After fixing CR-01, compute pagination indices based on position explicitly:
```python
params_with_pagination = params + [page_size, offset]
limit_idx = len(params_with_pagination) - 1
offset_idx = len(params_with_pagination)
rows = await conn.fetch(
    f"{base_query} ORDER BY u.created_at DESC LIMIT ${limit_idx} OFFSET ${offset_idx}",
    *params_with_pagination,
)
```

### WR-02: Private Mode Logic Inversion in Analysis Router

**File:** `backend/app/modules/analysis/router.py:269`
**Issue:** The request body default for `private_mode` is `False` (line 49: `private_mode: Optional[bool] = False`), and the endpoint docstring states "Privacy mode (default=False)". However, line 269 reads:
```python
private_mode = body.private_mode if body.private_mode is not None else True
```
When the client sends `private_mode=False` explicitly, `body.private_mode` is `False` (falsy but not `None`), so the `if` condition evaluates the truthy branch and assigns `False` — correct. But if `body.private_mode` is sent as `null`/omitted (resulting in `None`), the fallback is `True`, making private mode default to ON inside the handler, contradicting the schema default of `False`. This silent discrepancy means callers who rely on the schema default get the opposite behaviour server-side.

**Fix:** Use the schema default consistently:
```python
private_mode = body.private_mode if body.private_mode is not None else False
```

### WR-03: WebSocket JWT Token Exposed in URL Query String

**File:** `frontend/components/dashboard/FrequencyTrendsCard.tsx:27`
**Issue:** The admin WebSocket is connected using the auth token appended directly to the URL query string:
```ts
const ws = new WebSocket(`${WS_BASE_URL}/api/v1/admin/ws?token=${encodeURIComponent(token)}`);
```
Tokens in URLs are logged by web servers, proxies, CDNs, and browser history. The backend WebSocket endpoint (`admin/router.py:149`) also reads `token: str = None` from the query parameter, confirming this design. While this is a known limitation of the browser WebSocket API (no custom headers on initial handshake), the token source (`localStorage.getItem('auth_token')`) makes the token persistently accessible to any XSS payload.

**Fix:** Short-term — ensure the token is not a long-lived access token (use short-lived tokens or one-time WS tickets). Medium-term — implement a `/api/v1/admin/ws-ticket` endpoint that issues a single-use, short-TTL ticket, and pass that in the URL instead of the full JWT.

### WR-04: Activity Status Badge Never Shows Green ("completed" vs "succeeded")

**File:** `frontend/components/dashboard/OverviewTab.tsx:207-212`
**Issue:** The status badge conditional checks `item.status === 'completed'` to apply green styling. However, the backend `ActivityItem` schema (`admin/schemas.py:71`) documents that status values are `queued, running, succeeded, failed` — there is no `'completed'` value. The DB insert in `analysis/router.py` uses `"succeeded"`. This means the green badge is never applied; all rows will show amber regardless of their actual status.

**Fix:**
```tsx
item.status === 'succeeded'
  ? 'bg-green-50 text-green-600 dark:bg-green-900/20 dark:text-green-400'
  : item.status === 'failed'
  ? 'bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-400'
  : 'bg-amber-50 text-amber-600 dark:bg-amber-900/20 dark:text-amber-400'
```

### WR-05: Contact Endpoint Leaks SMTP Exception Detail to Clients

**File:** `backend/app/modules/contact/router.py:99-102`
**Issue:** When SMTP delivery fails, the raw exception is included in the HTTP 500 response body:
```python
detail=f"SMTP send failed: {exc}",
```
This can expose internal infrastructure information (SMTP server host/port, authentication error messages, internal IP addresses) to end users and potentially to attackers probing the contact endpoint.

**Fix:**
```python
logger.error("SMTP send failed: %s", exc)
raise HTTPException(
    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    detail="Message could not be sent. Please try again later.",
)
```

---

## Info

### IN-01: "Total Users" KPI Card Uses Hardcoded English Label

**File:** `frontend/components/dashboard/OverviewTab.tsx:127`
**Issue:** Three of the four KPI cards use the `translations` prop for their labels, but the "Total Users" card has a hardcoded string `"Total Users"` instead of using `translations.kpis.*`. This string will not be translated on the Hebrew locale.

**Fix:** Add a `totalUsers` key to the `translations.kpis` type and prop, and pass `translations.kpis.totalUsers` to the card. The i18n key `admin.kpi.activeUsers` already has a Hebrew counterpart — add `totalUsers` to `en.json` and `he.json` accordingly.

### IN-02: `UserItem` Frontend Type Is Missing `analysis_count` and `institution`

**File:** `frontend/lib/api/admin.ts:14-21`
**Issue:** The `UserItem` interface in the frontend admin API client is missing two fields that the backend `UserItem` schema (`admin/schemas.py:34-41`) includes: `analysis_count: int` and `institution: Optional[str]`. The `UsersTab` component likely accesses these fields but will get `undefined` at runtime (TypeScript won't catch it since the type doesn't declare them).

**Fix:**
```ts
export interface UserItem {
  user_id: string;
  email: string;
  role: string;
  last_login_at: string | null;
  created_at: string;
  analysis_count: number;
  institution: string | null;
}
```

### IN-03: `console.error` Left in Production Code Path

**File:** `frontend/app/[locale]/analyze/page.tsx:183`
**Issue:** `console.error('Analysis failed:', error)` is present in the production catch block. The error is already surfaced via `handleApiError` → `setErrorMessage` → UI display. The `console.error` exposes stack traces to end-user browser consoles.

**Fix:** Remove the `console.error` call or replace it with a structured logger if one exists in the project. The error handling is already complete without it.

### IN-04: `ProfileSetupModal` Dismiss Writes to `sessionStorage` Inside Dialog `onOpenChange`

**File:** `frontend/components/ProfileSetupModal.tsx:70`
**Issue:** `Dialog.Root onOpenChange={(v) => { if (!v) dismiss(); }` calls `dismiss()` which writes `sessionStorage.setItem(DISMISSED_KEY, '1')`. This means closing the dialog via the Escape key or clicking the overlay (both trigger `onOpenChange(false)`) permanently sets the dismissed flag for the session, same as the explicit "Skip" button. This may be intentional, but it means a user who accidentally closes the modal cannot be prompted again in the same session, even though they never explicitly skipped. The test at line 77-80 in `ProfileSetupModal.test.tsx` confirms this is the tested behaviour. Document this as an explicit decision if intentional; otherwise restrict `dismiss()` to explicit user actions only.

**Fix (if unintentional):**
```tsx
// Only set the key on explicit skip, not on every close
<Dialog.Root open={open} onOpenChange={(v) => { if (!v) setOpen(false); }}>
```
And call `dismiss()` only from the "Skip" button handler.

### IN-05: `FrequencyTrendsCard` WebSocket Effect Missing `refresh` in Dependency Array

**File:** `frontend/components/dashboard/FrequencyTrendsCard.tsx:44`
**Issue:** The `useEffect` that opens the WebSocket intentionally omits `refresh` from its dependency array with a `// eslint-disable-next-line react-hooks/exhaustive-deps` comment (line 43). While `refresh` (the SWR `mutate` function) is stable across renders in practice, relying on eslint suppression to hide this is fragile. If the hook implementation ever changes to return a new function reference, the stale closure will silently use an outdated `refresh`. This is a low-risk lint suppression but worth noting.

**Fix:** Wrap `refresh` in `useCallback` or `useRef` if the upstream hook doesn't guarantee referential stability, or document why the omission is safe.

---

_Reviewed: 2026-04-18_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
