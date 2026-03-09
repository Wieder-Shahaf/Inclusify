# Phase 4: Frontend Integration - Research

**Researched:** 2026-03-09
**Domain:** Next.js 16 API integration with FastAPI backend
**Confidence:** HIGH

## Summary

Phase 4 integrates the existing Next.js frontend with the real FastAPI backend, replacing demo mode with live API calls. The frontend already has most infrastructure in place: `client.ts` API client with type transformations, `ProcessingAnimation.tsx` with phase-based progress, and complete i18n support via next-intl.

The primary work involves: (1) adding a demo mode toggle via environment variable, (2) wiring the analyze page to use real API calls instead of `getSampleText()`/`analyzeDemoText()`, (3) implementing error handling with user-friendly messages, and (4) adding health check with non-blocking warning banner.

**Primary recommendation:** Use `NEXT_PUBLIC_USE_DEMO_MODE` environment variable with a simple `if/else` branch at the top of the data flow. Keep the existing `ProcessingAnimation` timing-based approach but trigger completion callback from actual API response rather than fixed timer.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Demo mode toggle: Environment variable `NEXT_PUBLIC_USE_DEMO_MODE=true/false`. Simple, works in dev and prod.
- Authentication: No auth headers for Phase 4. Analysis endpoint is public. Add auth later.
- Backend URL: Use existing `NEXT_PUBLIC_API_URL` env var. Already implemented in client.ts.
- Health check: Check backend health on page load. Show non-blocking warning banner if backend unreachable ("Analysis service unavailable"). User can still browse.
- Processing animation: Phase-based progress showing stages: "Uploading file..." -> "Extracting text..." -> "Analyzing content...". Indeterminate per stage. Matches Phase 2 decision.
- Long wait handling: After 15 seconds, show extended wait message: "Analysis taking longer than usual..." No timeout.
- Cancel support: No cancel button. User waits or refreshes page.
- Navigation state: No state preservation. User returns to upload page if they navigate away. Simple, avoids stale state.
- API errors: User-friendly messages with action. "Unable to analyze document. Please try again." with return-to-upload behavior. Hide technical details.
- vLLM fallback indicator: Silent fallback, show small indicator. Results page shows badge: "Basic analysis mode" when analysis_mode is 'rules_only'.
- PDF-specific errors: Specific error messages matching Phase 2 backend responses. "This PDF is password-protected" or "File appears corrupted".
- Retry behavior: Start over only. Error returns to upload page. User re-selects file.
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

### Deferred Ideas (OUT OF SCOPE)
None - discussion stayed within phase scope

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FE-01 | Frontend wired to real backend API (remove demo mode) | client.ts already has `analyzeText()`, `uploadFile()`, `healthCheck()`. Need environment toggle and page wiring. |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | 16 (App Router) | Frontend framework | Already in use, full TypeScript support |
| next-intl | 4.6.0 | i18n (HE/EN) | Already configured with RTL support |
| Framer Motion | 12.x | Animations | Already used for transitions and loading states |
| React | 19.2.1 | UI library | Supports useTransition for async state |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| lucide-react | 0.561.0 | Icons | Already used throughout UI |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom fetch | SWR/React Query | Overkill for single API call per page - keep simple fetch |
| Global state (Zustand) | React useState | Single-page flow doesn't need global state |

**Installation:**
```bash
# No new packages needed - all dependencies exist
```

## Architecture Patterns

### Recommended Project Structure
```
frontend/
├── lib/
│   └── api/
│       └── client.ts        # API functions (exists)
├── components/
│   ├── ProcessingAnimation.tsx  # Phase-based progress (exists)
│   ├── AnalysisSummary.tsx      # Results display (exists)
│   └── HealthWarningBanner.tsx  # New: health check banner
├── app/
│   └── [locale]/
│       └── analyze/
│           └── page.tsx     # Wire real API (modify)
└── .env.local               # Add NEXT_PUBLIC_USE_DEMO_MODE
```

### Pattern 1: Environment-Based Demo Toggle
**What:** Use `NEXT_PUBLIC_USE_DEMO_MODE` to conditionally use demo or real data
**When to use:** At the top of data flow functions
**Example:**
```typescript
// Source: analyze/page.tsx
const USE_DEMO = process.env.NEXT_PUBLIC_USE_DEMO_MODE === 'true';

const handleFileSelect = useCallback(async (file: File) => {
  setFileName(file.name);
  setViewState('processing');

  if (USE_DEMO) {
    // Demo path: use existing timer-based animation
    // handleProcessingComplete will use getSampleText/analyzeDemoText
    return;
  }

  // Real path: actual API calls
  try {
    const uploadResult = await uploadFile(file);
    setStage('extracting');

    const analysisResult = await analyzeText(uploadResult.text, {
      language: locale as 'en' | 'he' | 'auto',
      privateMode: true,
    });

    setAnalysis(transformToAnalysisData(analysisResult, locale));
    setViewState('results');
  } catch (error) {
    handleApiError(error);
  }
}, [locale]);
```

### Pattern 2: Async Processing with Stage Updates
**What:** Update processing stage based on actual API call progress
**When to use:** During file upload and analysis flow
**Example:**
```typescript
// Modified ProcessingAnimation to accept external stage control
interface ProcessingAnimationProps {
  fileName: string;
  stage?: 'uploading' | 'parsing' | 'analyzing' | 'generating' | 'complete';
  onComplete?: () => void;
  translations?: Translations;
}

// In parent page:
const [processingStage, setProcessingStage] = useState<ProcessingStage>('uploading');

// During API calls:
setProcessingStage('uploading');
await uploadFile(file);
setProcessingStage('parsing');  // Docling extracts text
// ... response received
setProcessingStage('analyzing');
await analyzeText(text);
setProcessingStage('complete');
```

### Pattern 3: Health Check with Non-Blocking Banner
**What:** Check backend health on mount, show warning if unreachable
**When to use:** App initialization or page load
**Example:**
```typescript
// Source: analyze/page.tsx
const [backendHealthy, setBackendHealthy] = useState<boolean | null>(null);

useEffect(() => {
  const checkHealth = async () => {
    const healthy = await healthCheck();
    setBackendHealthy(healthy);
  };
  checkHealth();
  // Optional: poll every 30 seconds
  const interval = setInterval(checkHealth, 30000);
  return () => clearInterval(interval);
}, []);

// In JSX:
{backendHealthy === false && (
  <HealthWarningBanner message={t('serviceUnavailable')} />
)}
```

### Pattern 4: User-Friendly Error Handling
**What:** Map API errors to user-friendly messages
**When to use:** All API calls
**Example:**
```typescript
// Source: analyze/page.tsx
const handleApiError = (error: unknown) => {
  let message = t('errors.generic');

  if (error instanceof Error) {
    // Map specific backend error messages
    if (error.message.includes('password-protected')) {
      message = t('errors.passwordProtected');
    } else if (error.message.includes('corrupted')) {
      message = t('errors.corruptedFile');
    } else if (error.message.includes('50 pages')) {
      message = t('errors.tooManyPages');
    } else if (error.message.includes('50MB')) {
      message = t('errors.fileTooLarge');
    }
  }

  setErrorMessage(message);
  setViewState('upload'); // Return to upload page
};
```

### Anti-Patterns to Avoid
- **Mixing demo and real code paths:** Keep demo logic isolated with clear `if (USE_DEMO)` branching
- **Blocking UI on health check:** Health check should be async, never block page render
- **Exposing raw HTTP errors:** Always transform backend errors to user-friendly messages
- **Hardcoding API URLs:** Always use `NEXT_PUBLIC_API_URL` environment variable

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Response transformation | Manual field mapping | Existing `transformResponse()` in client.ts | Already handles severity mapping, annotation creation, position fallback |
| RTL text direction | Custom direction logic | `dir={isHebrew ? 'rtl' : 'ltr'}` pattern | Already established throughout codebase |
| Severity colors | New color system | Existing `SeverityBadge` component | Consistent with existing design |
| Processing animation | New loading component | Existing `ProcessingAnimation` | Just needs stage prop for real API integration |

**Key insight:** The frontend already has 90% of the integration code written. The work is primarily wiring existing components together and adding the demo mode toggle.

## Common Pitfalls

### Pitfall 1: CORS in Production
**What goes wrong:** Frontend on one domain cannot call backend on another domain
**Why it happens:** Browser security policy blocks cross-origin requests
**How to avoid:** Backend already has CORS configured for localhost:3000. For production, add production frontend domain to `allow_origins` in backend/app/main.py
**Warning signs:** Console shows "Access to fetch at ... has been blocked by CORS policy"

### Pitfall 2: NEXT_PUBLIC_ Variables Not Updating
**What goes wrong:** Environment variable changes don't take effect
**Why it happens:** NEXT_PUBLIC_ variables are baked into the JavaScript bundle at build time
**How to avoid:** Rebuild frontend after changing NEXT_PUBLIC_ variables; for runtime config, use API route pattern
**Warning signs:** Old value persists despite .env changes

### Pitfall 3: Auth Token Missing
**What goes wrong:** 401 Unauthorized from backend
**Why it happens:** Backend endpoints require authentication (current_active_user dependency)
**How to avoid:** Phase 4 decision: Analysis endpoint currently requires auth. Need to either: (a) add auth header from frontend, or (b) create public endpoint variant
**Warning signs:** 401 errors in network tab

### Pitfall 4: Processing Animation Timing Mismatch
**What goes wrong:** Animation shows "complete" before API actually returns
**Why it happens:** Current ProcessingAnimation uses fixed 6-second timer
**How to avoid:** For real API, pass stage prop from parent and update based on actual API progress
**Warning signs:** Results appear before animation completes, or animation stuck at partial progress

### Pitfall 5: Hebrew/RTL Text Not Displaying Correctly
**What goes wrong:** Text appears backwards or misaligned
**Why it happens:** Missing `dir="rtl"` attribute on containers
**How to avoid:** Always use `dir={isHebrew ? 'rtl' : 'ltr'}` on text containers; already implemented in analyze page
**Warning signs:** Hebrew text mixed with LTR punctuation/numbers looks scrambled

### Pitfall 6: Backend Response Missing analysis_mode
**What goes wrong:** Cannot show "Basic analysis mode" badge
**Why it happens:** Older backend response format may not include `analysis_mode` field
**How to avoid:** Check if field exists before displaying: `response.analysis_mode === 'rules_only'`
**Warning signs:** Undefined reference errors when trying to access analysis_mode

## Code Examples

Verified patterns from existing codebase:

### API Client (Existing)
```typescript
// Source: frontend/lib/api/client.ts
export async function analyzeText(
  text: string,
  options?: {
    language?: 'en' | 'he' | 'auto';
    privateMode?: boolean;
  }
): Promise<AnalysisResult> {
  const response = await fetch(`${API_BASE_URL}/api/v1/analysis/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      text,
      language: options?.language || 'auto',
      private_mode: options?.privateMode ?? true,
    }),
  });
  // ... transformation logic
}
```

### Processing Stage Control (New Pattern)
```typescript
// Modified ProcessingAnimation usage
<ProcessingAnimation
  fileName={fileName}
  stage={USE_DEMO ? undefined : processingStage}  // undefined = use internal timer
  onComplete={USE_DEMO ? handleProcessingComplete : undefined}
  translations={processingTranslations}
/>
```

### Health Warning Banner (New Component)
```typescript
// Source: components/HealthWarningBanner.tsx
'use client';

import { AlertTriangle } from 'lucide-react';
import { motion } from 'framer-motion';

interface Props {
  message: string;
}

export default function HealthWarningBanner({ message }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-amber-50 dark:bg-amber-900/20 border-b border-amber-200 dark:border-amber-800 px-4 py-2"
    >
      <div className="flex items-center gap-2 text-amber-700 dark:text-amber-400 text-sm">
        <AlertTriangle className="w-4 h-4" />
        <span>{message}</span>
      </div>
    </motion.div>
  );
}
```

### Score Calculation (Severity-Weighted)
```typescript
// Calculate inclusivity score with severity weighting
function calculateScore(counts: Record<Severity, number>, wordCount: number): number {
  // Weights: offensive > incorrect > biased > outdated (per CONTEXT.md)
  const weights = {
    outdated: 1,
    biased: 2,
    incorrect: 3,
    offensive: 4,
  };

  const totalWeightedIssues =
    counts.outdated * weights.outdated +
    counts.biased * weights.biased +
    counts.incorrect * weights.incorrect +
    counts.offensive * weights.offensive;

  // Score formula: penalize based on issue density
  const penalty = (totalWeightedIssues / wordCount) * 200;
  return Math.max(0, Math.round(100 - penalty));
}
```

### Extended Wait Message (New Pattern)
```typescript
// In ProcessingAnimation or analyze page
const [startTime] = useState(Date.now());
const [showExtendedWait, setShowExtendedWait] = useState(false);

useEffect(() => {
  const timer = setTimeout(() => {
    if (viewState === 'processing') {
      setShowExtendedWait(true);
    }
  }, 15000);
  return () => clearTimeout(timer);
}, [viewState]);

// In JSX:
{showExtendedWait && (
  <p className="text-sm text-slate-500 mt-2">
    {t('processing.takingLonger')}
  </p>
)}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `getSampleText()`/`analyzeDemoText()` | `uploadFile()`/`analyzeText()` from client.ts | This phase | Real analysis results |
| Fixed 6-second timer | API-driven stage progression | This phase | Accurate progress indication |
| No health check | Health check on page load | This phase | Better UX when backend down |

**Deprecated/outdated:**
- Demo mode should still work via environment toggle for development/testing

## Open Questions

1. **Authentication for Analysis Endpoint**
   - What we know: Backend currently requires `current_active_user` dependency
   - What's unclear: Should frontend send JWT, or should backend have public endpoint?
   - Recommendation: CONTEXT.md says "No auth headers for Phase 4. Analysis endpoint is public." - may need backend change to make endpoint public, or use existing JWT from Phase 2 auth

2. **Full Text vs Preview**
   - What we know: Upload response includes `text_preview` (first 500 chars) and `full_text_length`
   - What's unclear: Need to get full text for analysis - is there a separate endpoint?
   - Recommendation: Check if backend returns full text or just preview. May need backend modification to return full text for analysis.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | None installed (no jest/vitest/playwright) |
| Config file | None - see Wave 0 |
| Quick run command | N/A |
| Full suite command | N/A |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FE-01 | Frontend calls real API | e2e | `npm run test:e2e` | No - Wave 0 |
| FE-01 | Demo mode toggle works | unit | `npm run test` | No - Wave 0 |
| FE-01 | Error messages display | unit | `npm run test` | No - Wave 0 |
| FE-01 | Hebrew RTL works | e2e | `npm run test:e2e` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** Manual browser testing (no automated tests yet)
- **Per wave merge:** Manual E2E verification
- **Phase gate:** Full manual testing of upload -> results flow in both locales

### Wave 0 Gaps
- [ ] `frontend/vitest.config.ts` - test framework configuration
- [ ] `frontend/__tests__/api/client.test.ts` - API client tests
- [ ] `frontend/playwright.config.ts` - e2e test configuration (optional for this phase)
- [ ] Framework install: `npm install -D vitest @testing-library/react @vitejs/plugin-react jsdom` - if tests required

*(Note: Given project timeline, manual testing may be acceptable for Phase 4. Test infrastructure can be added in Phase 7)*

## Sources

### Primary (HIGH confidence)
- `frontend/lib/api/client.ts` - Existing API client with all functions
- `frontend/app/[locale]/analyze/page.tsx` - Current page implementation
- `frontend/components/ProcessingAnimation.tsx` - Current animation component
- `backend/app/main.py` - CORS configuration
- `backend/app/modules/analysis/router.py` - API contract
- `04-CONTEXT.md` - User decisions

### Secondary (MEDIUM confidence)
- [Next.js Environment Variables Guide](https://nextjs.org/docs/pages/guides/environment-variables) - NEXT_PUBLIC_ pattern
- [Next.js Error Handling](https://nextjs.org/docs/app/getting-started/error-handling) - Error.tsx patterns
- [FastAPI CORS Tutorial](https://fastapi.tiangolo.com/tutorial/cors/) - Production CORS setup
- [React useTransition](https://react.dev/reference/react/useTransition) - Async state handling

### Tertiary (LOW confidence)
- None - all findings verified with primary sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already in use, verified in package.json
- Architecture: HIGH - patterns derived from existing codebase
- Pitfalls: HIGH - based on known issues from PITFALLS.md and CORS documentation

**Research date:** 2026-03-09
**Valid until:** 2026-04-09 (stable patterns, no fast-moving dependencies)
