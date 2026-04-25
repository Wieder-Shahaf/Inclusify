# Milestones: Inclusify

---

## v1.0 — Full Platform

**Shipped:** 2026-04-12
**Phases:** 1–7 (13 phases including 5.1, 5.2, 5.3, 5.4, 5.4.1, 5.5)
**Plans:** 37 / Tasks: Complete
**Timeline:** 2025-12-12 → 2026-04-12 (122 days)
**LOC:** ~19,100 (TypeScript + Python)
**Commits:** 415

### Delivered

Production-deployed LGBTQ+ inclusive language analyzer: full Docker containerization, Azure Container Apps deployment, fine-tuned Qwen2.5-3B inference via vLLM (90% F1), hybrid detection engine, JWT + Google OAuth auth, WCAG 2.1 AA accessibility, admin dashboard with analytics, and GitHub Actions CI/CD.

### Key Accomplishments

1. **Azure infrastructure** — Container Apps with VNet integration, PostgreSQL Flexible Server, CI/CD via GitHub Actions
2. **Fine-tuned LLM** — Qwen2.5-3B + QLoRA adapter (r=8, dropout=0.2): 90.0% F1, 34.5 req/sec throughput
3. **Hybrid detection engine** — vLLM contextual analysis + 127-term rule-based fallback with span deduplication
4. **Full auth stack** — JWT email/password + Google OAuth (FastAPI Users 13.x), RBAC, guest mode
5. **Frontend wired to real API** — Complete upload → analysis → results flow, Hebrew RTL + English
6. **Admin dashboard** — Real analytics KPIs, user management, SWR-powered, RBAC-protected
7. **Accessibility** — WCAG 2.1 AA: LiveAnnouncer, RTL keyboard nav, compliant contrast ratios
8. **Private mode** — Per-document text storage enforcement via DB CHECK constraint

### Archive

- Roadmap: `.planning/milestones/v1.0-ROADMAP.md`
- Requirements: `.planning/milestones/v1.0-REQUIREMENTS.md`

---

## v1.1 — Achva Feedback

**Shipped:** 2026-04-18
**Phases:** 8 (1 phase)
**Plans:** 5 / Tasks: 8+
**Timeline:** 2026-04-18 (1 day sprint)
**LOC:** +3,252 / -276 (39 files changed)
**Commits:** 28

### Delivered

5 stakeholder-requested improvements from the Achva LGBTQ+ organization April 12 meeting: profile completion enforcement, LLM-down fallback banner, locale-aware PDF footer watermark, Contact Us modal with email delivery, and admin frequency trends dashboard with WebSocket auto-refresh.

### Key Accomplishments

1. **Profile completion enforcement** — popup requires all 3 fields (full_name + institution + profession) with session-scoped dismiss; prevent race condition on refreshProfile() re-render
2. **LLM-down banner** — fixed-position banner in analyze results when analysis_mode is rules_only; glossary link + Hebrew i18n
3. **PDF footer watermark** — locale-aware footer (EN: "Achva LGBTQ+ Studential Organization" / HE: "ארגון אחווה להט״ב הסטודנטיאלי") + returnBase64 mode for email attachments; diagonal watermark removed
4. **Contact Us modal** — Radix Dialog modal in Navbar; smtplib multipart backend with DB-queried admin recipients; optional PDF attachment; SMTP vars in docker-compose
5. **Admin frequency trends** — SQL + HTTP endpoint + FastAPI WebSocket auto-refresh; custom SVG SimpleBarChart (no D3); pulsing green dot connection indicator

### Known Deferred Items at Close

6 items acknowledged (see STATE.md Deferred Items): 1 UAT pending, 4 verification human_needed, 1 quick-task missing summary.

### Archive

- Roadmap: `.planning/milestones/v1.1-ROADMAP.md`

---
