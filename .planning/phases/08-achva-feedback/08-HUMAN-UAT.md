---
status: partial
phase: 08-achva-feedback
source: [08-VERIFICATION.md]
started: 2026-04-18T00:00:00.000Z
updated: 2026-04-18T00:00:00.000Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. D-01: Profile popup session behavior
expected: Modal opens on every new session when any of full_name, institution, profession is empty. After filling all 3 fields and clicking Save, modal does NOT re-open after refreshProfile() triggers (no race condition). sessionStorage key 'profile_setup_dismissed' is set after dismissal.
result: [pending]

### 2. D-02: LLM-down banner visible in real results
expected: When backend returns analysis_mode === 'rules_only' in an actual analysis response, a red HealthWarningBanner appears in the results view with a link to the glossary. The pre-analysis modelUnavailable banner is unaffected.
result: [pending]

### 3. D-03: PDF footer watermark visual inspection
expected: Exported PDF shows "Achva LGBTQ+ Studential Organization" centered at the bottom of every page (EN locale). Hebrew locale shows "ארגון אחווה להט״ב הסטודנטיאלי". No diagonal INCLUSIFY watermark appears anywhere in the PDF.
result: [pending]

### 4. D-04: Contact form email delivery (no attachment)
expected: Clicking Contact Us in Navbar opens modal. Filling subject + message and clicking Send shows "Message sent!" toast, modal closes, and email arrives at wieder.shahaf@gmail.com and shahaf200019@gmail.com. Requires SMTP_USER + SMTP_PASSWORD env vars set with Gmail App Password.
result: [pending]

### 5. D-04: Contact form with PDF attachment
expected: On the analyze results page (after an analysis completes), clicking Contact Us shows "Analysis report attached" indicator. Sending the form delivers email with PDF attachment to admin inboxes.
result: [pending]

### 6. D-05: WebSocket auto-refresh on new analysis
expected: Admin dashboard OverviewTab shows FrequencyTrendsCard with pulsing green dot when WebSocket is connected. After a regular user submits a new analysis in another tab, the bar chart in the admin dashboard refreshes automatically without page reload.
result: [pending]

## Summary

total: 6
passed: 0
issues: 0
pending: 6
skipped: 0
blocked: 0

## Gaps
