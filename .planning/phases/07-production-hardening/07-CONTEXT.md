# Phase 7: Production Hardening - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement privacy enforcement and accessibility compliance for final presentation. This phase delivers:
- Private mode toggle UI on analyze page
- Database constraint enforcing no text storage when private mode enabled
- WCAG 2.1 AA compliance for all public pages
- Keyboard navigation with proper focus management

</domain>

<decisions>
## Implementation Decisions

### Private Mode UI
- Toggle appears above file upload (before user submits document)
- Default state: OFF (storage enabled by default, user opts-in to privacy)
- Tooltip on toggle explains what private mode means (short explanation on hover/focus)
- Subtle lock badge/icon on results page when private mode is ON (confirms no storage)

### Privacy Enforcement
- CHECK constraint at DB level: text_storage_ref must be NULL when private_mode=TRUE
- Never store anything for private docs — no DB records created at all
- Analysis runs completely in-memory, returns results to frontend, nothing persisted
- No document, analysis_run, or findings records created for private mode documents

### Accessibility Scope
- All public pages covered: Landing, Upload/Analyze, Results, Glossary
- Admin dashboard NOT in scope for this phase
- Automated testing with axe-core or Lighthouse CI
- Screen reader announces key state changes: upload complete, analysis done, errors
- Severity badge colors must meet WCAG AA contrast ratio (4.5:1)

### Keyboard Navigation
- No skip link (app navigation is minimal enough)
- Visible outline ring on focused elements (clear focus indicator)
- RTL navigation: arrow key direction flips in Hebrew mode (Right=next, Left=previous)
- Results page: Arrow keys navigate between issues for keyboard users

### Claude's Discretion
- Exact tooltip wording for private mode
- Lock badge/icon design (size, position on results page)
- Focus ring color and width
- Screen reader announcement phrasing
- Specific axe-core rule configuration

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `db/schema.sql`: documents.private_mode BOOLEAN already exists, needs CHECK constraint
- `db/schema.sql`: documents.text_storage_ref field exists, will be constrained
- `db/schema.sql`: organizations.default_private_mode exists (not used, default is OFF)
- `frontend/app/[locale]/analyze/page.tsx`: File upload flow exists, add toggle above
- `frontend/components/ui/`: shadcn-style components available for toggle
- Existing aria attributes scattered across components (partial implementation)

### Established Patterns
- i18n: `useTranslations()` hook with messages in `frontend/messages/{locale}.json`
- RTL: `dir={isHebrew ? 'rtl' : 'ltr'}` on containers
- Backend: FastAPI routers with Pydantic models
- DB: asyncpg with repository pattern

### Integration Points
- `frontend/app/[locale]/analyze/page.tsx`: Add private mode toggle above upload
- `backend/app/modules/analysis/router.py`: Skip DB storage when private_mode=true
- `db/schema.sql`: Add CHECK constraint to documents table
- All public page components: Add aria labels, focus management

</code_context>

<specifics>
## Specific Ideas

- Private mode toggle should feel like a simple on/off switch, not a complex form
- Lock icon is familiar visual language for privacy/security
- Arrow key navigation for issues mirrors how users browse lists (familiar pattern)
- Contrast fixes should be done once properly, not via high contrast mode toggle

</specifics>

<deferred>
## Deferred Ideas

- Admin dashboard accessibility — Phase 7 focuses on public pages
- High contrast mode toggle — meet AA contrast instead of optional mode
- Skip link — app navigation is minimal enough without it
- Per-user default private mode setting — organization default is sufficient

</deferred>

---

*Phase: 07-production-hardening*
*Context gathered: 2026-03-11*
