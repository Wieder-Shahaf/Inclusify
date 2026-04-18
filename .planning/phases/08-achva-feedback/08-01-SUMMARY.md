---
phase: 08-achva-feedback
plan: "08-01"
subsystem: ui
tags: [react, zod, jest, testing-library, next-intl, radix-ui]

# Dependency graph
requires:
  - phase: 07-auth
    provides: AuthContext with user.full_name/institution/profession fields
provides:
  - ProfileSetupModal with all-3-fields completion check
  - Zod schema rejecting empty institution/profession
  - 8 Jest tests for modal completion logic and schema validation
  - i18n keys profile.setup.save/saving/skip in both en.json and he.json
affects: [08-02, 08-03, 08-04, 08-05]

# Tech tracking
tech-stack:
  added:
    - "@testing-library/dom (missing peer dep for @testing-library/react)"
  patterns:
    - "TDD RED/GREEN: write failing tests first, then implement to make them pass"
    - "Export Zod schema (profileSetupSchema) from component for test imports"
    - "dismiss() pattern: sets sessionStorage AND closes modal — prevents re-open on refreshProfile()"

key-files:
  created:
    - frontend/__tests__/ProfileSetupModal.test.tsx
  modified:
    - frontend/components/ProfileSetupModal.tsx
    - frontend/messages/he.json

key-decisions:
  - "D-01b: Completion check now requires all 3 fields (full_name AND institution AND profession), not just full_name"
  - "D-01c: Zod schema changed from optional to min(1) required for institution and profession"
  - "onSubmit success calls dismiss() not setOpen(false) to prevent race condition when refreshProfile() triggers useEffect re-run"
  - "he.json skip key corrected to 'דלג בינתיים' per UI-SPEC copywriting contract (was 'דלג לעת עתה')"

patterns-established:
  - "Profile completion check pattern: !user.full_name || !user.institution || !user.profession"
  - "sessionStorage dismiss key pattern: prevents modal re-open per session"

requirements-completed:
  - D-01

# Metrics
duration: 20min
completed: 2026-04-18
---

# Phase 8 Plan 01: Profile Completion Popup Required Fields Summary

**ProfileSetupModal now enforces all 3 required fields (full_name, institution, profession) with Zod validation, corrected dismiss() race-condition fix, red asterisk labels, and 8 Jest tests GREEN**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-04-18T00:00:00Z
- **Completed:** 2026-04-18T00:20:00Z
- **Tasks:** 3
- **Files modified:** 4 (ProfileSetupModal.tsx, he.json, package.json, package-lock.json) + 1 created (__tests__/ProfileSetupModal.test.tsx)

## Accomplishments
- ProfileSetupModal completion check now requires all 3 fields: if any of full_name, institution, or profession is null, modal opens every session
- Zod schema: institution and profession changed from optional to `z.string().min(1)` — form submission blocked on empty
- Submit success path: `setOpen(false)` replaced with `dismiss()` — prevents modal re-opening after `refreshProfile()` triggers a useEffect re-run
- Red asterisk labels added to profession and institution fields with `aria-required="true"`
- 8 Jest tests covering completion logic (Tests 1-5) and Zod schema (Tests 6-8) — all GREEN
- Hebrew i18n: `profile.setup.skip` corrected to `"דלג בינתיים"` per UI-SPEC copywriting contract

## Task Commits

1. **Task 1: Create ProfileSetupModal test scaffold (TDD RED)** - `da4d0a3` (test)
2. **Task 2: Fix ProfileSetupModal completion check, Zod schema, labels, submit path (TDD GREEN)** - `aec1965` (feat)
3. **Task 3: Add profile.setup i18n keys** - `e57710c` (feat)

## Files Created/Modified
- `frontend/__tests__/ProfileSetupModal.test.tsx` - 8 Jest tests for completion logic and Zod schema validation
- `frontend/components/ProfileSetupModal.tsx` - Updated: exported schema, 3-field completion check, required Zod, dismiss() in submit, asterisk labels
- `frontend/messages/he.json` - Corrected `profile.setup.skip` to `"דלג בינתיים"` (was "דלג לעת עתה")
- `frontend/package.json` + `package-lock.json` - Added `@testing-library/dom` missing peer dep

## Decisions Made
- **he.json skip key correction:** UI-SPEC copywriting contract specifies `"דלג בינתיים"` — existing value `"דלג לעת עתה"` was updated to match
- **en.json skip key:** Already had correct values (`"Save Profile"`, `"Saving..."`, `"Skip for now"`) — no change needed
- **profileSetupSchema exported:** Made schema `export const` so tests can import and validate it directly without re-declaration

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed missing @testing-library/dom peer dependency**
- **Found during:** Task 1 (ProfileSetupModal test scaffold)
- **Issue:** `@testing-library/react` requires `@testing-library/dom` as a peer dependency; it was not installed — test runner failed to start with "Cannot find module '@testing-library/dom'"
- **Fix:** Ran `npm install --save-dev @testing-library/dom`
- **Files modified:** `frontend/package.json`, `frontend/package-lock.json`
- **Verification:** Tests ran successfully after install
- **Committed in:** `da4d0a3` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking dependency)
**Impact on plan:** Essential fix to unblock test runner. No scope creep.

## Issues Encountered
- Jest 30 uses `--testPathPatterns` (plural) instead of `--testPathPattern` — plan verification commands used old flag, adjusted at runtime

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- ProfileSetupModal is fully functional: opens on every session until all 3 fields filled, enforces required fields, correctly dismisses
- Plan 08-02 (LLM-down banner) can proceed independently
- No blockers

---
*Phase: 08-achva-feedback*
*Completed: 2026-04-18*
