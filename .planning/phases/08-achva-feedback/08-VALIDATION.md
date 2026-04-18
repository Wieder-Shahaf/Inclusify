---
phase: 8
slug: achva-feedback
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-18
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | jest (frontend), pytest (backend) |
| **Config file** | `frontend/jest.config.js` |
| **Quick run command** | `cd frontend && npm test -- --testPathPattern=<changed-file>` |
| **Full suite command** | `cd frontend && npm test && cd ../backend && pytest` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npm test -- --testPathPattern=<changed-file>`
- **After every plan wave:** Run `cd frontend && npm test && cd ../backend && pytest`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 8-D01-01 | D-01 | 1 | D-01 | — | Popup only dismissed when all 3 fields present | unit | `npm test -- --testPathPattern=ProfileSetupModal` | ❌ Wave 0 | ⬜ pending |
| 8-D01-02 | D-01 | 1 | D-01 | — | Zod schema rejects empty institution/profession | unit | `npm test -- --testPathPattern=ProfileSetupModal` | ❌ Wave 0 | ⬜ pending |
| 8-D02-01 | D-02 | 1 | D-02 | — | Banner renders when analysisMode=rules_only | unit | `npm test -- --testPathPattern=analyze` | ❌ Wave 0 | ⬜ pending |
| 8-D03-01 | D-03 | 1 | D-03 | — | exportReport returns base64 string when returnBase64=true | unit | `npm test -- --testPathPattern=exportReport` | ❌ Wave 0 | ⬜ pending |
| 8-D04-01 | D-04 | 2 | D-04 | T-SMTP | POST /api/v1/contact returns 200 with valid form data | integration | `cd backend && pytest tests/test_contact.py -x` | ❌ Wave 0 | ⬜ pending |
| 8-D05-01 | D-05 | 2 | D-05 | T-WS | get_label_frequency_trends returns expected shape | unit | `cd backend && pytest tests/test_admin_queries.py::test_frequency_trends -x` | ❌ Wave 0 | ⬜ pending |
| 8-D05-02 | D-05 | 2 | D-05 | T-WS-AUTH | WS closes with 4001 when JWT missing/invalid | unit | `cd backend && pytest tests/test_admin_ws.py -x` | ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/__tests__/ProfileSetupModal.test.tsx` — stubs for D-01
- [ ] `frontend/__tests__/analyze.test.tsx` — stub for D-02 banner render
- [ ] `frontend/__tests__/exportReport.test.ts` — stubs for D-03
- [ ] `backend/tests/test_contact.py` — stubs for D-04
- [ ] `backend/tests/test_admin_queries.py` — stub for D-05 query shape
- [ ] `backend/tests/test_admin_ws.py` — stub for D-05 WebSocket auth

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| PDF watermark appears on every page | D-03 | jsPDF canvas rendering not testable in jsdom | Export a multi-page PDF and visually confirm footer on all pages |
| Contact email delivers to site_admin inboxes | D-04 | SMTP integration with external mail server | Send test contact form in staging; verify delivery to `wieder.shahaf@gmail.com` |
| Admin bar chart renders label categories | D-05 | Chart rendering requires browser | Open admin dashboard and confirm bars appear for each category |
| Admin top-5 dropdown expands correctly | D-05 | DOM interaction | Click category bar dropdown and verify top phrases display |
| WebSocket auto-refresh fires on new analysis | D-05 | Requires live analysis pipeline | Submit analysis as user; verify admin dashboard updates without page reload |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
