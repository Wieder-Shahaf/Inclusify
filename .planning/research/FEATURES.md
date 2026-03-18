# Feature Landscape

**Project:** Inclusify - LGBTQ+ Inclusive Language Analyzer
**Researched:** 2026-03-08
**Confidence:** HIGH

## Executive Summary

Production NLP analysis tools in 2026 converge on core features users expect (table stakes), while differentiation comes from domain-specific intelligence, privacy controls, and workflow integration. For an academic-focused inclusive language analyzer, the feature landscape breaks down into:

1. **Table Stakes** - Features users expect from any professional text analysis tool
2. **Differentiators** - Features that create competitive advantage in the LGBTQ+ inclusive language niche
3. **Anti-Features** - Features to deliberately avoid that add complexity without value

---

## Table Stakes

Features users expect. Missing = product feels incomplete.

### Document Processing

| Feature | Complexity | Status |
|---------|------------|--------|
| PDF upload | Low | Implemented (PyMuPDF → Docling) |
| File size limits (10-500 MB) | Low | Industry standard |
| Supported formats (PDF, DOCX, TXT) | Medium | PDF only currently |
| Text extraction with layout preservation | Medium | Docling validated |
| Character/page count limits | Low | Prevent abuse |

### Text Analysis Core

| Feature | Complexity | Status |
|---------|------------|--------|
| Real-time analysis (< 5 seconds) | High | Rule-based fast, LLM TBD |
| Issue detection with positions | Low | Implemented |
| Severity grading | Low | Implemented (4 levels) |
| Issue categorization | Low | By severity, could add by type |
| Inline suggestions | Medium | Implemented, needs quality |
| Multi-language (HE/EN) | Medium | Frontend ready, backend TBD |

### User Management

| Feature | Complexity | Status |
|---------|------------|--------|
| Email/password authentication | Medium | DB schema ready |
| User profiles | Low | DB schema includes preferences |
| Password reset | Low | Standard pattern |
| Session management | Low | JWT/sessions |

### Organization/Multi-Tenancy

| Feature | Complexity | Status |
|---------|------------|--------|
| Organization accounts | Medium | DB schema ready |
| User-org relationships | Low | DB foreign keys |
| Basic RBAC (user/admin) | Medium | DB role field |
| Org-scoped data isolation | Medium | Critical for privacy |

### Analytics & Reporting

| Feature | Complexity | Status |
|---------|------------|--------|
| Analysis history | Low | DB tables ready |
| Usage metrics dashboard | Medium | Admin need |
| Document status tracking | Low | DB status field |
| Basic search/filtering | Medium | Standard CRUD |

### Infrastructure

| Feature | Complexity | Status |
|---------|------------|--------|
| Health check endpoint | Low | Implemented |
| CORS configuration | Low | Implemented |
| Rate limiting | Medium | Not implemented |
| Structured logging | Low | print() currently |

---

## Differentiators

Features that set the product apart.

### Domain-Specific Intelligence

| Feature | Value | Complexity |
|---------|-------|------------|
| Custom glossary management | Orgs define their own terms | High |
| Contextual analysis (LLM) | Catches nuanced bias | High |
| Academic terminology awareness | Research context | High |
| Hebrew-English bilingual | Rare in inclusive language tools | High |
| Explanation generation | *Why* is this problematic | Medium |
| Citation-aware parsing | Distinguish quotes vs author | High |

### Privacy & Ethics

| Feature | Value | Complexity |
|---------|-------|------------|
| Privacy-first architecture | No-retention option | Medium |
| Audit logs | Research ethics transparency | Medium |
| Compliance documentation | GDPR/IRB-ready | Low |

### Reporting & Export

| Feature | Value | Complexity |
|---------|-------|------------|
| Branded PDF reports | Professional, shareable | Medium |
| Export formats (PDF, DOCX, CSV) | Workflow flexibility | Medium |
| Before/after comparison | Show impact of changes | Medium |
| Annotation export | Import into other tools | Low |

### Quality & Feedback

| Feature | Value | Complexity |
|---------|-------|------------|
| False positive reporting | Feedback loop | Medium |
| Suggestion quality ratings | Thumbs up/down | Low |
| Model versioning/changelog | Track improvements | Low |

---

## Anti-Features

Features to explicitly NOT build (at least for v1).

| Anti-Feature | Why Avoid |
|--------------|-----------|
| Real-time collaboration (Google Docs-style) | Massive complexity, single-user sufficient |
| Video/audio analysis | Out of scope, text-only |
| Mobile native app | Responsive web sufficient |
| In-app model retraining | Complexity, security risk |
| Complex RBAC (org_admin, reviewer) | Overkill, user/admin sufficient |
| Payment processing | Academic project |
| Social features (profiles, following) | Not a social network |
| Gamification (badges, points) | Trivializes serious topic |
| AI training on user data | Privacy violation |
| Chrome extension / Word plugin | Integration complexity |
| Auto-correction without review | Dangerous for academic accuracy |
| Public rule marketplace | Moderation burden |

---

## Feature Dependencies

```
Authentication → User Profiles → Analysis History
Authentication → Organization Management → Org-Scoped Data
Organization Management → RBAC → Admin Dashboard
Document Upload → Text Extraction → Analysis Core
Analysis Core → Issue Detection → Suggestions
Analysis Core → Findings Storage → Analytics Dashboard
Private Mode → Data Retention Policies → Audit Logs
LLM Integration → Explanation Generation → Contextual Analysis
```

---

## MVP Recommendation

### Priority 1: Foundation (Blocking)

1. **Authentication & Org Management**
   - Email/password auth
   - Simple user/admin RBAC
   - Org-scoped data isolation
   - Rationale: Enables multi-tenant deployment

2. **LLM Integration**
   - vLLM deployment on Azure
   - Integrate fine-tuned model
   - Replace rule-based detection
   - Rationale: Core product value

### Priority 2: Admin (Required for Demo)

3. **Admin Dashboard**
   - User/org management UI
   - Usage metrics
   - Basic analytics
   - Rationale: Admins need visibility

### Priority 3: Output (Value Delivery)

4. **Export/Reporting**
   - PDF report generation
   - CSV/JSON export
   - Rationale: Makes results actionable

### Priority 4: Trust (Competitive Advantage)

5. **Privacy Controls**
   - Private mode enforcement
   - Data retention documentation
   - User-initiated deletion
   - Rationale: Ethical requirement

### Defer to v2

- Custom glossary management
- Batch document processing
- Webhooks / API SDK
- Collaboration features
- Advanced analytics
- Audit logs

---

## Complexity Estimates

| Level | Time | Examples |
|-------|------|----------|
| Low | < 1 week | User profiles, document status, health checks |
| Medium | 1-3 weeks | Admin dashboard, auth, PDF reports |
| High | 3-8 weeks | LLM integration, custom glossaries, contextual analysis |
| Very High | > 8 weeks | Real-time collaboration, NLQ on analytics |

---

## Sources

- Grammarly, Textio, Trinka (inclusive language tools)
- OpenAI, Google Cloud NLP, Azure Document Intelligence (NLP APIs)
- AWS Textract, Adobe Document Cloud (document processing)
- WorkOS, Clerk (multi-tenant SaaS patterns)
- Paperguide, Zotero (academic tools)

---

*Last updated: 2026-03-08*
