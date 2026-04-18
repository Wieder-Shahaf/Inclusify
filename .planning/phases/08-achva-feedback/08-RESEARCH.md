# Phase 8: Achva Feedback — Research

**Researched:** 2026-04-18
**Domain:** Full-stack feature work across Next.js 16 / FastAPI / asyncpg / jsPDF / FastAPI WebSocket
**Confidence:** HIGH

---

## Summary

Phase 8 implements 11 stakeholder improvements across 5 feature tracks. The codebase is in an advanced state: five of the 11 items are already fully implemented (confirmed by code inspection). The remaining 6 items — profile popup field-check fix, LLM-down banner wiring, PDF footer watermark, Contact Us endpoint + modal, admin frequency trend chart, and WebSocket push — each require narrow, well-defined changes. No new architecture is needed; every change slots into existing patterns.

The key integration risk is D-04 (Contact Us), which has two partially-conflicting implementations already in the codebase: `analyze/page.tsx` already has a `handleContactUs` function that opens a `mailto:` link directly (not a modal), and there is no backend `/api/v1/contact` endpoint yet. The decision requires replacing the `mailto:` shortcut with a proper modal + smtplib email flow. The plan must address this existing code explicitly.

A secondary risk is D-05 (admin WebSocket): FastAPI WebSockets are not CORS-protected the same way as HTTP routes — the `CORSMiddleware` does not apply to WebSocket connections. The frontend must connect using `ws://` / `wss://` URLs, and the backend must manually verify the JWT in the WebSocket handshake (no `Depends` auto-injection). The plan must include a manual auth step.

**Primary recommendation:** Implement in 5 discrete plan files: (1) D-01 profile popup, (2) D-02 LLM-down banner, (3) D-03 PDF footer, (4) D-04 Contact Us (backend + frontend), (5) D-05 admin frequency trends + WebSocket. Each plan is independently deployable.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Already Implemented (confirmed in codebase — planner should verify, not re-implement)
- **D-already-1:** Loading text — ProcessingAnimation already has stage-based translations; update i18n strings to "Checking for non-inclusive writing..." (EN) and Hebrew equivalent in `frontend/messages/en.json` + `frontend/messages/he.json`.
- **D-already-2:** Score label — `AnalysisSummary.tsx` `defaultTranslations.score` already reads `'LGBTQ+ inclusivity score.'` ✓
- **D-already-3:** Drop rule-based detection — `hybrid_detector.py` is already LLM-only; `analysis_mode='rules_only'` is returned when LLM is unavailable ✓
- **D-already-4:** `inclusive_sentence` field — `Issue` model and `llm_client.py` already return `inclusive_sentence` in the LLM response ✓
- **D-already-5:** Admin user table filters — `/api/v1/admin/users` already accepts `institution` and `min_analyses` query params; `UsersTab` frontend already has filter UI ✓

#### Profile Completion Popup (D-01)
- Show popup every session until profile is complete. Use `sessionStorage` — do NOT switch to localStorage.
- Popup disappears only when all three fields are set: `full_name`, `institution`, `profession`.
- All three fields must be required in the Zod schema (currently `institution` and `profession` are optional).
- `ProfileSetupModal` is already built and already wired into layout — update required fields only.

#### LLM-Down Fallback (D-02)
- When `analysis_mode === 'rules_only'` in the analysis response, show `HealthWarningBanner` on the analyze results view.
- Banner message (EN): `"Analysis service is temporarily unavailable. Browse the glossary for guidance."`
- Banner links to the existing `/[locale]/glossary` route.
- Banner uses `variant='error'` (amber). `linkHref` = `/[locale]/glossary`, `linkText` = `"Browse glossary"`.
- Add i18n keys for the banner message and link text.

#### PDF Report Watermark (D-03)
- Add a footer watermark to every page of exported PDFs in `frontend/lib/exportReport.ts`.
- Watermark text is locale-driven: EN: `"Achva LGBTQ+ Studential Organization"` / HE: `"ארגון אחווה להט״ב הסטודנטיאלי"`.
- Position: bottom footer on each page (not diagonal, not first page only).
- Style: small gray text, centered, near page bottom.

#### Contact Us Feature (D-04)
- "Contact us" button lives in the navigation bar (always visible, all pages).
- Clicking opens a modal with: subject field, message field, auto-prefilled read-only user info from AuthContext.
- Backend: new router at `POST /api/v1/contact` using Python `smtplib` (stdlib — no new deps).
- SMTP config: Gmail + App Password via env vars (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`).
- Recipient list: query `site_admin` users' emails from DB.
- Optional PDF attachment: if analysis is complete, call `exportReport()` in base64-return mode and include as file attachment.
- Coordinate with Adan's branch — `exportReport.ts` needs base64-return mode (not auto-download).

#### Admin Frequency Trends (D-05)
- Add new section to admin dashboard: label frequency bar chart + top-5 phrases per label.
- Bar chart: each bar = one category label. Bar height = count of findings with that category in the selected time window.
- Top-5 phrases: dropdown per label listing 5 most frequent `excerpt_redacted` values for that category.
- Auto-refresh: WebSocket push from backend when a new analysis completes.
- New SQL query `get_label_frequency_trends(conn, days)` in `admin/queries.py`.
- WebSocket endpoint: `GET /api/v1/admin/ws` — admin-only, pushes `{event: "new_analysis"}`.

### Claude's Discretion
- Exact Hebrew translations for new i18n strings.
- WebSocket library choice — use `fastapi.websockets` (native).
- Contact modal UI component structure — follow `ProfileSetupModal.tsx` as reference.
- Retry/error handling in the contact API endpoint — use `sonner` toast pattern.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| D-01 | Profile completion popup shows every session until all 3 fields filled | ProfileSetupModal.tsx exists; Zod schema fix + completion check update |
| D-02 | LLM-down banner appears when analysis_mode === 'rules_only' | HealthWarningBanner exists; analyze/page.tsx has analysisMode state; needs new conditional render in results view |
| D-03 | PDF footer watermark on every page, locale-driven text | exportReport.ts has a working watermark loop; replace diagonal INCLUSIFY watermark with footer text; add base64-return mode |
| D-04 | Contact Us modal in navbar with smtplib email + optional PDF attachment | analyze/page.tsx has mailto shortcut to replace; no backend /api/v1/contact exists; ContactModal component to build |
| D-05 | Admin frequency trends bar chart + top-5 phrases + WebSocket auto-refresh | No /api/v1/admin/ws exists; no get_label_frequency_trends query exists; bar chart component needed; SWR mutate pattern for refresh |
</phase_requirements>

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Profile popup display logic | Browser / Client | — | Reads sessionStorage + AuthContext in client component |
| LLM-down banner conditional render | Browser / Client | API / Backend | Frontend reads `analysis_mode` from API response |
| PDF watermark generation | Browser / Client | — | jsPDF runs entirely client-side |
| Contact Us modal UI | Browser / Client | — | React Dialog, client-side form |
| Contact Us email send | API / Backend | Database / Storage | smtplib on server; DB query for admin emails |
| Contact PDF attachment encode | Browser / Client | — | exportReport base64 mode, browser-side |
| Admin frequency trends query | Database / Storage | API / Backend | SQL GROUP BY on findings table |
| Admin WebSocket push | API / Backend | Browser / Client | FastAPI WebSocket endpoint; frontend connects on mount |
| Admin bar chart render | Browser / Client | — | Custom SVG chart (no recharts installed) |

---

## Standard Stack

### Core (verified from package.json and codebase)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| jsPDF | 4.2.1 | PDF generation | Already used in exportReport.ts [VERIFIED: package.json] |
| jspdf-autotable | 5.0.7 | Table layout in PDFs | Already used in exportReport.ts [VERIFIED: package.json] |
| @radix-ui/react-dialog | 1.1.15 | Modal dialogs | Used in ProfileSetupModal.tsx (reference pattern) [VERIFIED: package.json] |
| react-hook-form | 7.54.0 | Form state + validation | Used in ProfileSetupModal.tsx [VERIFIED: package.json] |
| zod | 4.1.0 | Form schema validation | Used in ProfileSetupModal.tsx [VERIFIED: package.json] |
| sonner | 1.7.4 | Toast notifications | Used throughout frontend [VERIFIED: package.json] |
| swr | 2.4.1 | Data fetching + revalidation | Used for all admin API hooks [VERIFIED: package.json] |
| framer-motion | 12.23.26 | Animation | Used in HealthWarningBanner, OverviewTab [VERIFIED: package.json] |
| fastapi (WebSocket) | stdlib | WebSocket push | Native FastAPI — no new dep needed [VERIFIED: FastAPI docs] |
| smtplib | Python stdlib | Email sending | stdlib — no new dep needed [VERIFIED: smtplib OK in environment] |

**No charting library is installed.** The admin dashboard uses custom SVG components (`SimpleLineChart.tsx`, `DonutChart.tsx`). The D-05 bar chart must follow the same custom SVG pattern. [VERIFIED: package.json, dashboard/] directory inspection]

### No New Dependencies Required
All features can be implemented with existing installed packages. The plan must NOT add recharts, chart.js, nodemailer, or any email library — smtplib is stdlib and already working in this Python 3.11 environment.

---

## Architecture Patterns

### System Architecture Diagram

```
D-01 Profile Popup Flow:
AuthProvider (validates token) → setUser() → ProfileSetupModal (useEffect on user)
  → sessionStorage check ('profile_setup_dismissed') → check all 3 fields
  → Dialog open=true → form submit → PATCH /api/v1/users/me/profile → refreshProfile()

D-02 LLM-Down Banner Flow:
analyze/page.tsx: POST /api/v1/analysis/analyze → response.analysis_mode
  → setAnalysisMode() → viewState='results'
  → {analysisMode === 'rules_only' && <HealthWarningBanner .../>}

D-03 PDF Export Flow (updated):
exportReport(analysis, {fileName, locale}) → jsPDF → autoTable → loop pages
  → per-page: doc.setPage(i) → footer text at (pageWidth/2, pageHeight - 8)
  → if returnBase64: return doc.output('datauristring') else doc.save(...)

D-04 Contact Us Flow:
Navbar → <ContactModal> (Radix Dialog)
  → form: subject, message, prefill from AuthContext
  → if analysisComplete: exportReport(base64 mode) → base64 string
  → POST /api/v1/contact (multipart: subject, message, user info, optional PDF)
  → backend: smtplib → SELECT emails FROM users WHERE role='site_admin' → send email

D-05 Admin Frequency Trends Flow:
AdminDashboard (OverviewTab) → useAdminFrequencyTrends(days) [new SWR hook]
  → GET /api/v1/admin/frequency-trends?days=N
  → custom SVG BarChart + expandable dropdown per label
  WebSocket:
  analysis/router.py: after _persist_results() → broadcast to WS connections
  AdminDashboard: useEffect → new WebSocket('ws://.../api/v1/admin/ws?token=...')
    → onmessage({event:'new_analysis'}) → refresh SWR caches (mutate)
```

### Recommended Project Structure (additions only)
```
frontend/
├── components/
│   ├── ContactModal.tsx        # NEW: D-04 modal (follow ProfileSetupModal pattern)
│   └── dashboard/
│       ├── SimpleBarChart.tsx  # NEW: D-05 custom SVG bar chart (follow SimpleLineChart)
│       └── FrequencyTrendsTab.tsx  # NEW: D-05 card with bar chart + dropdowns
├── lib/api/
│   ├── contact.ts              # NEW: D-04 POST /api/v1/contact
│   └── admin.ts                # UPDATE: add useAdminFrequencyTrends hook
backend/app/modules/
├── contact/
│   ├── __init__.py             # NEW: D-04 module
│   └── router.py               # NEW: POST /api/v1/contact
```

### Pattern 1: Radix Dialog Modal (from ProfileSetupModal.tsx)
**What:** Client component using `@radix-ui/react-dialog`, `react-hook-form`, `zod`, `sonner` toast.
**When to use:** Any modal in the frontend — Contact Us modal must follow this exact pattern.

```typescript
// Source: frontend/components/ProfileSetupModal.tsx
'use client';
import * as Dialog from '@radix-ui/react-dialog';
// ...
return (
  <Dialog.Root open={open} onOpenChange={(v) => { if (!v) handleClose(); }}>
    <Dialog.Portal>
      <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm" />
      <Dialog.Content className="fixed z-50 left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md">
        <div className="glass p-8 rounded-2xl shadow-2xl">
          {/* content */}
        </div>
      </Dialog.Content>
    </Dialog.Portal>
  </Dialog.Root>
);
```

### Pattern 2: Admin asyncpg Query
**What:** Raw SQL in `queries.py`, FastAPI Depends for auth, `_verify_db_pool` guard.
**When to use:** Every new admin endpoint.

```python
# Source: backend/app/modules/admin/queries.py
async def get_label_frequency_trends(conn: asyncpg.Connection, days: int) -> list[dict]:
    cutoff = datetime.utcnow() - timedelta(days=days)
    rows = await conn.fetch("""
        SELECT
            f.category,
            COUNT(*) AS count,
            ARRAY_AGG(f.excerpt_redacted ORDER BY f.excerpt_redacted) AS excerpts
        FROM findings f
        JOIN analysis_runs ar ON f.run_id = ar.run_id
        WHERE ar.started_at >= $1
          AND f.excerpt_redacted IS NOT NULL
        GROUP BY f.category
        ORDER BY count DESC
    """, cutoff)
    # For each category, extract top-5 most frequent phrases
    result = []
    for row in rows:
        from collections import Counter
        phrase_counts = Counter(row['excerpts'])
        top5 = [{'phrase': p, 'count': c} for p, c in phrase_counts.most_common(5)]
        result.append({'category': row['category'], 'count': row['count'], 'top_phrases': top5})
    return result
```

### Pattern 3: SWR Hook for Admin Data
**What:** Authenticated SWR fetcher in `frontend/lib/api/admin.ts`.
**When to use:** Any new admin data endpoint.

```typescript
// Source: frontend/lib/api/admin.ts (existing pattern)
export function useAdminFrequencyTrends(days: number) {
  const { data, error, isLoading, mutate } = useSWR<FrequencyTrendsResponse>(
    `${API_BASE_URL}/api/v1/admin/frequency-trends?days=${days}`,
    fetcher,
    { revalidateOnFocus: false }
  );
  return { data, isLoading, error, refresh: mutate };
}
```

### Pattern 4: jsPDF Per-Page Footer
**What:** Iterate pages after `autoTable`, set page, draw text at bottom.
**When to use:** D-03 watermark. The existing code already uses this exact pattern for a diagonal watermark — replace it with a footer.

```typescript
// Source: frontend/lib/exportReport.ts (existing watermark loop, adapted)
const totalPages: number = (doc as any).internal.getNumberOfPages();
const watermarkText = locale === 'he'
  ? 'ארגון אחווה להט״ב הסטודנטיאלי'
  : 'Achva LGBTQ+ Studential Organization';
for (let i = 1; i <= totalPages; i++) {
  doc.setPage(i);
  doc.setFontSize(8);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(150, 150, 150);
  doc.text(watermarkText, pageWidth / 2, pageHeight - 8, { align: 'center' });
}
```

### Pattern 5: FastAPI Native WebSocket with Manual JWT Auth
**What:** No `Depends()` injection in WebSocket handlers — must manually decode JWT from query param.
**When to use:** D-05 admin WebSocket endpoint.

```python
# Source: [CITED: FastAPI docs https://fastapi.tiangolo.com/advanced/websockets/]
from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from jose import jwt, JWTError
from app.core.config import settings

# Connection manager (module-level, shared between HTTP and WS handlers)
class AdminWSManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket):
        self.connections.remove(ws)

    async def broadcast(self, message: dict):
        dead = []
        for ws in self.connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.connections.remove(ws)

ws_manager = AdminWSManager()

@router.websocket("/ws")
async def admin_ws(websocket: WebSocket, token: str = None):
    # Manual JWT auth (Depends doesn't work in WS)
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"],
                             audience="fastapi-users:auth")
        if payload.get("role") != "site_admin":
            await websocket.close(code=4003)
            return
    except JWTError:
        await websocket.close(code=4001)
        return
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep alive
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
```

### Pattern 6: smtplib Email with Attachment
**What:** Python stdlib email sending via SMTP.

```python
# Source: [ASSUMED] Python smtplib + email.mime stdlib pattern
import smtplib
import os
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

async def send_contact_email(subject: str, body: str, pdf_bytes: bytes | None,
                              admin_emails: list[str]) -> None:
    msg = MIMEMultipart()
    msg['From'] = os.getenv('SMTP_USER')
    msg['To'] = ', '.join(admin_emails)
    msg['Subject'] = f"[Inclusify Contact] {subject}"
    msg.attach(MIMEText(body, 'plain'))

    if pdf_bytes:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(pdf_bytes)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="analysis_report.pdf"')
        msg.attach(part)

    with smtplib.SMTP(os.getenv('SMTP_HOST', 'smtp.gmail.com'),
                      int(os.getenv('SMTP_PORT', '587'))) as server:
        server.starttls()
        server.login(os.getenv('SMTP_USER'), os.getenv('SMTP_PASSWORD'))
        server.sendmail(msg['From'], admin_emails, msg.as_string())
```

### Anti-Patterns to Avoid
- **Using `Depends()` for WebSocket auth:** FastAPI cannot inject `Depends` into WebSocket handlers the same way as HTTP. Always decode JWT manually from the `token` query param.
- **Using localStorage in useState initializer:** Never initialize state from localStorage directly (hydration crash). AuthContext already handles this correctly.
- **CORSMiddleware protecting WebSockets:** The existing `CORSMiddleware` does not cover WebSocket connections — do not assume it does. JWT-based auth in the WS handshake is the only protection.
- **Calling `doc.save()` and returning base64 in the same call:** jsPDF's `doc.output('datauristring')` returns the PDF as a data URI; `doc.save()` triggers a download. The two modes are mutually exclusive — the `exportReport` signature must accept a mode parameter.
- **Making `institution`/`profession` optional in Zod and marking label as required:** The visual `*` asterisk marker must match the Zod schema. D-01 requires updating both the schema and the label markup in `ProfileSetupModal.tsx`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bar chart | Custom D3 or ad-hoc SVG from scratch | Extend `SimpleLineChart.tsx` pattern — custom SVG, no library needed | No charting lib installed; custom SVG is the established pattern |
| Email sending | Custom HTTP client to Gmail API | Python `smtplib` + Gmail App Password | stdlib, no new dependency |
| Modal | Custom CSS overlay | `@radix-ui/react-dialog` | Already installed; focus trap, accessibility, keyboard handling included |
| Form validation | Manual validation | `zod` + `react-hook-form` | Already installed; pattern established in ProfileSetupModal |
| Admin data fetching | Raw `fetch` in useEffect | SWR hooks in `frontend/lib/api/admin.ts` | Caching, deduplication, revalidation included |
| WebSocket reconnect | Manual setTimeout reconnect | Browser native WebSocket with `onclose` handler | Simple enough; no library needed |

---

## Current State Findings (what actually exists vs. what CONTEXT.md says)

### D-01: Profile Popup — PARTIALLY DONE, NEEDS FIXES
**Current state:** `ProfileSetupModal.tsx` exists and is already wired into `layout.tsx` (line 93: `<ProfileSetupModal />`). The `DISMISSED_KEY = 'profile_setup_dismissed'` pattern uses sessionStorage correctly.

**What's wrong:** The `useEffect` completion check on line 37 only checks `!user.full_name`:
```typescript
if (!dismissed && !user.full_name) {  // BUG: should also check institution + profession
```

The Zod schema marks `profession` and `institution` as optional (lines 18-19). The form labels do not show `*` for these fields.

**Required changes:**
1. Update `useEffect` condition to: `!user.full_name || !user.institution || !user.profession`
2. Update Zod schema: `profession: z.string().min(1).max(200)` (remove `.optional().or(z.literal(''))`)
3. Update Zod schema: `institution: z.string().min(1).max(200)` (same)
4. Add `<span className="text-red-500">*</span>` to `profession` and `institution` labels

### D-02: LLM-Down Banner — NOT YET WIRED FOR ANALYSIS RESULTS
**Current state:** `HealthWarningBanner` component exists and is already imported in `analyze/page.tsx`. The component has all needed props (`message`, `variant`, `linkHref`, `linkText`). The `analysisMode` state variable exists and is set on line 177.

Two existing usages: one for backend health (line 354-356), one for model health (line 357-364).

**What's missing:** There is no `HealthWarningBanner` conditional render for `analysisMode === 'rules_only'` in the results view. The existing i18n keys at `analyzer.modelUnavailable` and `analyzer.modelUnavailableLinkText` are for the pre-analysis banner (model offline before upload), not the post-analysis banner (LLM returned rules_only after running).

**Required changes:**
1. Add a new `HealthWarningBanner` render in the results section, conditional on `analysisMode === 'rules_only'`
2. Add new i18n keys: `analyzer.llmDownResults` (EN: `"Analysis service is temporarily unavailable. Browse the glossary for guidance."`) and `analyzer.llmDownResultsLink` (EN: `"Browse glossary"`)
3. Add Hebrew equivalents in `he.json`

**Note:** The existing pre-analysis `modelUnavailable` banner (lines 357-364) handles the case where the model is offline before analysis starts. The new banner handles the case where analysis ran but LLM failed. These are distinct scenarios and need distinct i18n keys.

### D-03: PDF Watermark — CURRENT WATERMARK IS DIAGONAL, NEEDS REPLACEMENT
**Current state:** `exportReport.ts` already has a watermark loop (lines 89-101) that iterates all pages and adds a diagonal `INCLUSIFY — Achva LGBT` watermark at 38pt bold with `angle: 45`. The `ExportOptions` interface has `locale?: string`.

**What needs to change:**
1. Replace the diagonal watermark block with a footer text watermark using locale-aware text
2. Add `returnBase64?: boolean` to `ExportOptions` interface
3. Change return type to `Promise<string | void>` — return `doc.output('datauristring')` when `returnBase64 === true`, else call `doc.save()` as before
4. `exportReport` callers in `analyze/page.tsx` (line 215) must still work without `returnBase64` (default false)

**Current watermark style to preserve/adapt:** The loop already calls `doc.setPage(i)` — the new footer text goes inside this same loop. Just change the content from diagonal text to footer text.

### D-04: Contact Us — EXISTING MAILTO SHORTCUT MUST BE REPLACED
**Current state:** `analyze/page.tsx` has a `handleContactUs` function (lines 218-232) and a `<button>` that calls it (line 516-522). The current implementation builds a `mailto:` link and sets `window.location.href` — no modal, no backend, no attachment. The button is labeled `{t('contactUs')}` (key exists: `"Contact Us"`).

**What needs to change (frontend):**
1. Remove `handleContactUs` function
2. Build `ContactModal.tsx` (new component, follow `ProfileSetupModal.tsx` structure)
3. Add state `const [contactOpen, setContactOpen] = useState(false)` in analyze page
4. Replace `onClick={handleContactUs}` with `onClick={() => setContactOpen(true)}`
5. Render `<ContactModal open={contactOpen} onClose={() => setContactOpen(false)} analysis={viewState === 'results' ? analysis : null} fileName={fileName} />`
6. The Contact button must also exist in `Navbar.tsx` (always visible). Current `Navbar.tsx` has no Contact button — add it.
7. `exportReport.ts` must gain a `returnBase64` mode before ContactModal can attach PDFs

**What needs to change (backend):**
1. New module `backend/app/modules/contact/router.py` with `POST /api/v1/contact`
2. Register in `backend/app/main.py`: `app.include_router(contact_router.router, prefix="/api/v1/contact", tags=["Contact"])`
3. No new Python dependencies

**New API contract:**
```
POST /api/v1/contact
Content-Type: multipart/form-data
Fields: subject (str), message (str), sender_name (str), sender_email (str), sender_institution (str | null)
File (optional): pdf_attachment (bytes)
Response: { "status": "sent" } or 500
Auth: optional (guests can also contact)
```

### D-05: Admin Frequency Trends — NOTHING EXISTS, FULL BUILD REQUIRED
**Current state:** No `get_label_frequency_trends` query in `admin/queries.py`. No `/api/v1/admin/frequency-trends` endpoint. No `/api/v1/admin/ws` WebSocket endpoint. No `AdminWSManager` class. No `FrequencyTrendsTab` or `SimpleBarChart` component. No `useAdminFrequencyTrends` SWR hook.

**Database:** `findings.category` and `findings.excerpt_redacted` exist in `db/schema.sql`. The query joins `findings` → `analysis_runs` (via `run_id`) for date filtering. No schema changes needed.

**WebSocket integration point:** After `_persist_results()` succeeds in `analysis/router.py`, the router must call `ws_manager.broadcast({event: "new_analysis"})`. The `ws_manager` instance must be importable from `admin/router.py` or placed in a shared module.

**Frontend WebSocket pattern:** The admin dashboard is a `'use client'` component. The WebSocket must be created in a `useEffect` with cleanup on unmount. Token for auth must come from `localStorage.getItem('auth_token')` (same pattern as `fetchWithAuth` in `client.ts`).

---

## Common Pitfalls

### Pitfall 1: FastAPI WebSocket CORS Is Not Covered by CORSMiddleware
**What goes wrong:** Browser WebSocket connections from `http://localhost:3000` to `ws://localhost:8000` are not subject to the `CORSMiddleware` you already have configured. The browser does not send a preflight for WebSocket — instead it sends an `Origin` header in the upgrade request. Most configurations simply accept any origin.
**Why it happens:** `CORSMiddleware` only handles HTTP requests; the WebSocket protocol upgrade bypasses it.
**How to avoid:** Rely entirely on JWT verification in the WebSocket handshake (the `token` query param + manual `jwt.decode`). This is sufficient for security.
**Warning signs:** If you see the WebSocket connect but subsequent messages are rejected, check whether the token is being passed correctly as a query param.

### Pitfall 2: sessionStorage vs. Profile Completion — Race Condition on Login
**What goes wrong:** The `DISMISSED_KEY` is set when the user clicks "Skip". If the user fills in all 3 fields and the popup closes via `setOpen(false)` (not `dismiss()`), the sessionStorage key is NOT set. On the same session, if `refreshProfile()` causes a re-render, the popup reopens because `dismissed === null` and the fields are now filled — but the `useEffect` checks fields first, not dismissal.
**Why it happens:** The current `onSubmit` calls `setOpen(false)` directly (line 59), not `dismiss()`. After a successful save, `refreshProfile()` runs and triggers the `useEffect` again.
**How to avoid:** On successful submit, call `dismiss()` (which sets the sessionStorage key) instead of `setOpen(false)`. The `dismiss()` function already sets the key and closes. Current code is correct for the skip path but wrong for the success path.

### Pitfall 3: jsPDF `getNumberOfPages()` Must Be Called After All Content Is Written
**What goes wrong:** If `getNumberOfPages()` is called before `autoTable` renders, it returns 1 even if the table will span multiple pages.
**Why it happens:** `autoTable` lazily creates pages during rendering. The page count is not known until `autoTable` has finished.
**How to avoid:** The existing `exportReport.ts` correctly calls the watermark loop after `autoTable` — maintain this order.

### Pitfall 4: smtplib SMTP.starttls() Required for Gmail Port 587
**What goes wrong:** If `SMTP_PORT=587` and you do not call `server.starttls()`, the connection is rejected by Gmail. If `SMTP_PORT=465` (SSL), you must use `smtplib.SMTP_SSL` instead of `smtplib.SMTP`.
**How to avoid:** Default to port 587 + `starttls()`. Document this in the env var comment.

### Pitfall 5: Contact Modal PDF Attachment — Base64 Data URI vs Raw Bytes
**What goes wrong:** jsPDF `doc.output('datauristring')` returns `data:application/pdf;base64,JVBERi0x...`. When sending as a file attachment to the backend, you must strip the `data:application/pdf;base64,` prefix and decode to bytes on the backend, or send it as a proper multipart file blob from the browser.
**How to avoid:** Use `doc.output('arraybuffer')` on the browser side and send as a `Blob` in `FormData`. This avoids base64 string handling entirely. Alternatively use `doc.output('datauristring')`, slice the prefix, and let the backend call `base64.b64decode()`.

### Pitfall 6: Admin WebSocket Token Expiry
**What goes wrong:** If the admin dashboard is left open for 30+ days (the token expiry), the WebSocket will be open but the token has expired. The `receive_text()` loop will still be alive because the WebSocket itself doesn't expire.
**How to avoid:** Add a ping/pong interval on the backend, or simply close + reconnect on auth error from the HTTP side. For this phase, documenting the limitation is sufficient — token expiry is 30 days and admin sessions are short.

---

## Code Examples

### Add required field to Zod schema (D-01)
```typescript
// Source: frontend/components/ProfileSetupModal.tsx — current schema (to update)
// BEFORE:
profession: z.string().max(200).optional().or(z.literal('')),
institution: z.string().max(200).optional().or(z.literal('')),
// AFTER (D-01c):
profession: z.string().min(1, 'required').max(200),
institution: z.string().min(1, 'required').max(200),
```

### Update profile completion check (D-01)
```typescript
// Source: frontend/components/ProfileSetupModal.tsx line 37 — to update
// BEFORE:
if (!dismissed && !user.full_name) {
// AFTER (D-01b):
if (!dismissed && (!user.full_name || !user.institution || !user.profession)) {
```

### LLM-down banner in results view (D-02)
```typescript
// In analyze/page.tsx results section, after the results header div (around line 530)
// Source: pattern from existing HealthWarningBanner usages on lines 354-364
{viewState === 'results' && analysisMode === 'rules_only' && (
  <HealthWarningBanner
    message={t('llmDownResults')}
    variant="error"
    linkHref={`/${locale}/glossary`}
    linkText={t('llmDownResultsLink')}
  />
)}
```

### exportReport base64 mode (D-03 / D-04)
```typescript
// Source: frontend/lib/exportReport.ts — signature update
interface ExportOptions {
  fileName: string;
  locale?: string;
  returnBase64?: boolean;  // ADD
}

export async function exportReport(
  analysis: AnalysisData,
  options: ExportOptions
): Promise<string | void> {   // RETURN TYPE UPDATE
  // ... existing code ...

  // Replace diagonal watermark loop with footer watermark:
  const watermarkText = options.locale === 'he'
    ? 'ארגון אחווה להט״ב הסטודנטיאלי'
    : 'Achva LGBTQ+ Studential Organization';
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);
    doc.setFontSize(8);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(150, 150, 150);
    doc.text(watermarkText, pageWidth / 2, pageHeight - 8, { align: 'center' });
  }

  if (options.returnBase64) {
    return doc.output('datauristring');  // returns 'data:application/pdf;base64,...'
  }
  const safeFileName = (options.fileName || 'analysis').replace(/[^a-z0-9_\-]/gi, '_');
  doc.save(`${safeFileName}_inclusify_report.pdf`);
}
```

### Frequency trends SQL query (D-05)
```python
# Source: pattern from backend/app/modules/admin/queries.py
# findings.category and findings.excerpt_redacted verified in db/schema.sql lines 138-155
async def get_label_frequency_trends(conn: asyncpg.Connection, days: int) -> list[dict]:
    cutoff = datetime.utcnow() - timedelta(days=days)
    rows = await conn.fetch("""
        SELECT f.category, COUNT(*) AS total_count,
               ARRAY_AGG(f.excerpt_redacted) AS all_excerpts
        FROM findings f
        JOIN analysis_runs ar ON f.run_id = ar.run_id
        WHERE ar.started_at >= $1
          AND f.excerpt_redacted IS NOT NULL
        GROUP BY f.category
        ORDER BY total_count DESC
    """, cutoff)
    from collections import Counter
    result = []
    for row in rows:
        phrase_counts = Counter(row['all_excerpts'])
        top5 = [{'phrase': p, 'count': c} for p, c in phrase_counts.most_common(5)]
        result.append({
            'category': row['category'],
            'count': int(row['total_count']),
            'top_phrases': top5,
        })
    return result
```

### Register new routes in main.py (D-04, D-05)
```python
# Source: backend/app/main.py (existing pattern, lines 115-118)
# D-04: add in main.py
from app.modules.contact import router as contact_router
app.include_router(contact_router.router, prefix="/api/v1/contact", tags=["Contact"])

# D-05: admin WebSocket is added to the existing admin router — no new include needed
# Just add @router.websocket("/ws") to backend/app/modules/admin/router.py
```

### Admin i18n additions needed in en.json
```json
// Add to "admin" section:
"frequencyTrends": {
  "title": "Label Frequency Trends",
  "subtitle": "Most flagged categories in the selected period",
  "topPhrases": "Top phrases",
  "noData": "No findings recorded in this period."
}
// Add to "analyzer" section:
"llmDownResults": "Analysis service is temporarily unavailable. Browse the glossary for guidance.",
"llmDownResultsLink": "Browse glossary"
// Add to "contact" section (new top-level key):
"contact": {
  "button": "Contact Us",
  "title": "Contact Us",
  "subtitle": "Send a message or feedback to the Inclusify team.",
  "subject": "Subject",
  "message": "Message",
  "send": "Send",
  "sending": "Sending...",
  "success": "Message sent!",
  "error": "Failed to send. Please try again.",
  "attachReport": "Analysis report attached",
  "nameLabel": "Name",
  "emailLabel": "Email",
  "institutionLabel": "Institution"
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Rule-based detection | LLM-only (hybrid_detector.py is already LLM-only) | Phase 7 | analysis_mode='rules_only' means LLM down, not a hybrid mode |
| Diagonal watermark | Footer watermark (D-03) | Phase 8 | Replace existing loop in exportReport.ts |
| mailto: Contact Us shortcut | Modal + smtplib backend (D-04) | Phase 8 | Remove handleContactUs from analyze/page.tsx |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | smtplib `starttls()` pattern works with Gmail App Password | Code Examples (D-04) | Could require `SMTP_SSL` on port 465 instead; clarify env var documentation |
| A2 | `doc.output('datauristring')` returns a data URI prefix that must be stripped before base64 decode in Python | Code Examples (D-03/D-04) | Using `output('arraybuffer')` + Blob in FormData avoids this entirely — either approach works |
| A3 | AdminWSManager can be a module-level singleton in admin/router.py without state sharing issues | Architecture (D-05) | If multiple workers run (e.g., uvicorn --workers 4), each worker has its own manager — WebSocket broadcast only reaches connections on the same worker process; acceptable for this phase |
| A4 | FrequencyTrendsTab will be added as a new section within OverviewTab (not a new tab) | Architecture (D-05) | If it needs to be a new tab, AdminDashboard.tsx TabKey type and tab bar must be extended |

---

## Open Questions (RESOLVED)

1. **Contact Us button placement in Navbar vs. analyze page only**
   - What we know: CONTEXT.md D-04a says "button lives in the navigation bar (always visible, all pages)". The analyze page currently has a Contact Us button in the results header.
   - What's unclear: Should both placements coexist? Or should the analyze-page button be removed once Navbar has the button?
   - Recommendation: Keep both — navbar button is always visible; analyze-page button remains in the results header with pre-attached report context.
   - **RESOLVED:** Keep both placements — navbar button is always visible across every page; the analyze-page button remains in the results header and pre-attaches the generated report context to the ContactModal.

2. **WebSocket auth: what happens if admin token expires while dashboard is open?**
   - What we know: Token lifetime is 30 days. WS close code 4001 = unauthorized.
   - What's unclear: Should the frontend auto-reconnect silently or show an error?
   - Recommendation: On `code === 4001` in `onclose`, redirect to login (follow existing `fetchWithAuth` behavior).
   - **RESOLVED:** On `code === 4001` in `ws.onclose`, redirect to login — mirroring the existing `fetchWithAuth` 401 behavior. Frontend implements `ws.onclose = (e) => { if (e.code === 4001) router.push('/login') }` (or equivalent `window.location.href` redirect with locale prefix).

3. **FrequencyTrendsTab placement: new card below KPIs in OverviewTab, or new admin tab?**
   - What we know: CONTEXT.md D-05a says "new section to the admin dashboard." D-05c mentions expandable dropdowns.
   - What's unclear: Whether "section" means inside OverviewTab or a new top-level tab.
   - Recommendation: New card below the recent activity section within OverviewTab. This avoids changes to the tab bar and is consistent with "section."
   - **RESOLVED:** New card below the recent activity section within OverviewTab. No tab-bar changes; consistent with the CONTEXT "section" wording.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | smtplib (D-04) | ✓ | 3.x (verified) | — |
| Node.js | Frontend build | ✓ | v24.6.0 | — |
| jsPDF 4.2.1 | PDF watermark (D-03) | ✓ | 4.2.1 | — |
| jspdf-autotable | PDF table | ✓ | 5.0.7 | — |
| @radix-ui/react-dialog | ContactModal (D-04) | ✓ | 1.1.15 | — |
| SMTP credentials | Contact email (D-04) | ✗ (not in repo) | — | Must be in `.env` before D-04 runs |
| FastAPI WebSocket | Admin WS (D-05) | ✓ | stdlib in fastapi | — |

**Missing dependencies with no fallback:**
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` environment variables — must be configured before D-04 plan executes. The plan should include an env var documentation task.

---

## Validation Architecture

> nyquist_validation not explicitly disabled; section included per default.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | jest (frontend), pytest (backend) |
| Config file | frontend/jest.config.js |
| Quick run command | `cd frontend && npm test -- --testPathPattern=ProfileSetupModal` |
| Full suite command | `cd frontend && npm test` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| D-01 | Popup opens when institution or profession is null | unit | `npm test -- --testPathPattern=ProfileSetupModal` | ❌ Wave 0 |
| D-01 | Zod schema rejects empty institution | unit | `npm test -- --testPathPattern=ProfileSetupModal` | ❌ Wave 0 |
| D-02 | HealthWarningBanner renders when analysisMode=rules_only | unit | `npm test -- --testPathPattern=analyze` | ❌ Wave 0 |
| D-03 | exportReport returns string when returnBase64=true | unit | `npm test -- --testPathPattern=exportReport` | ❌ Wave 0 |
| D-04 | POST /api/v1/contact returns 200 with valid form data | integration | `cd backend && pytest tests/test_contact.py -x` | ❌ Wave 0 |
| D-05 | get_label_frequency_trends returns expected shape | unit | `cd backend && pytest tests/test_admin_queries.py::test_frequency_trends -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd frontend && npm test -- --testPathPattern=<changed-file>`
- **Per wave merge:** `cd frontend && npm test && cd ../backend && pytest`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `frontend/__tests__/ProfileSetupModal.test.tsx` — covers D-01
- [ ] `frontend/__tests__/exportReport.test.ts` — covers D-03
- [ ] `backend/tests/test_contact.py` — covers D-04
- [ ] `backend/tests/test_admin_queries.py` — covers D-05 query

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | JWT in WebSocket handshake — manual decode required (D-05) |
| V3 Session Management | no | — |
| V4 Access Control | yes | `require_admin` Depends on HTTP endpoints; manual role check in WebSocket (D-05) |
| V5 Input Validation | yes | Zod (frontend forms), Pydantic (backend contact endpoint) |
| V6 Cryptography | no | No new crypto |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| WebSocket without auth | Elevation of Privilege | Manual JWT decode in WS handshake, close with code 4001/4003 |
| SMTP credentials in env | Information Disclosure | Store in `.env` / Azure Key Vault, never commit to git |
| PDF base64 in POST body | Tampering | Validate MIME type server-side; limit size (e.g., 5MB) |
| Contact form spam | Denial of Service | Rate limit the `/api/v1/contact` endpoint (simple: 5 req/min per IP using starlette middleware) |
| Unvalidated email recipients | Spoofing | Recipients are always queried from DB (`WHERE role='site_admin'`) — never user-supplied |

---

## Sources

### Primary (HIGH confidence)
- Codebase direct read — `frontend/components/ProfileSetupModal.tsx`, `HealthWarningBanner.tsx`, `exportReport.ts`, `analyze/page.tsx`, `admin/queries.py`, `admin/router.py`, `admin/schemas.py`, `hybrid_detector.py`, `main.py`, `layout.tsx`, `Navbar.tsx`, `package.json`, `db/schema.sql`
- All code patterns and file paths verified by direct file inspection in this session

### Secondary (MEDIUM confidence)
- [CITED: FastAPI WebSocket docs](https://fastapi.tiangolo.com/advanced/websockets/) — WebSocket endpoint pattern, manual auth approach
- [CITED: jsPDF output modes](https://rawgit.com/MrRio/jsPDF/master/docs/jsPDF.html) — `output('datauristring')` return value format

### Tertiary (LOW confidence — flagged in Assumptions Log)
- smtplib Gmail App Password `starttls()` pattern — standard Python docs, marked [ASSUMED] for exact port/SSL mode

---

## Metadata

**Confidence breakdown:**
- D-already (1-5): HIGH — confirmed by direct code inspection
- D-01 Profile popup: HIGH — file exists, bugs identified precisely
- D-02 LLM-down banner: HIGH — component exists, missing conditional render identified
- D-03 PDF watermark: HIGH — existing loop confirmed, replacement pattern clear
- D-04 Contact Us: HIGH (frontend structure), MEDIUM (smtplib port/SSL details — see A1)
- D-05 Admin trends: HIGH (SQL pattern), MEDIUM (WebSocket multi-worker caveat — see A3)

**Research date:** 2026-04-18
**Valid until:** 2026-05-18 (stable stack — no fast-moving dependencies)
