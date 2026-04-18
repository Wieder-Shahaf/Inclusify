# Phase 8: Achva Feedback - Context

**Gathered:** 2026-04-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement 11 stakeholder-requested improvements from the Achva meeting on 2026-04-12. Covers UX polish, LLM pipeline cleanup, admin analytics enhancements, PDF export watermark, and a new "Contact us" feature. Scope is fixed — clarifies HOW to implement what was agreed, not new capabilities.

</domain>

<decisions>
## Implementation Decisions

### Already Implemented (confirmed in codebase — planner should verify, not re-implement)
- **D-already-1:** Loading text — ProcessingAnimation already has stage-based translations; update i18n strings to "Checking for non-inclusive writing..." (EN) and Hebrew equivalent in `frontend/messages/en.json` + `frontend/messages/he.json`.
- **D-already-2:** Score label — `AnalysisSummary.tsx` `defaultTranslations.score` already reads `'LGBTQ+ inclusivity score.'` ✓
- **D-already-3:** Drop rule-based detection — `hybrid_detector.py` is already LLM-only; `analysis_mode='rules_only'` is returned when LLM is unavailable ✓
- **D-already-4:** `inclusive_sentence` field — `Issue` model and `llm_client.py` already return `inclusive_sentence` in the LLM response ✓
- **D-already-5:** Admin user table filters — `/api/v1/admin/users` already accepts `institution` and `min_analyses` query params; `UsersTab` frontend already has filter UI ✓

### Profile Completion Popup (D-01)
- **D-01a:** Show popup **every session** until profile is complete. Use `sessionStorage` (current implementation) — resets per browser tab/session. Do NOT switch to localStorage.
- **D-01b:** Popup disappears only when **all three fields** are set: `full_name`, `institution`, `profession`. Current logic only checks `full_name` — update `ProfileSetupModal.tsx` to check `!user.full_name || !user.institution || !user.profession`.
- **D-01c:** All three fields (`full_name`, `institution`, `profession`) must be required in the form schema (currently `institution` and `profession` are optional). Update Zod schema to make them required.
- **D-01d:** `ProfileSetupModal` is already built (untracked file) — wire it into the authenticated layout so it mounts on login.

### LLM-Down Fallback (D-02)
- **D-02a:** When `analysis_mode === 'rules_only'` in the analysis response, show `HealthWarningBanner` on the results/analyze page.
- **D-02b:** Banner message (EN): `"Analysis service is temporarily unavailable. Browse the glossary for guidance."`
- **D-02c:** Banner links to the existing `/[locale]/glossary` route (already exists at `frontend/app/[locale]/glossary/page.tsx`).
- **D-02d:** Banner uses `variant='error'` (amber). `linkHref` = `/[locale]/glossary`, `linkText` = `"Browse glossary"` (or translated equivalent).
- **D-02e:** Add i18n keys for the banner message and link text to `en.json` / `he.json`.

### PDF Report Watermark (D-03)
- **D-03a:** Add a footer watermark to every page of exported PDFs in `frontend/lib/exportReport.ts`.
- **D-03b:** Watermark text is **locale-driven**:
  - EN: `"Achva LGBTQ+ Studential Organization"`
  - HE: `"ארגון אחווה להט״ב הסטודנטיאלי"`
- **D-03c:** Position: bottom footer on **each page** (not diagonal, not first page only).
- **D-03d:** Style: small gray text, centered, near page bottom. Match the existing footer area style in `exportReport.ts`.

### Contact Us Feature (D-04)
- **D-04a:** "Contact us" button lives in the **navigation bar** (always visible, all pages).
- **D-04b:** Clicking opens a **modal** (not a new page) with:
  - Subject field (free text)
  - Message field (free text textarea)
  - Auto-prefilled read-only fields: user name, email, institution — pulled from `AuthContext` if logged in; empty if guest.
- **D-04c:** Backend: new router at `POST /api/v1/contact`. Implementation:
  - Uses Python `smtplib` (stdlib — no new deps).
  - SMTP config: Gmail + App Password via env vars (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`).
  - Recipient list: query `site_admin` users' emails from DB (existing `users` table with `role = 'site_admin'`).
  - Optional PDF attachment: if client sends a `file` part (multipart), attach it to the email.
- **D-04d:** Frontend: if analysis is complete when user opens the modal, call `exportReport()` in base64-return mode instead of auto-download, and include it as a file attachment in the POST body.
- **D-04e:** If no analysis has been run (user on landing/nav), send email without attachment — predefined template body from the message field only.
- **D-04f:** **Coordinate with Adan's branch** — PDF export feature is in progress on a separate branch. `exportReport.ts` needs a mode to return `base64` instead of triggering a browser download.

### Admin Frequency Trends (D-05)
- **D-05a:** Add a new section to the admin dashboard: label frequency bar chart + top-5 phrases per label.
- **D-05b:** Chart: **bar chart** where each bar = one category label (e.g., "Historical Pathologization", "Identity Invalidation"). Bar height = count of findings with that category in the selected time window.
- **D-05c:** Top-5 phrases: **dropdown per label** (expandable) listing the 5 most frequent `excerpt_redacted` values for that category. Data source: `findings.excerpt_redacted` grouped by `findings.category` — already in DB, no schema change needed.
- **D-05d:** Auto-refresh: **WebSocket push** from backend when a new analysis completes. Backend emits an event on the admin WebSocket channel; frontend re-fetches analytics data on receipt.
- **D-05e:** New SQL query needed in `backend/app/modules/admin/queries.py`: `get_label_frequency_trends(conn, days)` returning `[{category, count, top_phrases: [{phrase, count}]}]`.
- **D-05f:** WebSocket endpoint needed: `GET /api/v1/admin/ws` — admin-only, pushes `{event: "new_analysis"}` JSON message on each completed analysis run.

### Claude's Discretion
- Exact Hebrew translations for new i18n strings (LLM-down banner, profile popup, contact modal) — follow existing Hebrew message style in `he.json`.
- WebSocket library choice for D-05f — FastAPI supports native WebSockets; use `fastapi.websockets`.
- Contact modal UI component structure — follow existing modal patterns in the codebase (Radix Dialog, `ProfileSetupModal.tsx` as reference).
- Retry/error handling in the contact API endpoint — show toast on success/failure (follow existing `sonner` toast pattern).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Frontend — UI Components
- `frontend/components/ProcessingAnimation.tsx` — loading stage system; update i18n keys only
- `frontend/components/AnalysisSummary.tsx` — score label (already correct, verify only)
- `frontend/components/HealthWarningBanner.tsx` — LLM-down banner component (already built, wire up)
- `frontend/components/ProfileSetupModal.tsx` — profile popup (already built, update required fields + wiring)
- `frontend/lib/exportReport.ts` — PDF export; add watermark footer + base64-return mode

### Frontend — Auth & Context
- `frontend/contexts/AuthContext.tsx` — user object shape (full_name, institution, profession fields)
- `frontend/app/[locale]/layout.tsx` — authenticated layout; mount ProfileSetupModal here
- `frontend/components/auth/UserDropdown.tsx` — nav pattern reference for adding Contact button

### Frontend — i18n
- `frontend/messages/en.json` — add keys for LLM-down banner, contact modal, profile popup
- `frontend/messages/he.json` — Hebrew equivalents

### Backend — Analysis
- `backend/app/modules/analysis/router.py` — AnalysisResponse with `analysis_mode` field
- `backend/app/modules/analysis/hybrid_detector.py` — LLM-only pipeline, `analysis_mode='rules_only'` on LLM failure

### Backend — Admin
- `backend/app/modules/admin/router.py` — admin endpoints; add WebSocket endpoint here
- `backend/app/modules/admin/queries.py` — add `get_label_frequency_trends()` query
- `backend/app/modules/admin/schemas.py` — add response schema for trends

### Database
- `db/schema.sql` — `findings` table: `category`, `severity`, `excerpt_redacted` columns (no schema change needed for D-05)
- `backend/app/db/repository.py` — `insert_finding()` already saves `excerpt_redacted`

### Glossary
- `frontend/app/[locale]/glossary/page.tsx` — existing glossary page (LLM-down fallback links here)

### Profile Backend
- `backend/app/modules/profile/` — profile update endpoints (new untracked module)
- `db/migrations/001_add_user_profile_fields.sql` — migration for profile fields (untracked)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `HealthWarningBanner` — already supports `message`, `variant`, `linkHref`, `linkText` props; just wire it to `analysis_mode === 'rules_only'`
- `ProfileSetupModal` — built with Radix Dialog, Zod validation, react-hook-form; needs required field update + layout wiring
- `exportReport.ts` — full jsPDF pipeline exists; add footer text per page + add base64-return mode
- `sonner` toast — used in ProfileSetupModal; use same pattern in contact modal
- `AuthContext` — exposes `user.full_name`, `user.institution`, `user.profession`; use for contact modal prefill + popup condition

### Established Patterns
- Modals: Radix `Dialog` + Tailwind (see `ProfileSetupModal.tsx`)
- API client: async functions in `frontend/lib/api/` with `getToken()` from AuthContext
- Admin queries: raw asyncpg SQL in `queries.py`, FastAPI deps for auth guard
- i18n: add keys to both `en.json` and `he.json`; use `useTranslations()` in client components

### Integration Points
- Contact modal → navbar (`frontend/app/[locale]/layout.tsx` or `Navbar` component)
- ProfileSetupModal → authenticated layout (mount after auth check)
- LLM-down banner → analyze page results view (check `analysis_mode` from API response)
- WebSocket → admin dashboard page (connect on mount, disconnect on unmount)
- Label trends → admin dashboard analytics section (new card below existing KPIs)

</code_context>

<specifics>
## Specific Ideas

- Contact email recipient list: query `SELECT email FROM users WHERE role = 'site_admin'` — site_admin emails are `wieder.shahaf@gmail.com` and `shahaf200019@gmail.com` (seeded in DB)
- PDF footer watermark: use `doc.setFontSize(8)` + `doc.setTextColor(150, 150, 150)` + `doc.text(text, pageWidth/2, pageHeight - 8, {align: 'center'})` pattern in the existing jsPDF pipeline
- WebSocket: FastAPI native `from fastapi import WebSocket` — no additional libraries needed
- Profile popup: `const complete = !!(user.full_name && user.institution && user.profession)` — all three must be truthy

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 08-achva-feedback*
*Context gathered: 2026-04-18*
