# Phase 8: Achva Feedback - Pattern Map

**Mapped:** 2026-04-18
**Files analyzed:** 18 new/modified files
**Analogs found:** 17 / 18

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `frontend/components/ProfileSetupModal.tsx` | component (modal) | request-response | self (already exists) | self |
| `frontend/components/ContactModal.tsx` | component (modal) | request-response | `frontend/components/ProfileSetupModal.tsx` | exact |
| `frontend/lib/api/contact.ts` | utility (api client) | request-response | `frontend/lib/api/auth.ts` | role-match |
| `frontend/lib/api/admin.ts` | utility (SWR hooks) | request-response | self (already exists) | self |
| `frontend/lib/exportReport.ts` | utility | transform | self (already exists) | self |
| `frontend/app/[locale]/analyze/page.tsx` | component (page) | request-response | self (already exists) | self |
| `frontend/app/[locale]/layout.tsx` | config/layout | — | self (already exists) | self |
| `frontend/components/dashboard/SimpleBarChart.tsx` | component (chart) | transform | `frontend/components/dashboard/SimpleLineChart.tsx` | exact |
| `frontend/components/dashboard/FrequencyTrendsTab.tsx` | component (tab) | request-response | `frontend/components/dashboard/OverviewTab.tsx` | exact |
| `frontend/messages/en.json` | config (i18n) | — | self (already exists) | self |
| `frontend/messages/he.json` | config (i18n) | — | self (already exists) | self |
| `backend/app/modules/contact/__init__.py` | config (module) | — | `backend/app/modules/profile/__init__.py` | exact |
| `backend/app/modules/contact/router.py` | controller (router) | request-response | `backend/app/modules/profile/router.py` | role-match |
| `backend/app/modules/admin/router.py` | controller (router) | event-driven (WS) | self + FastAPI WS docs | partial |
| `backend/app/modules/admin/queries.py` | service (data) | CRUD | self (already exists) | self |
| `backend/app/modules/admin/schemas.py` | model (Pydantic) | — | self (already exists) | self |
| `backend/app/main.py` | config | — | self (already exists) | self |
| `frontend/components/HealthWarningBanner.tsx` | component (banner) | — | self (verify only) | self |

---

## Pattern Assignments

### `frontend/components/ContactModal.tsx` (component, request-response)

**Analog:** `frontend/components/ProfileSetupModal.tsx`

**Imports pattern** (lines 1-13 of ProfileSetupModal.tsx):
```typescript
'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useTranslations } from 'next-intl';
import { toast } from 'sonner';
import * as Dialog from '@radix-ui/react-dialog';
import { X } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
```

**Zod schema pattern** (lines 16-20 of ProfileSetupModal.tsx — apply same required-field approach):
```typescript
const schema = z.object({
  subject: z.string().min(1, 'required').max(300),
  message: z.string().min(1, 'required').max(5000),
  // read-only prefill fields come from AuthContext, not from form schema
});
```

**Dialog shell pattern** (lines 68-72 of ProfileSetupModal.tsx):
```typescript
return (
  <Dialog.Root open={open} onOpenChange={(v) => { if (!v) onClose(); }}>
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

**Submit + toast pattern** (lines 47-65 of ProfileSetupModal.tsx):
```typescript
const onSubmit = async (data: FormData) => {
  setIsSubmitting(true);
  try {
    await sendContactMessage({ ...data, senderName: user?.full_name, senderEmail: user?.email, ... });
    toast.success(t('success'));
    onClose();
  } catch {
    toast.error(t('error'));
  } finally {
    setIsSubmitting(false);
  }
};
```

**Read-only prefill field pattern** (adapt from input pattern at lines 98-106):
```typescript
// Read-only fields: render as static text, not editable inputs
<div>
  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
    {t('nameLabel')}
  </label>
  <p className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-500 dark:text-slate-400 text-sm">
    {user?.full_name || '—'}
  </p>
</div>
```

**Submit button pattern** (lines 132-138 of ProfileSetupModal.tsx):
```typescript
<button
  type="submit"
  disabled={isSubmitting}
  className="btn-primary flex-1 disabled:opacity-50 disabled:cursor-not-allowed"
>
  {isSubmitting ? t('sending') : t('send')}
</button>
```

---

### `frontend/lib/api/contact.ts` (utility, request-response)

**Analog:** `frontend/lib/api/auth.ts`

**Module setup pattern** (lines 1, 6 of auth.ts):
```typescript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
```

**Multipart POST pattern** (adapt from `uploadFile` in `frontend/lib/api/client.ts` lines 261-288):
```typescript
export async function sendContactMessage(params: {
  subject: string;
  message: string;
  senderName: string | null;
  senderEmail: string | null;
  senderInstitution: string | null;
  pdfBlob?: Blob;
}): Promise<void> {
  const formData = new FormData();
  formData.append('subject', params.subject);
  formData.append('message', params.message);
  if (params.senderName) formData.append('sender_name', params.senderName);
  if (params.senderEmail) formData.append('sender_email', params.senderEmail);
  if (params.senderInstitution) formData.append('sender_institution', params.senderInstitution);
  if (params.pdfBlob) formData.append('pdf_attachment', params.pdfBlob, 'analysis_report.pdf');

  const response = await fetch(`${API_BASE_URL}/api/v1/contact`, {
    method: 'POST',
    body: formData,
    // No Content-Type header — browser sets multipart boundary automatically
  });

  if (!response.ok) {
    throw new Error(`Contact failed: ${response.status}`);
  }
}
```

**Note:** Contact endpoint is auth-optional (guests can contact). Do NOT use `fetchWithAuth` — use plain `fetch` so unauthenticated users can also submit.

---

### `frontend/lib/api/admin.ts` — add `useAdminFrequencyTrends` hook

**Analog:** existing hooks in `frontend/lib/api/admin.ts` lines 57-92

**SWR hook pattern** (lines 57-63 of admin.ts — exact pattern to copy):
```typescript
export function useAdminFrequencyTrends(days: number) {
  const { data, error, isLoading, mutate } = useSWR<FrequencyTrendsResponse>(
    `${API_BASE_URL}/api/v1/admin/frequency-trends?days=${days}`,
    fetcher,
    { revalidateOnFocus: false, dedupingInterval: 60000 }
  );
  return { data, isLoading, error, refresh: mutate };
}
```

**Interface pattern** (lines 6-45 of admin.ts — add adjacent to existing interfaces):
```typescript
export interface FrequencyTrendItem {
  category: string;
  count: number;
  top_phrases: Array<{ phrase: string; count: number }>;
}

export interface FrequencyTrendsResponse {
  trends: FrequencyTrendItem[];
  days: number;
}
```

---

### `frontend/components/dashboard/SimpleBarChart.tsx` (component, transform)

**Analog:** `frontend/components/dashboard/SimpleLineChart.tsx` (lines 1-80)

**File header + props pattern** (lines 1-18 of SimpleLineChart.tsx):
```typescript
'use client';

import { useMemo } from 'react';

export default function SimpleBarChart({
  data,
  labels,
  color = '#7b61ff',
  height = 200,
}: {
  data: number[];
  labels: string[];
  color?: string;
  height?: number;
}) {
```

**SVG coordinate system pattern** (lines 20-48 of SimpleLineChart.tsx — adapt for bars):
```typescript
const { bars, maxVal } = useMemo(() => {
  if (data.length === 0) return { bars: [], maxVal: 1 };
  const maxVal = Math.max(...data) || 1;
  const width = 800;
  const barWidth = (width / data.length) * 0.6;
  const gap = (width / data.length) * 0.4;
  const bars = data.map((v, i) => ({
    x: i * (barWidth + gap) + gap / 2,
    y: height - 24 - ((v / maxVal) * (height - 40)),
    barHeight: (v / maxVal) * (height - 40),
    barWidth,
    value: v,
  }));
  return { bars, maxVal };
}, [data, height]);
```

**SVG render pattern** (lines 50-78 of SimpleLineChart.tsx — adapt rects for bars):
```typescript
return (
  <div className="w-full overflow-hidden">
    <svg viewBox={`0 0 800 ${height}`} className="w-full h-auto">
      {bars.map((b, i) => (
        <g key={i}>
          <rect x={b.x} y={b.y} width={b.barWidth} height={b.barHeight}
            fill={color} rx="4" opacity="0.85" />
          <text x={b.x + b.barWidth / 2} y={height - 6}
            textAnchor="middle" fontSize="11" fill="currentColor" opacity="0.5">
            {labels[i]}
          </text>
        </g>
      ))}
    </svg>
  </div>
);
```

---

### `frontend/components/dashboard/FrequencyTrendsTab.tsx` (component, request-response)

**Analog:** `frontend/components/dashboard/OverviewTab.tsx`

**Imports pattern** (lines 1-14 of OverviewTab.tsx):
```typescript
'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { BarChart3 } from 'lucide-react';
import { useAdminFrequencyTrends } from '@/lib/api/admin';
import SimpleBarChart from './SimpleBarChart';
```

**Props interface pattern** (lines 16-33 of OverviewTab.tsx — translate to FrequencyTrends):
```typescript
interface FrequencyTrendsTabProps {
  days: number;
  translations: {
    title: string;
    subtitle: string;
    topPhrases: string;
    noData: string;
  };
}
```

**Loading / error / empty state pattern** (lines 155-173 of OverviewTab.tsx):
```typescript
{isLoading ? (
  <div className="space-y-3">
    {[1, 2, 3].map((i) => (
      <div key={i} className="animate-pulse bg-slate-200 dark:bg-slate-700 rounded h-8" />
    ))}
  </div>
) : error ? (
  <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg text-red-600 dark:text-red-400 text-sm">
    Failed to load trends. Please try again.
  </div>
) : !data?.trends.length ? (
  <div className="p-8 text-center text-slate-500 dark:text-slate-400">
    {translations.noData}
  </div>
) : (
  // chart + dropdown content
)}
```

**Card wrapper pattern** (lines 142-151 of OverviewTab.tsx):
```typescript
<div className="rounded-2xl border bg-white dark:bg-slate-900 p-5 shadow-sm">
  <div className="flex items-center justify-between mb-4">
    <div>
      <h3 className="font-semibold text-slate-800 dark:text-white flex items-center gap-2">
        <BarChart3 className="w-4 h-4 text-pride-purple" />
        {translations.title}
      </h3>
      <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
        {translations.subtitle}
      </p>
    </div>
  </div>
  {/* chart content */}
</div>
```

**WebSocket effect pattern** (to add in the component that mounts FrequencyTrendsTab — AdminDashboard or OverviewTab):
```typescript
useEffect(() => {
  const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
  if (!token) return;

  const wsUrl = `${WS_BASE_URL}/api/v1/admin/ws?token=${token}`;
  const ws = new WebSocket(wsUrl);

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      if (msg.event === 'new_analysis') {
        refreshTrends();  // mutate() from useAdminFrequencyTrends
      }
    } catch { /* ignore malformed messages */ }
  };

  ws.onclose = (event) => {
    if (event.code === 4001) {
      // Token expired — redirect to login (same pattern as fetchWithAuth)
      window.location.href = `/${locale}/login`;
    }
  };

  return () => ws.close();
}, [locale]);
```

---

### `backend/app/modules/contact/router.py` (controller, request-response)

**Analog:** `backend/app/modules/profile/router.py`

**Module header + imports pattern** (lines 1-8 of profile/router.py):
```python
"""Contact form router — sends email to site admins via smtplib.

No auth required: both authenticated and guest users may contact.
SMTP config: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD env vars.
"""
import os
import smtplib
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status

router = APIRouter()
```

**DB pool guard pattern** (lines 12-15 of profile/router.py):
```python
def _pool(request: Request):
    if not getattr(request.app.state, "db_pool", None):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not available")
    return request.app.state.db_pool
```

**Endpoint signature pattern** (adapt lines 18-32 of profile/router.py for multipart POST):
```python
@router.post("", status_code=200)
async def send_contact(
    request: Request,
    subject: str = Form(...),
    message: str = Form(...),
    sender_name: str = Form(default=""),
    sender_email: str = Form(default=""),
    sender_institution: str = Form(default=""),
    pdf_attachment: UploadFile | None = File(default=None),
):
    pool = _pool(request)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT email FROM users WHERE role = 'site_admin'"
        )
    admin_emails = [r["email"] for r in rows]
    if not admin_emails:
        raise HTTPException(status_code=500, detail="No admin recipients configured")
    # ... send email ...
    return {"status": "sent"}
```

**smtplib send pattern** (stdlib — no analog in codebase, from RESEARCH.md):
```python
msg = MIMEMultipart()
msg['From'] = os.getenv('SMTP_USER')
msg['To'] = ', '.join(admin_emails)
msg['Subject'] = f"[Inclusify Contact] {subject}"
body_text = f"From: {sender_name} <{sender_email}>\nInstitution: {sender_institution}\n\n{message}"
msg.attach(MIMEText(body_text, 'plain'))

if pdf_attachment:
    pdf_bytes = await pdf_attachment.read()
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

---

### `backend/app/modules/admin/router.py` — add WebSocket endpoint

**Analog:** existing `backend/app/modules/admin/router.py` (lines 1-102) + FastAPI WebSocket pattern

**Import additions** (add to existing imports at lines 7-17):
```python
from fastapi import WebSocket, WebSocketDisconnect
from jose import jwt, JWTError
from app.core.config import settings  # or however JWT_SECRET is accessed
```

**AdminWSManager class** (add as module-level singleton before `router = APIRouter()`):
```python
class AdminWSManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.connections:
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
```

**WebSocket endpoint pattern** (add after existing HTTP routes):
```python
@router.websocket("/ws")
async def admin_ws(websocket: WebSocket, token: str = None):
    # Manual JWT auth — Depends() does not work in WebSocket handlers
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"],
                             audience="fastapi-users:auth")
        if payload.get("role") != "site_admin":
            await websocket.close(code=4003)
            return
    except (JWTError, Exception):
        await websocket.close(code=4001)
        return
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep-alive; messages from client are ignored
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
```

**Existing HTTP endpoint pattern to follow** (lines 32-41 of admin/router.py):
```python
@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    request: Request,
    user: dict = Depends(require_admin),
    days: int = Query(default=30, ge=1, le=365, description="Time range in days")
):
    pool = _verify_db_pool(request)
    async with pool.acquire() as conn:
        return await queries.get_analytics_kpis(conn, days)
```

**New HTTP endpoint for trends** (follow same pattern):
```python
@router.get("/frequency-trends", response_model=FrequencyTrendsResponse)
async def get_frequency_trends(
    request: Request,
    user: dict = Depends(require_admin),
    days: int = Query(default=30, ge=1, le=365, description="Time range in days")
):
    pool = _verify_db_pool(request)
    async with pool.acquire() as conn:
        trends = await queries.get_label_frequency_trends(conn, days)
    return {"trends": trends, "days": days}
```

---

### `backend/app/modules/admin/queries.py` — add `get_label_frequency_trends`

**Analog:** existing functions in `backend/app/modules/admin/queries.py`

**Function signature pattern** (lines 14-28 of queries.py):
```python
async def get_label_frequency_trends(conn: asyncpg.Connection, days: int) -> list[dict]:
    """Fetch label frequency trends for admin dashboard.

    Args:
        conn: asyncpg database connection
        days: Time range in days

    Returns:
        list of dicts with keys: category (str), count (int), top_phrases (list[dict])
    """
    from datetime import datetime, timedelta
    from collections import Counter
    cutoff = datetime.utcnow() - timedelta(days=days)
```

**asyncpg fetch pattern** (lines 34-51 of queries.py):
```python
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

---

### `backend/app/modules/admin/schemas.py` — add `FrequencyTrendsResponse`

**Analog:** existing schemas in `backend/app/modules/admin/schemas.py`

**Pydantic model pattern** (lines 18-30 of schemas.py):
```python
class TopPhrase(BaseModel):
    phrase: str
    count: int

class FrequencyTrendItem(BaseModel):
    category: str
    count: int
    top_phrases: list[TopPhrase]

class FrequencyTrendsResponse(BaseModel):
    trends: list[FrequencyTrendItem]
    days: int
```

**Import line** (existing at line 12-15 of schemas.py — already present):
```python
from pydantic import BaseModel
from typing import Optional
```

---

### `backend/app/main.py` — register contact router

**Analog:** lines 114-118 of `backend/app/main.py`

**Import pattern** (lines 13-19 of main.py):
```python
from app.modules.contact import router as contact_router
```

**Router registration pattern** (lines 115-118 of main.py):
```python
app.include_router(contact_router.router, prefix="/api/v1/contact", tags=["Contact"])
```

---

### `frontend/components/ProfileSetupModal.tsx` — field fixes (D-01)

**Self-analog. Changes are surgical patches:**

**Zod schema fix** (lines 16-20, CURRENT → TARGET):
```typescript
// CURRENT (lines 18-19):
profession: z.string().max(200).optional().or(z.literal('')),
institution: z.string().max(200).optional().or(z.literal('')),

// TARGET (D-01c):
profession: z.string().min(1, 'required').max(200),
institution: z.string().min(1, 'required').max(200),
```

**Completion check fix** (line 37, CURRENT → TARGET):
```typescript
// CURRENT:
if (!dismissed && !user.full_name) {
// TARGET (D-01b):
if (!dismissed && (!user.full_name || !user.institution || !user.profession)) {
```

**Label asterisk additions** (add to profession label at line 111, institution at line 121):
```typescript
{t('profession')} <span className="text-red-500">*</span>
{t('institution')} <span className="text-red-500">*</span>
```

**Submit success path fix** (line 59 — replace `setOpen(false)` with `dismiss()`):
```typescript
// CURRENT (line 59):
setOpen(false);
// TARGET (prevents re-open on refreshProfile re-render — see RESEARCH Pitfall 2):
dismiss();
```

---

### `frontend/lib/exportReport.ts` — watermark + base64 mode (D-03)

**Self-analog. Surgical changes to existing file (lines 1-106):**

**Interface update** (lines 15-18, add `returnBase64`):
```typescript
interface ExportOptions {
  fileName: string;
  locale?: string;
  returnBase64?: boolean;  // ADD: when true, return data URI string instead of triggering download
}
```

**Function return type update** (line 20):
```typescript
// CURRENT:
export async function exportReport(analysis: AnalysisData, options: ExportOptions): Promise<void>
// TARGET:
export async function exportReport(analysis: AnalysisData, options: ExportOptions): Promise<string | void>
```

**Watermark loop replacement** (lines 89-101, FULL REPLACEMENT):
```typescript
// REPLACE diagonal watermark block with footer watermark:
const totalPages: number = (doc as any).internal.getNumberOfPages();
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
```

**Save vs base64 branch** (lines 103-106, CURRENT → TARGET):
```typescript
// CURRENT (lines 103-105):
const safeFileName = (options.fileName || 'analysis').replace(/[^a-z0-9_\-]/gi, '_');
doc.save(`${safeFileName}_inclusify_report.pdf`);

// TARGET:
if (options.returnBase64) {
  return doc.output('datauristring');  // caller strips 'data:application/pdf;base64,' prefix
}
const safeFileName = (options.fileName || 'analysis').replace(/[^a-z0-9_\-]/gi, '_');
doc.save(`${safeFileName}_inclusify_report.pdf`);
```

**CRITICAL:** The existing caller at `analyze/page.tsx` line 215 calls `exportReport(analysis, { fileName, locale })` without `returnBase64` — this still works unchanged (returns void, triggers download).

---

### `frontend/app/[locale]/analyze/page.tsx` — D-02 banner + D-04 contact

**Self-analog. Two discrete changes:**

**LLM-down banner addition** (add in results section, after existing banner usages around line 354-364):
```typescript
{viewState === 'results' && analysisMode === 'rules_only' && (
  <HealthWarningBanner
    message={t('llmDownResults')}
    variant="error"
    linkHref={`/${locale}/glossary`}
    linkText={t('llmDownResultsLink')}
  />
)}
```

**Contact Us replacement** (lines 218-232 — remove `handleContactUs`, add modal state):
```typescript
// REMOVE handleContactUs function entirely (lines 218-232)

// ADD modal state (near other useState declarations, line 66-70 area):
const [contactOpen, setContactOpen] = useState(false);

// REPLACE onClick={handleContactUs} with:
onClick={() => setContactOpen(true)}

// ADD ContactModal render (near end of JSX, before closing tag):
<ContactModal
  open={contactOpen}
  onClose={() => setContactOpen(false)}
  analysis={viewState === 'results' ? analysis : null}
  fileName={fileName}
  locale={locale}
/>
```

---

### `frontend/messages/en.json` + `frontend/messages/he.json` — i18n additions

**Self-analog. Add keys following existing structure.**

**New keys for en.json** (add to corresponding sections):
```json
// In "analyzer" section — add alongside existing modelUnavailable keys:
"llmDownResults": "Analysis service is temporarily unavailable. Browse the glossary for guidance.",
"llmDownResultsLink": "Browse glossary",

// New top-level "contact" section:
"contact": {
  "button": "Contact Us",
  "title": "Contact Us",
  "subtitle": "Send a message or feedback to the Inclusify team.",
  "subject": "Subject",
  "message": "Message",
  "send": "Send",
  "sending": "Sending...",
  "success": "Message sent successfully.",
  "error": "Failed to send. Please try again.",
  "attachReport": "Analysis report will be attached",
  "nameLabel": "Name",
  "emailLabel": "Email",
  "institutionLabel": "Institution"
},

// In "admin" section — add new frequencyTrends object:
"frequencyTrends": {
  "title": "Label Frequency Trends",
  "subtitle": "Most flagged categories in the selected period",
  "topPhrases": "Top phrases",
  "noData": "No findings recorded in this period."
}
```

**Corresponding he.json additions** (follow existing Hebrew message style — RTL, no punctuation changes):
```json
"llmDownResults": "שירות הניתוח אינו זמין כרגע. עיין במילון המונחים לקבלת הנחיות.",
"llmDownResultsLink": "עיין במילון",

"contact": {
  "button": "צור קשר",
  "title": "צור קשר",
  "subtitle": "שלח הודעה או משוב לצוות Inclusify.",
  "subject": "נושא",
  "message": "הודעה",
  "send": "שלח",
  "sending": "שולח...",
  "success": "ההודעה נשלחה בהצלחה.",
  "error": "שליחה נכשלה. נסה שנית.",
  "attachReport": "דוח הניתוח יצורף",
  "nameLabel": "שם",
  "emailLabel": "אימייל",
  "institutionLabel": "מוסד"
},

"frequencyTrends": {
  "title": "מגמות תדירות תוויות",
  "subtitle": "הקטגוריות המסומנות ביותר בטווח הזמן הנבחר",
  "topPhrases": "ביטויים נפוצים",
  "noData": "לא נמצאו ממצאים בתקופה זו."
}
```

**Also add to en.json profile.setup section** (existing keys per CONTEXT.md D-01):
```json
"save": "Save",
"saving": "Saving...",
"skip": "Skip for now"
```

---

### `backend/app/modules/contact/__init__.py` (config, module init)

**Analog:** `backend/app/modules/profile/__init__.py`

```python
# Empty file — module marker, same pattern as all other modules
```

---

## Shared Patterns

### Authentication — fetchWithAuth
**Source:** `frontend/lib/api/client.ts` lines 9-47
**Apply to:** All authenticated frontend API calls (admin hooks use this via the `fetcher` function in admin.ts)
```typescript
// Token from localStorage (not useState initializer — avoids hydration crash)
const token = typeof window !== 'undefined'
  ? localStorage.getItem('auth_token')
  : null;
// Attach as Bearer header; 401 triggers toast + redirect
```

**NOT applied to:** `frontend/lib/api/contact.ts` — contact endpoint is auth-optional (guests can submit)

### DB Pool Guard
**Source:** `backend/app/modules/profile/router.py` lines 12-15
**Apply to:** All backend router files that need DB access (`contact/router.py`)
```python
def _pool(request: Request):
    if not getattr(request.app.state, "db_pool", None):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not available")
    return request.app.state.db_pool
```

### Toast Notifications
**Source:** `frontend/components/ProfileSetupModal.tsx` lines 8, 58, 61
**Apply to:** `ContactModal.tsx`
```typescript
import { toast } from 'sonner';
// success:
toast.success(t('success'));
// error:
toast.error(t('error'));
```

### Admin require_admin Depends
**Source:** `backend/app/modules/admin/router.py` lines 7-8, 34-36
**Apply to:** New HTTP `/api/v1/admin/frequency-trends` endpoint (NOT the WebSocket endpoint — manual JWT decode required there)
```python
from app.auth.deps import require_admin
user: dict = Depends(require_admin),
```

### i18n useTranslations
**Source:** `frontend/components/ProfileSetupModal.tsx` line 7
**Apply to:** `ContactModal.tsx`, `FrequencyTrendsTab.tsx`
```typescript
import { useTranslations } from 'next-intl';
const t = useTranslations('contact');   // for ContactModal
const t = useTranslations('admin');     // for FrequencyTrendsTab
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| smtplib email logic (inside contact/router.py) | service | event-driven | No email sending exists anywhere in the codebase. Pattern sourced from RESEARCH.md Pattern 6 (Python stdlib docs). |

---

## Critical Implementation Notes

1. **WebSocket auth is manual** — `Depends(require_admin)` does NOT work in `@router.websocket` handlers. Always decode JWT manually from `token` query param and close with code 4001/4003 on failure.

2. **exportReport callers are backward-compatible** — the new `returnBase64?: boolean` parameter is optional and defaults to undefined (falsy). Existing call at `analyze/page.tsx` line 215 works unchanged.

3. **ProfileSetupModal onSubmit success path** — change `setOpen(false)` to `dismiss()` to prevent modal re-opening when `refreshProfile()` triggers a `useEffect` re-run (RESEARCH Pitfall 2).

4. **Contact PDF attachment uses Blob/FormData** — use `doc.output('arraybuffer')` then `new Blob([buffer], {type:'application/pdf'})` in FormData to avoid base64 prefix stripping issues (RESEARCH Pitfall 5). Alternatively use `datauristring` and strip prefix server-side with `base64.b64decode(data_uri.split(',')[1])`.

5. **AdminWSManager is a module-level singleton** — with single-worker uvicorn (dev + this phase), all WS connections share one process. Multi-worker limitation is documented in RESEARCH.md A3 but acceptable for this phase.

6. **FrequencyTrendsTab placement** — new card appended inside `OverviewTab` (below activity table), not a new top-level tab. This avoids changes to AdminDashboard tab bar and `TabKey` type.

---

## Metadata

**Analog search scope:** `frontend/components/`, `frontend/lib/api/`, `frontend/components/dashboard/`, `backend/app/modules/`, `backend/app/main.py`
**Files read:** 17
**Pattern extraction date:** 2026-04-18
