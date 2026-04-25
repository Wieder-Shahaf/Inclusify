---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: complete
last_updated: "2026-04-25T09:57:06.605Z"
progress:
  total_phases: 14
  completed_phases: 14
  total_plans: 42
  completed_plans: 42
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-18)

**Core value:** Academics can identify and fix non-inclusive language in their work before publication
**Current focus:** v1.1 shipped — ready for July 8 final presentation. Next: /gsd-new-milestone for v2.0

## Milestone Complete

**v1.1 Achva Feedback** — shipped 2026-04-18

- 1 phase (Phase 8), 5 plans, all complete
- Profile completion enforcement, LLM-down banner, PDF watermark, Contact Us modal, admin WS bar chart
- 28 commits, 39 files, +3252/-276 LOC

Archives: `.planning/milestones/v1.1-ROADMAP.md` | `.planning/milestones/v1.0-ROADMAP.md`

## Accumulated Context

### Roadmap Evolution

- Phase 8 added: Achva Feedback (12/04) — 11 stakeholder-requested improvements from 2026-04-12 meeting

### Decisions

All decisions logged in PROJECT.md Key Decisions table.

- 08-01: ProfileSetupModal completion check requires all 3 fields (full_name AND institution AND profession)
- 08-01: dismiss() used in onSubmit success to prevent race condition on refreshProfile() re-render
- 08-01: he.json profile.setup.skip corrected to "דלג בינתיים" per UI-SPEC copywriting contract
- 08-02: Option B thin harness used for TDD test — PaperUpload two-step flow made full-page integration test impractical
- 08-02: HealthWarningBanner variant="error" for rules_only results banner per UI-SPEC
- 08-03: Footer watermark at pageHeight-8mm centered, gray 8pt; locale switch he → Hebrew string
- 08-03: returnBase64 uses doc.output('datauristring'); no doc.save() call when true
- 08-04: Recipients always queried from DB WHERE role='site_admin'; POST body sender_email never used for routing
- 08-04: AnalysisData defined locally in ContactModal.tsx (not re-exported from exportReport.ts)
- 08-04: models.py str | None → Optional[str] for Python 3.9 SQLAlchemy compatibility
- 08-05: WebSocket JWT auth via query param — Depends() injection does not work in FastAPI WS handlers
- 08-05: AdminWSManager as module-level singleton in admin/router.py; imported by analysis/router.py
- 08-05: Broadcast wrapped in try/except so WS failures never fail the analysis request
- 08-05: WS close code 4001 for missing/invalid token; 4003 for non-admin role
- 08-05: Custom SVG SimpleBarChart — no D3 dependency, follows existing SimpleLineChart pattern

### Pending Todos

None.

### Blockers/Concerns

None — ready for April 15 presentation.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260407-kps | Fix vLLM response parsing crash in llm_client.py | 2026-04-07 | aa049b7 | [260407-kps-fix-vllm-response-parsing-crash-in-llm-c](.planning/quick/260407-kps-fix-vllm-response-parsing-crash-in-llm-c/) |

## Deferred Items

Items acknowledged and deferred at milestone close on 2026-04-18:

| Category | Item | Status |
|----------|------|--------|
| uat_gap | Phase 08: 08-HUMAN-UAT.md — 1 pending scenario (D-05 WebSocket auto-refresh) | partial |
| verification | Phase 01: 01-VERIFICATION.md | human_needed |
| verification | Phase 03: 03-VERIFICATION.md | human_needed |
| verification | Phase 05.2: 05.2-01-VERIFICATION.md | gaps_found |
| verification | Phase 08: 08-VERIFICATION.md | human_needed |
| quick_task | 260407-kps-fix-vllm-response-parsing-crash-in-llm-c | missing summary |
