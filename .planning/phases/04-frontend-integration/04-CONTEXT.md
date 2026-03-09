# Phase 4: Frontend Integration - Context

**Gathered:** 2026-03-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Frontend displays real analysis results from the production backend. This phase delivers:
- Wiring frontend API client to real backend (remove demo mode)
- Processing UX with real API calls
- Error handling for backend failures
- Results display with real analysis data
- Hebrew and English end-to-end support

</domain>

<decisions>
## Implementation Decisions

### API Connection Strategy
- Demo mode toggle: Environment variable `NEXT_PUBLIC_USE_DEMO_MODE=true/false`. Simple, works in dev and prod.
- Authentication: No auth headers for Phase 4. Analysis endpoint is public. Add auth later.
- Backend URL: Use existing `NEXT_PUBLIC_API_URL` env var. Already implemented in client.ts.
- Health check: Check backend health on page load. Show non-blocking warning banner if backend unreachable ("Analysis service unavailable"). User can still browse.

### Loading & Processing UX
- Processing animation: Phase-based progress showing stages: "Uploading file..." → "Extracting text..." → "Analyzing content...". Indeterminate per stage. Matches Phase 2 decision.
- Long wait handling: After 15 seconds, show extended wait message: "Analysis taking longer than usual..." No timeout.
- Cancel support: No cancel button. User waits or refreshes page.
- Navigation state: No state preservation. User returns to upload page if they navigate away. Simple, avoids stale state.

### Error Handling & Feedback
- API errors: User-friendly messages with action. "Unable to analyze document. Please try again." with return-to-upload behavior. Hide technical details.
- vLLM fallback indicator: Silent fallback, show small indicator. Results page shows badge: "Basic analysis mode" when analysis_mode is 'rules_only'.
- PDF-specific errors: Specific error messages matching Phase 2 backend responses. "This PDF is password-protected" or "File appears corrupted".
- Retry behavior: Start over only. Error returns to upload page. User re-selects file.

### Results Display
- Detection source: No indicator per issue. Results look the same regardless of LLM vs rule detection. Cleaner UI.
- Severity display: Colored badges with labels. Use existing SeverityBadge component. Green/yellow/orange/red for outdated/biased/offensive/incorrect.
- Inclusivity score: Severity-weighted score. Offensive issues reduce score more than outdated.
- Text highlighting: Prefer exact character positions from backend, fall back to phrase search. Already implemented in client.ts.

### Claude's Discretion
- Exact health check polling interval
- Warning banner styling
- Processing stage timing (when to transition between stages)
- Score weighting formula (how much each severity reduces score)
- Error message exact wording

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/lib/api/client.ts`: API client with `analyzeText()`, `uploadFile()`, `healthCheck()`. Type transformations ready. Uses `NEXT_PUBLIC_API_URL`.
- `frontend/components/ProcessingAnimation.tsx`: Multi-step processing animation with translations. Ready to wire to real API states.
- `frontend/components/AnalysisSummary.tsx`: Summary card with score, counts, recommendations.
- `frontend/components/SeverityBadge.tsx`: Colored severity badges already implemented.
- `frontend/components/IssueTooltip.tsx`: Hover tooltips for highlighted issues.
- `frontend/components/AnnotationSidePanel.tsx`: Slide-out panel for issue details.

### Established Patterns
- i18n: next-intl with `useTranslations()` hook. All user-facing strings from translation files.
- RTL handling: `dir={isHebrew ? 'rtl' : 'ltr'}` on text containers.
- Animation: Framer Motion `AnimatePresence` for state transitions.
- State management: React useState with callback pattern. No global store.
- View states: `'upload' | 'processing' | 'results'` pattern in analyze page.

### Integration Points
- `frontend/app/[locale]/analyze/page.tsx`: Main integration point. Replace `getSampleText()` and `analyzeDemoText()` with real API calls.
- `frontend/lib/utils/demoData.ts`: Demo data utilities to be bypassed via env var.
- `frontend/components/PaperUpload.tsx`: File selection triggers processing. No changes needed.
- Environment files: Add `NEXT_PUBLIC_USE_DEMO_MODE` to `.env.local` and `.env.production`.

</code_context>

<specifics>
## Specific Ideas

- Health check warning should be non-blocking — user can still explore UI
- Phase-based progress matches the actual API flow (upload → extract → analyze)
- "Basic analysis mode" badge only shown when LLM was unavailable (analysis_mode === 'rules_only')
- Severity weighting: offensive > incorrect > biased > outdated in score penalty

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-frontend-integration*
*Context gathered: 2026-03-09*
