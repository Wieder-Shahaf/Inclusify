---
phase: 8
plan: "08-05"
subsystem: admin-analytics
tags: [websocket, admin, analytics, bar-chart, swr, real-time, d3-free]
dependency_graph:
  requires: ["08-04"]
  provides: ["admin-frequency-trends-endpoint", "admin-ws-manager", "frequency-trends-card"]
  affects: ["backend/app/modules/admin/router.py", "backend/app/modules/analysis/router.py", "frontend/components/dashboard/OverviewTab.tsx"]
tech_stack:
  added: ["AdminWSManager (custom WebSocket manager)", "SimpleBarChart (custom SVG bar chart)"]
  patterns: ["Manual JWT auth in WebSocket handler", "SWR + WebSocket hybrid refresh", "SVG bar chart via useMemo"]
key_files:
  created:
    - backend/tests/test_admin_queries.py
    - backend/tests/test_admin_ws.py
    - frontend/components/dashboard/SimpleBarChart.tsx
    - frontend/components/dashboard/FrequencyTrendsCard.tsx
  modified:
    - backend/app/modules/admin/queries.py
    - backend/app/modules/admin/schemas.py
    - backend/app/modules/admin/router.py
    - backend/app/modules/analysis/router.py
    - frontend/lib/api/admin.ts
    - frontend/components/dashboard/OverviewTab.tsx
    - frontend/messages/en.json
    - frontend/messages/he.json
decisions:
  - "WebSocket JWT auth via query param (token=...) — Depends() injection does not work in FastAPI WS handlers"
  - "AdminWSManager as module-level singleton in admin/router.py — imported directly by analysis/router.py"
  - "Broadcast wrapped in try/except so WS failures never fail the analysis request"
  - "WS close code 4001 for missing/invalid token; 4003 for non-admin role"
  - "Custom SVG bar chart (SimpleBarChart) — no D3 dependency, follows existing SimpleLineChart pattern"
  - "FrequencyTrendsCard useEffect deps [locale] only — refresh not included to avoid reconnect loops"
metrics:
  duration: "~25 minutes"
  completed: "2026-04-18"
  tasks_completed: 3
  tests_added: 9
  files_changed: 12
---

# Phase 8 Plan 05: Admin Label Frequency Trends with WebSocket Auto-Refresh Summary

**One-liner:** Admin bar chart of finding categories with top-5 phrase drilldown and JWT-authenticated WebSocket auto-refresh on new_analysis events.

## What Was Built

### Task 1: Backend SQL Query + Schemas + HTTP Endpoint (TDD)

- **`get_label_frequency_trends(conn, days)`** added to `admin/queries.py` — JOINs `findings` and `analysis_runs`, groups by category, uses Python `Counter` to compute top-5 excerpts per category sorted by count descending
- **Pydantic schemas** added to `admin/schemas.py`: `TopPhrase`, `FrequencyTrendItem`, `FrequencyTrendsResponse`
- **`GET /api/v1/admin/frequency-trends`** HTTP endpoint added to `admin/router.py` — requires `site_admin` role via `Depends(require_admin)`, `days` param (1–365, default 30)
- **4 tests** in `test_admin_queries.py`: empty result, correct shape/aggregation, top-5 limit and sort order, cutoff parameter forwarded correctly

### Task 2: Backend WebSocket + AdminWSManager + Broadcast Hook (TDD)

- **`AdminWSManager` class** added to `admin/router.py` with `connect()`, `disconnect()`, `broadcast()` (dead-connection cleanup on send failure)
- **`ws_manager` module-level singleton** — importable by analysis router without circular import
- **`@router.websocket("/ws")`** endpoint with manual JWT auth (`Depends()` does not work in WS handlers): missing token → close 4001, invalid JWT → close 4001, non-admin role → close 4003; valid admin → accept and keep-alive
- **Broadcast hook** in `analysis/router.py` — imports `ws_manager`, fires `{"event": "new_analysis"}` after `_persist_results()` succeeds, wrapped in `try/except` to never block the analysis response
- **5 tests** in `test_admin_ws.py`: 2 broadcast unit tests (sends to all, removes dead), 3 WS auth tests (missing token, invalid JWT, non-admin)

### Task 3: Frontend SWR Hook + Components + Integration + i18n

- **`useAdminFrequencyTrends(days)`** SWR hook + `FrequencyTrendsResponse`/`FrequencyTrendItem`/`TopPhrase` interfaces added to `lib/api/admin.ts`
- **`SimpleBarChart.tsx`** — custom SVG bar chart, no external charting library, follows `SimpleLineChart` pattern: `useMemo` for bar geometry, `<rect rx="4">` bars with value labels above and truncated category labels below
- **`FrequencyTrendsCard.tsx`** — full card component: bar chart + per-category expandable top-5 phrase list with `AnimatePresence` height animation; WebSocket connection with pulsing green dot when connected; auto-calls `refresh()` on `new_analysis` WS event; redirects to login on 4001 (expired token)
- **`OverviewTab.tsx`** — `FrequencyTrendsCard` imported and rendered below the activity table, receives `days` prop from parent
- **i18n keys** added under `admin.frequencyTrends` in both `en.json` and `he.json`

## Tests

| Suite | Tests | Status |
|-------|-------|--------|
| test_admin_queries.py | 4 | GREEN |
| test_admin_ws.py | 5 | GREEN |
| **Total** | **9** | **9/9 PASS** |

## Commits

| Hash | Message |
|------|---------|
| f69cfc9 | feat(08-05): add get_label_frequency_trends query + /frequency-trends endpoint (D-05) |
| d6e9d63 | feat(08-05): add AdminWSManager + WebSocket endpoint + analysis broadcast (D-05) |
| b573ab8 | feat(08-05): add SWR hook + SimpleBarChart + FrequencyTrendsCard + WS integration (D-05) |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all data flows from real DB queries. `useAdminFrequencyTrends` fetches from live `/api/v1/admin/frequency-trends` endpoint.

## Threat Flags

None — all trust boundaries from the plan's threat model were implemented as specified:
- T-08-05-01: Manual JWT decode in WS handler (4001/4003 close codes)
- T-08-05-02: `Depends(require_admin)` on HTTP endpoint
- T-08-05-06: `algorithms=["HS256"]` explicitly enumerated
- T-08-05-07: Broadcast in try/except in analysis router

## Self-Check: PASSED

- `backend/app/modules/admin/queries.py` — contains `get_label_frequency_trends` ✓
- `backend/app/modules/admin/schemas.py` — contains `FrequencyTrendsResponse` ✓
- `backend/app/modules/admin/router.py` — contains `AdminWSManager`, `ws_manager`, `/frequency-trends`, `/ws` endpoints ✓
- `backend/app/modules/analysis/router.py` — contains `ws_manager.broadcast` ✓
- `frontend/components/dashboard/SimpleBarChart.tsx` — exists ✓
- `frontend/components/dashboard/FrequencyTrendsCard.tsx` — exists ✓
- `frontend/components/dashboard/OverviewTab.tsx` — imports FrequencyTrendsCard ✓
- All 9 backend tests pass ✓
- TypeScript: 0 errors ✓
- Commits f69cfc9, d6e9d63, b573ab8 exist ✓
