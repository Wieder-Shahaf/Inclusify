# Roadmap: Inclusify

## Milestones

- ✅ **v1.0 Full Platform** — Phases 1–7 (shipped 2026-04-12) → [archive](.planning/milestones/v1.0-ROADMAP.md)
- 🔄 **v1.1 Achva Feedback** — Phase 8 (in progress)

## Phases

<details>
<summary>✅ v1.0 Full Platform (Phases 1–7) — SHIPPED 2026-04-12</summary>

- [x] Phase 1: Infrastructure Foundation (3/3 plans) — completed 2026-03-09
- [x] Phase 2: Core Services (3/3 plans) — completed 2026-03-09
- [x] Phase 3: LLM Integration (4/4 plans) — completed 2026-03-09
- [x] Phase 4: Frontend Integration (3/3 plans) — completed 2026-03-09
- [x] Phase 5: Production Deployment (3/3 plans) — completed 2026-04-12
- [x] Phase 5.1: Azure Infrastructure (1/1 plan) — completed 2026-03-10
- [x] Phase 5.2: Model Migration (2/2 plans) — completed 2026-03-10
- [x] Phase 5.3: Auth Frontend (4/4 plans) — completed 2026-03-18
- [x] Phase 5.4: LoRA Retraining (4/4 plans) — completed 2026-03-13
- [x] Phase 5.4.1: Dataset Synthesis (4/4 plans) — completed 2026-04-12
- [x] Phase 5.5: Backend OAuth (2/2 plans) — completed 2026-03-18
- [x] Phase 6: Admin & Analytics (2/2 plans) — completed 2026-03-11
- [x] Phase 7: Production Hardening (2/2 plans) — completed 2026-03-11

**Total:** 13 phases, 37 plans, all complete

</details>

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Infrastructure Foundation | v1.0 | 3/3 | Complete | 2026-03-09 |
| 2. Core Services | v1.0 | 3/3 | Complete | 2026-03-09 |
| 3. LLM Integration | v1.0 | 4/4 | Complete | 2026-03-09 |
| 4. Frontend Integration | v1.0 | 3/3 | Complete | 2026-03-09 |
| 5. Production Deployment | v1.0 | 3/3 | Complete | 2026-04-12 |
| 5.1. Azure Infrastructure | v1.0 | 1/1 | Complete | 2026-03-10 |
| 5.2. Model Migration | v1.0 | 2/2 | Complete | 2026-03-10 |
| 5.3. Auth Frontend | v1.0 | 4/4 | Complete | 2026-03-18 |
| 5.4. LoRA Retraining | v1.0 | 4/4 | Complete | 2026-03-13 |
| 5.4.1. Dataset Synthesis | v1.0 | 4/4 | Complete | 2026-04-12 |
| 5.5. Backend OAuth | v1.0 | 2/2 | Complete | 2026-03-18 |
| 6. Admin & Analytics | v1.0 | 2/2 | Complete | 2026-03-11 |
| 7. Production Hardening | v1.0 | 2/2 | Complete | 2026-03-11 |
| 8. Achva Feedback (12/04) | v1.1 | 2/5 | In Progress | — |

---

### Phase 8: Achva Feedback (12/04)

**Goal:** Implement 5 stakeholder-requested improvements from Achva meeting on 2026-04-12 that require code changes (6 other items are already implemented and verified in code).

**Requirements:** D-01, D-02, D-03, D-04, D-05

**Scope (5 code-change items — 6 verify-only items already in code):**
- D-01: Profile completion popup requires all 3 fields (full_name, institution, profession)
- D-02: LLM-down fallback banner in analyze results view + glossary link
- D-03: PDF footer watermark (locale-aware) + base64 return mode for exportReport
- D-04: Contact Us modal in navbar + backend smtplib endpoint with optional PDF attachment
- D-05: Admin label frequency trends bar chart + top-5 phrases + WebSocket auto-refresh

**Verify-only (already implemented in code):**
- Loading text, score label, rule-based drop, inclusive_sentence field, admin user filters

**Depends on:** Phase 7 (complete)

**Plans:** 5 plans

Plans:
- [ ] 08-01-PLAN.md — D-01: Profile popup required fields fix + tests + i18n
- [ ] 08-02-PLAN.md — D-02: LLM-down banner wiring in analyze results + i18n
- [ ] 08-03-PLAN.md — D-03: PDF footer watermark + returnBase64 mode + tests
- [ ] 08-04-PLAN.md — D-04: Contact Us modal + smtplib endpoint + Navbar integration + tests
- [ ] 08-05-PLAN.md — D-05: Admin frequency trends SQL + HTTP + WebSocket + bar chart UI + tests

---

*Created: 2026-03-08 | v1.0 shipped: 2026-04-12 | Phase 8 planned: 2026-04-18*
