# Coding Conventions

**Analysis Date:** 2026-03-09

## Naming Patterns

**Files:**
- React components: PascalCase (e.g., `AnalysisSummary.tsx`, `PaperUpload.tsx`, `HeroSection.tsx`)
- Utilities and services: camelCase (e.g., `demoData.ts`, `client.ts`, `utils.ts`)
- Configuration files: camelCase with `.config` suffix (e.g., `eslint.config.mjs`, `tsconfig.json`)
- Python modules: snake_case (e.g., `connection.py`, `repository.py`, `router.py`)
- Directory names: camelCase (e.g., `components/`, `lib/`, `modules/`)
- i18n files: lowercase with `.json` (e.g., `en.json`, `he.json`)

**Functions:**
- TypeScript/JavaScript: camelCase for all functions (e.g., `analyzeText()`, `findOccurrences()`, `handleFileSelect()`)
- Python: snake_case for all functions (e.g., `get_org_by_slug()`, `create_document()`, `find_issues()`)
- Event handlers: prefix with `handle` (e.g., `handleReset`, `handleFileSelect`, `handleDrop`)
- Async functions: named naturally without prefix (e.g., `async def get_conn()`, `async function analyzeText()`)

**Variables:**
- TypeScript/React: camelCase (e.g., `viewState`, `selectedAnnotation`, `isHebrew`)
- Constants: UPPER_CASE for static dictionaries (e.g., `TERM_RULES`, `API_BASE_URL`)
- Python: snake_case (e.g., `text_sha256`, `org_id`, `private_mode`)
- Boolean variables: prefix with `is`/`has`/`should` (e.g., `isHebrew`, `isExpanded`, `isDragging`)

**Types:**
- TypeScript interfaces: PascalCase (e.g., `Annotation`, `AnalysisResult`, `GlossaryTerm`)
- TypeScript type aliases: PascalCase (e.g., `Severity`, `ViewState`, `Locale`)
- Props types: ComponentName + `Props` suffix (e.g., `HeroSectionProps`, `PaperUploadProps`)
- Python Pydantic models: PascalCase (e.g., `AnalysisRequest`, `AnalysisResponse`, `Issue`)

## Code Style

**Formatting:**
- Indentation: 2 spaces (TypeScript/TSX), 4 spaces (Python)
- Quotes: Single quotes in TypeScript, double quotes in Python
- Semicolons: Not enforced (most files omit)
- Max line length: ~100 characters observed
- Trailing commas: Used in arrays and objects

**Linting:**
- ESLint: `eslint-config-next/core-web-vitals` and `eslint-config-next/typescript`
- Config: `frontend/eslint.config.mjs` (ESLint v9 flat config)
- Run: `cd frontend && npm run lint`
- Python: No linting config detected (no Black, Ruff, or Flake8)

**TypeScript Settings:**
- Strict mode enabled
- Path alias: `@/*` maps to frontend root
- Target: ES2017
- Module: ESNext with bundler resolution

## Import Organization

**Order (TypeScript):**
1. React/Next.js core imports
2. External library imports (framer-motion, lucide-react, next-intl)
3. Internal imports using `@/` alias
4. Relative imports from same directory
5. Type imports (inline with regular imports)

**Example:**
```typescript
'use client';

import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslations, useLocale } from 'next-intl';
import { cn } from '@/lib/utils';
import SeverityBadge from './SeverityBadge';
import type { Annotation } from '@/components/AnnotatedText';
```

**Order (Python):**
1. Standard library imports
2. Third-party imports (fastapi, pydantic, asyncpg)
3. Local application imports (app.db, app.modules)

**Example:**
```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Literal
import asyncio

from app.db.deps import get_db
from app.db import repository as repo
```

## Component Patterns (Frontend)

**Client Components:**
- Mark with `'use client';` directive at top of file
- Use React hooks for state and effects
- Handle events with `useCallback` for memoization

**Server Components:**
- No directive needed (default in App Router)
- Use async functions for data fetching
- Access translations with `getTranslations()` (not `useTranslations()`)

**Props Pattern:**
- Define interface for props
- Destructure in function signature
- Provide default values inline

```typescript
interface HeroSectionProps {
  locale: string;
  isHebrew: boolean;
  translations: {
    headline: string;
    headlineTop: string;
    headlineBottom: string;
    // ...
  };
}

export default function HeroSection({ locale, isHebrew, translations }: HeroSectionProps) {
  // ...
}
```

**Component Composition:**
- Pass translation objects as props rather than using hooks in child components
- Keep translation key access in parent, pass strings to children
- Use `cn()` utility for conditional class merging

```typescript
// Parent (page)
const uploadTranslations = {
  title: t('uploadTitle'),
  description: t('uploadDesc'),
  // ...
};
<PaperUpload translations={uploadTranslations} />

// Child component
export default function PaperUpload({ translations }: PaperUploadProps) {
  const t = { ...defaultTranslations, ...translations };
  // Use t.title, t.description, etc.
}
```

## i18n Patterns

**Configuration:**
- Location: `frontend/i18n/config.ts`
- Locales: `['en', 'he']` with `'en'` as default
- Provider: `NextIntlClientProvider` wraps app in locale layout

**Message Files:**
- Location: `frontend/messages/{locale}.json`
- Structure: Nested keys by page/feature (e.g., `app.title`, `analyzer.placeholder`, `severity.outdated`)
- Both locales maintain identical key structure

**Usage in Client Components:**
```typescript
const t = useTranslations('analyzer');
const locale = useLocale();
const isHebrew = locale === 'he';

// Access keys
{t('uploadTitle')}
{t('processing.uploading')}  // Nested keys
```

**Usage in Server Components:**
```typescript
const t = await getTranslations();
const { locale } = await params;
setRequestLocale(locale);

// Access with full namespace
{t('home.heroHeadline')}
```

**RTL Handling:**
```typescript
const isRtl = locale === 'he';
<html lang={locale} dir={isRtl ? 'rtl' : 'ltr'}>
```

## API Conventions

**Route Structure:**
- Base path: `/api/v1/{module}/{action}`
- Modules: `ingestion`, `analysis`
- Examples: `POST /api/v1/analysis/analyze`, `POST /api/v1/ingestion/upload`

**Request Models (Pydantic):**
```python
class AnalysisRequest(BaseModel):
    text: str = Field(..., min_length=1)
    language: Optional[Literal['en', 'he', 'auto']] = 'auto'
    private_mode: Optional[bool] = True
```

**Response Models:**
```python
class AnalysisResponse(BaseModel):
    original_text: str
    analysis_status: str
    issues_found: list[Issue]
    corrected_text: Optional[str] = None
    note: Optional[str] = None
```

**Error Responses:**
```python
raise HTTPException(status_code=400, detail="Invalid file type. Currently only PDF is supported.")
raise HTTPException(status_code=500, detail=f"DB error: {e}")
```

**Frontend API Client:**
- Location: `frontend/lib/api/client.ts`
- Pattern: Export async functions per endpoint
- Transform backend responses to frontend-friendly format

```typescript
export async function analyzeText(
  text: string,
  options?: { language?: 'en' | 'he' | 'auto'; privateMode?: boolean }
): Promise<AnalysisResult> {
  const response = await fetch(`${API_BASE_URL}/api/v1/analysis/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, language: options?.language || 'auto' }),
  });
  // Transform and return
}
```

## Styling Conventions

**Tailwind CSS:**
- Version: v4 with PostCSS
- Custom theme in `frontend/app/globals.css`
- Custom colors: `pride-purple`, `pride-pink`, `pride-blue`, etc.
- Dark mode: Class-based (`.dark` on html element)

**Utility Classes Pattern:**
```typescript
<div className={cn(
  'rounded-xl border p-5 transition-all cursor-pointer',
  config.bgColor,
  config.borderColor,
  isExpanded && 'ring-2 ring-pride-purple/30'
)}/>
```

**Custom Component Classes:**
```css
.btn-primary {
  @apply inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2
         font-medium transition-all focus:outline-none focus:ring-2
         bg-gradient-to-tr from-pride-purple to-pride-pink text-white;
}

.glass {
  @apply bg-white/60 dark:bg-slate-900/50 backdrop-blur-md
         border border-white/40 dark:border-slate-800/50;
}
```

## Error Handling

**Frontend:**
- Try-catch in async functions
- Descriptive error messages with context
- No global error boundary yet

```typescript
if (!response.ok) {
  const errorText = await response.text();
  throw new Error(`Analysis failed: ${response.status} - ${errorText}`);
}
```

**Backend:**
- HTTPException with status codes
- Detail messages for debugging
- Transaction rollback on failure

```python
try:
    async with conn.transaction():
        # operations
except Exception as e:
    raise HTTPException(status_code=500, detail=f"DB error: {e}")
```

## Comments

**Documentation Comments:**
- Python: Docstrings for public functions and classes
- TypeScript: JSDoc not consistently used
- Section dividers with `===` in Python for major code blocks

```python
# =============================================================================
# DEMO: Rule-Based Term Dictionary
# =============================================================================
```

**TODO Annotations:**
```python
# TODO (for model integration):
# - [ ] Add Azure ML endpoint client
# - [ ] Load system prompt for LLM
```

## Database Patterns (Python)

**Repository Layer:**
- Location: `backend/app/db/repository.py`
- Pattern: One function per query
- All async with asyncpg
- Parameterized queries (`$1, $2`) for security

**Connection:**
```python
async def get_conn() -> asyncpg.Connection:
    return await asyncpg.connect(
        host=os.environ["PGHOST"],
        # ...
    )
```

**Query Pattern:**
```python
async def create_document(conn: asyncpg.Connection, org_id, user_id, ...) -> int:
    row = await conn.fetchrow(
        """INSERT INTO documents (...) VALUES ($1,$2,...) RETURNING document_id;""",
        org_id, user_id, ...
    )
    return row["document_id"]
```

## State Management

**Local State:**
- useState for component state
- useCallback for event handlers (memoization)
- useMemo for computed values

```typescript
const [viewState, setViewState] = useState<ViewState>('upload');
const [selectedAnnotation, setSelectedAnnotation] = useState<Annotation | null>(null);

const handleReset = useCallback(() => {
  setViewState('upload');
  setFileName('');
}, []);
```

**No Global State:**
- No Redux, Zustand, or Context API usage detected
- State is component-local or passed via props

## Animation Patterns

**Framer Motion:**
- Used extensively for UI animations
- AnimatePresence for enter/exit transitions
- motion components for animated elements

```typescript
<AnimatePresence mode="wait">
  {viewState === 'upload' && (
    <motion.div
      key="upload"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3 }}
    >
      {/* content */}
    </motion.div>
  )}
</AnimatePresence>
```

---

*Convention analysis: 2026-03-09*
