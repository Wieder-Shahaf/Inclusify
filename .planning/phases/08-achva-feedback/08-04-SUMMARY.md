---
phase: 8
plan: "08-04"
subsystem: backend/contact + frontend/modal
tags: [contact-form, smtp, modal, radix-dialog, tdd, email, pdf-attachment]
dependency_graph:
  requires: [08-03/exportReport.returnBase64]
  provides: [POST /api/v1/contact, ContactModal, Navbar.contactButton]
  affects:
    - backend/app/modules/contact/router.py
    - backend/app/main.py
    - frontend/components/ContactModal.tsx
    - frontend/lib/api/contact.ts
    - frontend/components/Navbar.tsx
    - frontend/app/[locale]/analyze/page.tsx
tech_stack:
  added: [smtplib, email.mime.multipart]
  patterns: [multipart-form-post, base64-to-blob, radix-dialog-modal, tdd-red-green]
key_files:
  created:
    - backend/app/modules/contact/__init__.py
    - backend/app/modules/contact/router.py
    - backend/tests/test_contact.py
    - frontend/lib/api/contact.ts
    - frontend/components/ContactModal.tsx
  modified:
    - backend/app/main.py
    - backend/app/db/models.py
    - frontend/components/Navbar.tsx
    - frontend/app/[locale]/analyze/page.tsx
    - frontend/messages/en.json
    - frontend/messages/he.json
decisions:
  - "Recipients always queried from DB WHERE role='site_admin'; POST body sender_email never used for routing"
  - "5 MB PDF cap enforced at MAX_PDF_BYTES before SMTP path; 413 returned on excess"
  - "STARTTLS on port 587 (Gmail App Password required); SMTP_USER/SMTP_PASSWORD from env vars only"
  - "AnalysisData defined locally in ContactModal.tsx (not re-exported from exportReport.ts)"
  - "models.py: str | None changed to Optional[str] for Python 3.9 SQLAlchemy compatibility"
  - "ContactModal placed before closing </header> in Navbar (no analysis prop — guest context)"
metrics:
  duration: "~20 minutes"
  completed: "2026-04-18"
  tasks_completed: 3
  files_changed: 11
---

# Phase 8 Plan 04: Contact Us Modal + Backend Email Endpoint Summary

**One-liner:** Replaced mailto shortcut with in-app ContactModal backed by smtplib FastAPI endpoint; recipients always pulled from DB site_admin list; optional PDF analysis attachment via base64→Blob pipeline.

## What Was Built

- `backend/app/modules/contact/router.py` — FastAPI multipart POST endpoint with DB recipient lookup, 5 MB PDF cap, STARTTLS SMTP send, no auth required.
- `backend/app/modules/contact/__init__.py` — Module marker.
- `backend/app/main.py` — Contact router registered at `/api/v1/contact`.
- `backend/tests/test_contact.py` — 7 integration tests (TDD RED → GREEN): 422 on missing fields, 500 on no admins, full send to all admins, PDF attachment in email, 413 on oversized PDF, recipients from DB not POST body.
- `frontend/lib/api/contact.ts` — Plain fetch multipart POST (no auth); `sendContactMessage()` exported.
- `frontend/components/ContactModal.tsx` — Radix Dialog + zod + react-hook-form + sonner; prefills sender info for authenticated users; attachment indicator when analysis present; PDF base64→Blob via atob.
- `frontend/components/Navbar.tsx` — Contact Us button (min-h-11 WCAG 44px, aria-haspopup="dialog") triggering ContactModal without analysis prop.
- `frontend/app/[locale]/analyze/page.tsx` — handleContactUs and mailto: removed; ContactModal wired with analysis prop on results view.
- `frontend/messages/en.json` + `frontend/messages/he.json` — Contact i18n keys added.

## TDD Gate Compliance

- RED commit: `1fa3f8c` — `test(08-04): add failing tests for POST /api/v1/contact endpoint (D-04)` (7 tests failed with 404)
- GREEN commit: `f9c8a73` — `feat(08-04): add POST /api/v1/contact smtplib endpoint + tests (D-04)` (all 7 tests pass)

## Tasks Completed

| # | Name | Commit | Status |
|---|------|--------|--------|
| 1 | Create backend contact module + tests | 1fa3f8c (RED), f9c8a73 (GREEN) | Done |
| 2 | Create ContactModal + API client + i18n keys | f9e5527 | Done |
| 3 | Wire ContactModal into Navbar + replace mailto | 1f5d593 | Done |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fix Python 3.9 incompatibility in backend/app/db/models.py**
- **Found during:** Task 1 RED phase — `pytest tests/test_contact.py` failed with `TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'`
- **Issue:** `Mapped[str | None]` union syntax requires Python 3.10+; system Python is 3.9.6. SQLAlchemy also cannot resolve `str | None` at runtime even with `from __future__ import annotations`.
- **Fix:** Added `from __future__ import annotations` and changed `Mapped[str | None]` → `Mapped[Optional[str]]` with `Optional` imported from `typing`.
- **Files modified:** `backend/app/db/models.py`
- **Commit:** `1fa3f8c`
- **Impact:** Pre-existing issue that was blocking all backend tests. Fix unblocked RED phase and confirmed all 7 tests were correctly failing (404 rather than import error).

**2. [Rule 2 - Missing functionality] AnalysisData not exported from exportReport.ts**
- **Found during:** Task 2 — plan said to import `AnalysisData` from `@/lib/exportReport` but it's only a local interface there.
- **Fix:** Defined a compatible `AnalysisData` interface inline in `ContactModal.tsx` with `export` so downstream consumers can import it if needed. Shape matches both exportReport.ts and analyze/page.tsx definitions.
- **Files modified:** `frontend/components/ContactModal.tsx`

## Known Stubs

None — all functionality is implemented. SMTP credentials (SMTP_USER, SMTP_PASSWORD) must be configured via environment variables before emails will actually send; this is intentional per user_setup spec.

## Threat Flags

None — all threats from the plan's threat model were mitigated as designed:
- T-08-04-01: SMTP credentials from env only, 500 on missing (no credential leakage)
- T-08-04-02: 5 MB cap enforced before SMTP path
- T-08-04-03: Recipients from DB only, tested by test_recipients_from_db_not_user_input
- T-08-04-04: FastAPI Form() min/max_length validation
- T-08-04-05 / T-08-04-06 / T-08-04-07: Accepted per plan

## Self-Check: PASSED

- `backend/app/modules/contact/__init__.py` — exists
- `backend/app/modules/contact/router.py` — exists, contains smtplib, site_admin query, MAX_PDF_BYTES, starttls
- `backend/app/main.py` — contains `/api/v1/contact` route registration
- `backend/tests/test_contact.py` — exists, 7 tests GREEN
- `frontend/lib/api/contact.ts` — exists, sendContactMessage exported, no fetchWithAuth
- `frontend/components/ContactModal.tsx` — exists, Radix Dialog, returnBase64, atob, attachReport
- `frontend/components/Navbar.tsx` — ContactModal imported, contactOpen state, aria-haspopup="dialog"
- `frontend/app/[locale]/analyze/page.tsx` — no handleContactUs, no mailto:, ContactModal with analysis prop
- `frontend/messages/en.json` — contact.button = "Contact Us"
- `frontend/messages/he.json` — contact.button = "צרו קשר"
- TypeScript: `npx tsc --noEmit` exits 0 (no errors)
- Commits: 1fa3f8c, f9c8a73, f9e5527, 1f5d593 all exist
