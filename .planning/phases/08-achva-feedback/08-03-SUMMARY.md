---
phase: 8
plan: "08-03"
subsystem: frontend/pdf-export
tags: [pdf, jspdf, watermark, base64, tdd]
dependency_graph:
  requires: []
  provides: [exportReport.returnBase64, pdf-footer-watermark]
  affects: [frontend/lib/exportReport.ts, D-04-ContactModal]
tech_stack:
  added: []
  patterns: [jsPDF per-page loop, conditional return base64 vs download]
key_files:
  created:
    - frontend/__tests__/exportReport.test.ts
  modified:
    - frontend/lib/exportReport.ts
decisions:
  - "Footer watermark placed at pageHeight - 8mm centered, font-size 8 gray text"
  - "returnBase64 uses doc.output('datauristring') — no save() call when true"
  - "Locale switch: options.locale === 'he' → Hebrew string, otherwise EN"
metrics:
  duration: "~2 minutes"
  completed: "2026-04-18"
  tasks_completed: 2
  files_changed: 2
---

# Phase 8 Plan 03: PDF Footer Watermark + returnBase64 Mode Summary

**One-liner:** Replaced diagonal INCLUSIFY watermark with locale-aware Achva footer on every PDF page; added `returnBase64` mode returning a data URI for ContactModal attachment (D-04).

## What Was Built

- `frontend/lib/exportReport.ts` — Extended `ExportOptions` with `returnBase64?: boolean`; changed return type to `Promise<string | void>`; removed diagonal 45° watermark loop; added per-page footer loop writing locale-aware text at `pageHeight - 8` centered in gray 8pt helvetica; conditional `doc.output('datauristring')` return vs `doc.save()`.
- `frontend/__tests__/exportReport.test.ts` — 8 Jest tests (TDD RED → GREEN) covering: data URI return value, void return, save/no-save spy, EN footer text, HE footer text, no diagonal angle-45 call, output('datauristring') invocation.

## TDD Gate Compliance

- RED commit: `9d111db` — `test(08-03): add failing tests for exportReport base64 mode + footer watermark` (5 of 8 tests failed)
- GREEN commit: `3aecd4d` — `feat(08-03): replace diagonal watermark with locale footer + add returnBase64 mode (D-03)` (all 8 tests pass)

## Tasks Completed

| # | Name | Commit | Status |
|---|------|--------|--------|
| 1 | Create exportReport test file (RED) | 9d111db | Done |
| 2 | Replace diagonal watermark + add returnBase64 (GREEN) | 3aecd4d | Done |

## Deviations from Plan

None — plan executed exactly as written. The test file had 8 tests (plan specified 7+); the extra test (`doc.output called with datauristring`) was added to match test 3/4's spy-verification pattern for completeness.

## Known Stubs

None — both EN and HE watermark strings are hardcoded locale-switched values, not stubs.

## Threat Flags

None — PDF generation is entirely client-side per threat model. No new network surface introduced.

## Self-Check: PASSED

- `frontend/lib/exportReport.ts` — exists, contains `returnBase64`, `datauristring`, `pageHeight - 8`, `Achva LGBTQ+ Studential Organization`, `ארגון אחווה להט״ב הסטודנטיאלי`
- `frontend/__tests__/exportReport.test.ts` — exists, 8 tests GREEN
- Commit `9d111db` — exists (RED gate)
- Commit `3aecd4d` — exists (GREEN gate)
- TypeScript clean: `npx tsc --noEmit` exits 0
- No diagonal angle-45 remaining in exportReport.ts
