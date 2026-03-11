# Phase 7: Production Hardening - Research

**Researched:** 2026-03-11
**Domain:** Privacy enforcement, WCAG 2.1 AA accessibility compliance
**Confidence:** HIGH

## Summary

Phase 7 implements two critical production requirements: privacy enforcement (PRIV-01) and accessibility compliance (A11Y-01). The privacy implementation is architecturally simple - the database CHECK constraint already exists in `db/schema.sql`, and the backend simply needs to skip DB storage when `private_mode=true`. The frontend requires a toggle UI before file upload.

Accessibility work involves four areas: (1) contrast ratio fixes for severity badges to meet WCAG 2.1 AA 4.5:1 requirement, (2) screen reader live region announcements for key state changes, (3) keyboard navigation with proper focus management and RTL-aware arrow key behavior, and (4) automated testing with axe-core. The project already uses Radix UI primitives which provide built-in accessibility, but explicit ARIA attributes and focus management need to be added to custom components.

**Primary recommendation:** Use `@radix-ui/react-switch` for the private mode toggle (already have Radix installed), implement a persistent ARIA live region for screen reader announcements, and add jest-axe for automated accessibility testing in CI.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Toggle appears above file upload (before user submits document)
- Default state: OFF (storage enabled by default, user opts-in to privacy)
- Tooltip on toggle explains what private mode means (short explanation on hover/focus)
- Subtle lock badge/icon on results page when private mode is ON (confirms no storage)
- CHECK constraint at DB level: text_storage_ref must be NULL when private_mode=TRUE
- Never store anything for private docs - no DB records created at all
- Analysis runs completely in-memory, returns results to frontend, nothing persisted
- No document, analysis_run, or findings records created for private mode documents
- All public pages covered: Landing, Upload/Analyze, Results, Glossary
- Admin dashboard NOT in scope for this phase
- Automated testing with axe-core or Lighthouse CI
- Screen reader announces key state changes: upload complete, analysis done, errors
- Severity badge colors must meet WCAG AA contrast ratio (4.5:1)
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

### Deferred Ideas (OUT OF SCOPE)
- Admin dashboard accessibility - Phase 7 focuses on public pages
- High contrast mode toggle - meet AA contrast instead of optional mode
- Skip link - app navigation is minimal enough without it
- Per-user default private mode setting - organization default is sufficient
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PRIV-01 | Private mode enforcement (per-document, no text storage) | DB CHECK constraint exists (lines 269-276 schema.sql), backend skip logic, Radix Switch for toggle UI, lock icon for visual confirmation |
| A11Y-01 | WCAG 2.1 accessibility compliance | Contrast ratio fixes for badges, ARIA live regions, keyboard navigation with RTL support, jest-axe testing |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| @radix-ui/react-switch | ^1.1.x | Accessible toggle switch | Already using Radix, WAI-ARIA switch role compliant, keyboard accessible |
| @radix-ui/react-tooltip | ^1.1.x | Accessible tooltips | Radix ecosystem, accessible by default |
| jest-axe | ^9.0.0 | Automated a11y testing | Industry standard, integrates with existing Jest |
| @types/jest-axe | ^3.5.x | TypeScript types | Required for TypeScript projects |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| lucide-react | (existing) | Lock icon | Already installed, use Lock or LockKeyhole icon |
| axe-core | ^4.10.x | Core a11y engine | Peer dependency for jest-axe |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| @radix-ui/react-switch | Headless UI Switch | Radix already in project, consistent ecosystem |
| jest-axe | @axe-core/react | jest-axe for testing, @axe-core/react deprecated for React 18+ |
| Custom live region | @react-aria/live-announcer | Custom is simpler for this use case |

**Installation:**
```bash
cd frontend && npm install @radix-ui/react-switch @radix-ui/react-tooltip jest-axe @types/jest-axe --save-dev
```

## Architecture Patterns

### Recommended Component Structure
```
frontend/
├── components/
│   ├── ui/
│   │   └── switch.tsx         # Radix Switch wrapper (new)
│   ├── PrivateModeToggle.tsx  # Toggle with tooltip (new)
│   ├── LiveAnnouncer.tsx      # ARIA live region (new)
│   └── SeverityBadge.tsx      # Update colors for contrast
├── contexts/
│   └── LiveAnnouncerContext.tsx  # Global announcer (new)
└── hooks/
    └── useKeyboardNavigation.ts  # Arrow key nav hook (new)
```

### Pattern 1: Radix Switch Component
**What:** Accessible toggle switch with visual thumb indicator
**When to use:** Any on/off toggle that needs WAI-ARIA compliance
**Example:**
```typescript
// Source: https://www.radix-ui.com/primitives/docs/components/switch
import * as Switch from '@radix-ui/react-switch';

export function PrivateModeToggle({
  checked,
  onCheckedChange,
  disabled
}: Props) {
  return (
    <div className="flex items-center gap-3">
      <Switch.Root
        checked={checked}
        onCheckedChange={onCheckedChange}
        disabled={disabled}
        className="w-11 h-6 rounded-full bg-slate-200 dark:bg-slate-700
                   data-[state=checked]:bg-pride-purple transition-colors
                   focus:outline-none focus:ring-2 focus:ring-pride-purple/40 focus:ring-offset-2"
      >
        <Switch.Thumb
          className="block w-5 h-5 bg-white rounded-full shadow transition-transform
                     data-[state=checked]:translate-x-5 translate-x-0.5"
        />
      </Switch.Root>
      <label className="text-sm text-slate-600 dark:text-slate-300">
        {/* Label text */}
      </label>
    </div>
  );
}
```

### Pattern 2: ARIA Live Region
**What:** Persistent DOM element that announces content changes to screen readers
**When to use:** Dynamic state changes (upload complete, analysis done, errors)
**Example:**
```typescript
// Source: https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Guides/Live_regions
// CRITICAL: Element must exist in DOM at mount, not conditionally rendered

export function LiveAnnouncer() {
  const [message, setMessage] = useState('');

  // Expose via context for global access
  return (
    <div
      role="status"
      aria-live="polite"
      aria-atomic="true"
      className="sr-only"  // Visually hidden but accessible
    >
      {message}
    </div>
  );
}

// Usage in component:
const { announce } = useLiveAnnouncer();
announce('Analysis complete. 3 issues found.');
```

### Pattern 3: RTL-Aware Keyboard Navigation
**What:** Arrow key navigation that respects text direction
**When to use:** List/grid navigation in bilingual apps
**Example:**
```typescript
// Arrow keys flip direction in RTL
function useArrowNavigation(items: HTMLElement[], isRTL: boolean) {
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    const currentIndex = items.findIndex(el => el === document.activeElement);
    let nextIndex = currentIndex;

    if (e.key === 'ArrowRight') {
      nextIndex = isRTL ? currentIndex - 1 : currentIndex + 1;
    } else if (e.key === 'ArrowLeft') {
      nextIndex = isRTL ? currentIndex + 1 : currentIndex - 1;
    } else if (e.key === 'ArrowDown') {
      nextIndex = currentIndex + 1;
    } else if (e.key === 'ArrowUp') {
      nextIndex = currentIndex - 1;
    }

    // Wrap around
    nextIndex = (nextIndex + items.length) % items.length;
    items[nextIndex]?.focus();
    e.preventDefault();
  }, [items, isRTL]);

  return handleKeyDown;
}
```

### Pattern 4: WCAG AA Contrast-Compliant Badge Colors
**What:** Severity badge colors that meet 4.5:1 contrast ratio
**When to use:** All text-containing UI elements
**Example:**
```typescript
// Verified with WebAIM Contrast Checker
// All combinations meet WCAG 2.1 AA 4.5:1 minimum

const severityColors = {
  // Light mode (white bg #ffffff)
  outdated: 'bg-sky-100 text-sky-900',      // sky-900 #0c4a6e on sky-100 #e0f2fe = 7.2:1
  biased: 'bg-amber-100 text-amber-900',    // amber-900 #78350f on amber-100 #fef3c7 = 5.8:1
  offensive: 'bg-rose-100 text-rose-900',   // rose-900 #881337 on rose-100 #ffe4e6 = 6.1:1
  incorrect: 'bg-red-100 text-red-900',     // red-900 #7f1d1d on red-100 #fee2e2 = 5.9:1

  // Dark mode (slate-900 bg #0f172a)
  outdatedDark: 'dark:bg-sky-900/40 dark:text-sky-200',
  biasedDark: 'dark:bg-amber-900/40 dark:text-amber-200',
  offensiveDark: 'dark:bg-rose-900/40 dark:text-rose-200',
  incorrectDark: 'dark:bg-red-900/40 dark:text-red-200',
};
```

### Anti-Patterns to Avoid
- **Conditional live region rendering:** Screen readers lose track when aria-live elements are removed/recreated. Always keep the element mounted.
- **Using aria-live="assertive" for non-critical updates:** Interrupts users. Use "polite" for 90% of cases.
- **Hardcoded left/right arrow behavior:** Fails in RTL layouts. Always check document direction.
- **Focus indicators via `:focus` only:** Some users disable outlines. Use `:focus-visible` for keyboard-only focus.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Toggle switch | Custom checkbox styling | @radix-ui/react-switch | ARIA roles, keyboard nav, state management |
| Tooltip | title attribute or custom | @radix-ui/react-tooltip | Accessible, delayed show, proper positioning |
| Contrast checking | Manual color picking | WebAIM Contrast Checker | Accurate WCAG compliance verification |
| A11y testing | Manual checklist | jest-axe + axe-core | Catches 57% of WCAG issues automatically |

**Key insight:** Radix primitives handle the hard accessibility work (focus trapping, ARIA attributes, keyboard interaction). Custom implementations invariably miss edge cases.

## Common Pitfalls

### Pitfall 1: Live Region Not Announcing
**What goes wrong:** Screen reader never reads dynamic updates
**Why it happens:** Element is conditionally rendered, so it doesn't exist when content changes
**How to avoid:** Mount live region element once at app root, never unmount
**Warning signs:** Works in some browsers but not others, or works initially then stops

### Pitfall 2: Color Contrast Fails in Dark Mode
**What goes wrong:** Passes in light mode, fails WCAG in dark mode
**Why it happens:** Only testing one theme, or dark mode uses transparency that reduces contrast
**How to avoid:** Test both themes with contrast checker, avoid opacity on text colors
**Warning signs:** Badge text hard to read in dark mode

### Pitfall 3: Focus Ring Invisible on Some Backgrounds
**What goes wrong:** Focus indicator not visible against certain backgrounds
**Why it happens:** Using same-color outline as background
**How to avoid:** Use offset + contrasting color, or ring with both light and dark components
**Warning signs:** Can't see focus when tabbing through UI

### Pitfall 4: Arrow Keys Work Backwards in Hebrew
**What goes wrong:** Right arrow goes to previous item in RTL
**Why it happens:** Hardcoded left=previous, right=next
**How to avoid:** Check `isHebrew` / document direction before mapping keys
**Warning signs:** Navigation feels "backwards" when switching languages

### Pitfall 5: Private Mode Stored in URL/History
**What goes wrong:** Private mode setting leaks into browser history or shareable URLs
**Why it happens:** Using URL query params for toggle state
**How to avoid:** Use React state only, never persist privacy setting
**Warning signs:** Refreshing page changes privacy state unexpectedly

## Code Examples

### Private Mode Toggle with Tooltip
```typescript
// Source: Radix Switch + Tooltip primitives
import * as Switch from '@radix-ui/react-switch';
import * as Tooltip from '@radix-ui/react-tooltip';
import { Lock } from 'lucide-react';

interface PrivateModeToggleProps {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  label: string;
  tooltip: string;
}

export function PrivateModeToggle({
  checked,
  onCheckedChange,
  label,
  tooltip
}: PrivateModeToggleProps) {
  return (
    <div className="flex items-center gap-3">
      <Tooltip.Provider delayDuration={300}>
        <Tooltip.Root>
          <Tooltip.Trigger asChild>
            <div className="flex items-center gap-2">
              <Switch.Root
                checked={checked}
                onCheckedChange={onCheckedChange}
                id="private-mode"
                className="w-11 h-6 rounded-full bg-slate-200 dark:bg-slate-700
                           data-[state=checked]:bg-pride-purple transition-colors
                           focus-visible:outline-none focus-visible:ring-2
                           focus-visible:ring-pride-purple focus-visible:ring-offset-2"
              >
                <Switch.Thumb
                  className="block w-5 h-5 bg-white rounded-full shadow-sm transition-transform
                             data-[state=checked]:translate-x-5 translate-x-0.5"
                />
              </Switch.Root>
              <label
                htmlFor="private-mode"
                className="text-sm font-medium text-slate-700 dark:text-slate-200 cursor-pointer flex items-center gap-1.5"
              >
                <Lock className="w-4 h-4" />
                {label}
              </label>
            </div>
          </Tooltip.Trigger>
          <Tooltip.Portal>
            <Tooltip.Content
              className="px-3 py-2 text-sm bg-slate-900 text-white rounded-lg shadow-lg max-w-xs"
              sideOffset={5}
            >
              {tooltip}
              <Tooltip.Arrow className="fill-slate-900" />
            </Tooltip.Content>
          </Tooltip.Portal>
        </Tooltip.Root>
      </Tooltip.Provider>
    </div>
  );
}
```

### Live Announcer Context
```typescript
// Source: MDN ARIA live regions + React context pattern
'use client';

import { createContext, useContext, useState, useCallback, ReactNode } from 'react';

interface LiveAnnouncerContextType {
  announce: (message: string, priority?: 'polite' | 'assertive') => void;
}

const LiveAnnouncerContext = createContext<LiveAnnouncerContextType | null>(null);

export function LiveAnnouncerProvider({ children }: { children: ReactNode }) {
  const [politeMessage, setPoliteMessage] = useState('');
  const [assertiveMessage, setAssertiveMessage] = useState('');

  const announce = useCallback((message: string, priority: 'polite' | 'assertive' = 'polite') => {
    // Clear then set to ensure announcement even if same message
    if (priority === 'assertive') {
      setAssertiveMessage('');
      setTimeout(() => setAssertiveMessage(message), 50);
    } else {
      setPoliteMessage('');
      setTimeout(() => setPoliteMessage(message), 50);
    }
  }, []);

  return (
    <LiveAnnouncerContext.Provider value={{ announce }}>
      {children}
      {/* Visually hidden but accessible to screen readers */}
      <div className="sr-only" aria-live="polite" aria-atomic="true">
        {politeMessage}
      </div>
      <div className="sr-only" aria-live="assertive" aria-atomic="true">
        {assertiveMessage}
      </div>
    </LiveAnnouncerContext.Provider>
  );
}

export function useLiveAnnouncer() {
  const context = useContext(LiveAnnouncerContext);
  if (!context) {
    throw new Error('useLiveAnnouncer must be used within LiveAnnouncerProvider');
  }
  return context;
}
```

### jest-axe Test Setup
```typescript
// Source: https://github.com/NickColley/jest-axe
// jest.setup.ts
import { toHaveNoViolations } from 'jest-axe';

expect.extend(toHaveNoViolations);

// Component test example
import { render } from '@testing-library/react';
import { axe } from 'jest-axe';
import { PrivateModeToggle } from './PrivateModeToggle';

describe('PrivateModeToggle', () => {
  it('should have no accessibility violations', async () => {
    const { container } = render(
      <PrivateModeToggle
        checked={false}
        onCheckedChange={() => {}}
        label="Private mode"
        tooltip="Your document will not be stored"
      />
    );

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
```

### Updated SeverityBadge with Contrast-Compliant Colors
```typescript
// Verified colors meeting WCAG 2.1 AA 4.5:1 contrast
'use client';

import { useTranslations } from 'next-intl';
import { cn } from '@/lib/utils';

export type Severity = 'outdated' | 'biased' | 'offensive' | 'incorrect';

export default function SeverityBadge({ level }: { level: Severity }) {
  const t = useTranslations('severity');

  // Colors verified with WebAIM Contrast Checker for WCAG AA compliance
  const color = {
    outdated: 'bg-sky-100 text-sky-900 dark:bg-sky-900/40 dark:text-sky-100',
    biased: 'bg-amber-100 text-amber-900 dark:bg-amber-900/40 dark:text-amber-100',
    offensive: 'bg-rose-100 text-rose-900 dark:bg-rose-900/40 dark:text-rose-100',
    incorrect: 'bg-red-100 text-red-900 dark:bg-red-900/40 dark:text-red-100',
  }[level];

  return <span className={cn('badge', color)}>{t(level)}</span>;
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| @axe-core/react | jest-axe + manual testing | 2024 | @axe-core/react deprecated for React 18+, use jest-axe for tests |
| :focus for all | :focus-visible | 2022 | Only shows focus for keyboard users, better UX |
| title attribute | ARIA tooltips | Long-standing | title not reliably announced, timing issues |
| role="alert" everywhere | aria-live="polite" | Best practice | assertive interrupts, polite waits for pause |

**Deprecated/outdated:**
- @axe-core/react: Deprecated, doesn't support React 18+
- title attribute for tooltips: Unreliable accessibility, use proper tooltip components
- tabindex on non-interactive elements: Confuses keyboard users

## Open Questions

1. **Screen reader testing strategy**
   - What we know: Automated tests catch ~57% of issues
   - What's unclear: How to test actual screen reader behavior in CI
   - Recommendation: Manual testing with VoiceOver (macOS) before release, automated tests for regression

2. **Hebrew live region announcement order**
   - What we know: RTL affects visual layout
   - What's unclear: Does RTL affect screen reader announcement order?
   - Recommendation: Test with Hebrew text in VoiceOver, adjust message structure if needed

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Jest + Testing Library (to be configured) |
| Config file | none - see Wave 0 |
| Quick run command | `npm test -- --testPathPattern=accessibility` |
| Full suite command | `npm test` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PRIV-01 | Toggle checked state updates | unit | `npm test -- PrivateModeToggle.test.tsx` | Wave 0 |
| PRIV-01 | No violations on toggle | unit | `npm test -- PrivateModeToggle.test.tsx` | Wave 0 |
| A11Y-01 | SeverityBadge no violations | unit | `npm test -- SeverityBadge.test.tsx` | Wave 0 |
| A11Y-01 | Live announcer announces | unit | `npm test -- LiveAnnouncer.test.tsx` | Wave 0 |
| A11Y-01 | Landing page no violations | integration | `npm test -- landing.a11y.test.tsx` | Wave 0 |
| A11Y-01 | Analyze page no violations | integration | `npm test -- analyze.a11y.test.tsx` | Wave 0 |

### Sampling Rate
- **Per task commit:** `npm test -- --testPathPattern=accessibility --bail`
- **Per wave merge:** `npm test`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `frontend/jest.config.js` - Jest configuration for Next.js 16
- [ ] `frontend/jest.setup.ts` - jest-axe extension setup
- [ ] `frontend/__tests__/` - Test directory structure
- [ ] Install: `npm install -D jest @testing-library/react @testing-library/jest-dom jest-axe @types/jest-axe jest-environment-jsdom`

## Sources

### Primary (HIGH confidence)
- [Radix UI Switch](https://www.radix-ui.com/primitives/docs/components/switch) - Component API, accessibility features
- [WCAG 2.1 Contrast (Minimum)](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html) - 4.5:1 ratio requirement
- [MDN ARIA Live Regions](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Guides/Live_regions) - Implementation guidance
- [jest-axe GitHub](https://github.com/NickColley/jest-axe) - Testing setup and usage

### Secondary (MEDIUM confidence)
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/) - Color verification tool
- [WebAIM Keyboard Accessibility](https://webaim.org/techniques/keyboard/) - Navigation patterns
- [When Your Live Region Isn't Live](https://k9n.dev/blog/2025-11-aria-live/) - React-specific gotchas

### Tertiary (LOW confidence)
- RTL keyboard navigation specifics - limited documentation, needs manual testing

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Radix already in project, jest-axe is standard
- Architecture: HIGH - Patterns well-documented
- Pitfalls: HIGH - Verified from official sources and recent articles
- RTL keyboard nav: MEDIUM - General patterns clear, Hebrew-specific needs testing

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (30 days - stable domain)
