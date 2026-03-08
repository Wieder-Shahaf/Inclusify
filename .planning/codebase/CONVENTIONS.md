# Coding Conventions

**Analysis Date:** 2026-03-08

## Naming Patterns

**Files:**
- React components: PascalCase (e.g., `AnalysisSummary.tsx`, `ResultCard.tsx`)
- Utilities and services: camelCase (e.g., `demoData.ts`, `client.ts`)
- Configuration files: camelCase or snake_case for env-related files (e.g., `eslint.config.mjs`)
- Python modules: snake_case (e.g., `connection.py`, `repository.py`)
- Directory names: camelCase (e.g., `components/`, `lib/`, `modules/`)

**Functions:**
- TypeScript/JavaScript: camelCase for all functions (e.g., `analyzeText()`, `findOccurrences()`, `getScoreColor()`)
- Python: snake_case for all functions (e.g., `get_org_by_slug()`, `create_document()`, `insert_finding()`)
- Async functions: prefix convention not enforced; functions named naturally (e.g., `async def get_conn()`)

**Variables:**
- TypeScript/React: camelCase (e.g., `viewState`, `selectedAnnotation`, `isHebrew`)
- Constants: UPPER_CASE (e.g., `TERM_RULES`, `API_BASE_URL`, `defaultTranslations`)
- Python: snake_case (e.g., `text_sha256`, `org_id`, `user_org_id`)
- Component props: PascalCase in types (e.g., `AnalysisSummaryProps`, `AnalysisRequest`)

**Types:**
- TypeScript: PascalCase for interfaces and types (e.g., `Annotation`, `Result`, `Severity`)
- Python Pydantic models: PascalCase (e.g., `AnalysisRequest`, `AnalysisResponse`, `Issue`)
- Enums/Literals: lowercase values in type definitions

## Code Style

**Formatting:**
- ESLint with Next.js core web vitals and TypeScript presets enforces frontend styling
- Config file: `frontend/eslint.config.mjs` (ESLint v9+ flat config)
- No Prettier config found; ESLint handles linting but not formatting
- Indentation: 2 spaces (observed in all TypeScript/JSX files)
- Line endings: LF (Unix style)

**Linting:**
- ESLint: Uses `eslint-config-next/core-web-vitals` and `eslint-config-next/typescript`
- Run command: `npm run lint` (defined in `frontend/package.json`)
- Python: No linting config detected (no Black, pylint, or Ruff config)

## Import Organization

**Order:**
1. External libraries (React, Next.js, third-party packages)
2. Relative imports from project (using `@/` path alias)
3. Type imports (when separated, but typically mixed with regular imports)

**Path Aliases:**
- Frontend: `@/*` maps to `./` (root of frontend directory, allowing `@/lib`, `@/components`, etc.)
- Example: `import { cn } from '@/lib/utils'`

**Example from codebase:**
```typescript
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Severity } from './SeverityBadge';
import { TrendingUp, AlertCircle, ... } from 'lucide-react';
import { useTranslations } from 'next-intl';
```

## Error Handling

**TypeScript/Frontend Patterns:**
- Try-catch blocks in async functions (e.g., `client.ts` `healthCheck()`)
- Direct error propagation with descriptive messages (e.g., `throw new Error(\`Analysis failed: ${response.status}\`)`)
- HTTPException in FastAPI routes with status codes and detail messages
- No global error boundary or centralized error handler detected

**Python Backend Patterns:**
- FastAPI HTTPException for error responses (e.g., status_code=400, detail="...")
- Early validation in route handlers
- Async context managers for transactional safety (e.g., `async with conn.transaction()`)
- Direct exception chaining in catch blocks: `raise HTTPException(status_code=500, detail=f"DB error: {e}")`

## Logging

**Framework:** console for development, no structured logging detected

**Patterns:**
- TypeScript: Direct `console.error()` in catch blocks (e.g., ingestion router)
- Python: `print()` for error logging (e.g., `print(f"Error processing file: {str(e)}")`)
- No centralized logger or log levels enforced
- Recommendation: Logging is minimal and suitable for demo/development stage

## Comments

**When to Comment:**
- Docstrings required in Python functions for clarity (observed in backend routers)
- Inline comments explain complex logic or configuration (e.g., CORS setup, TODO annotations)
- Section headers with `=` dividers separate major code blocks (seen in `analysis/router.py`)

**JSDoc/TSDoc:**
- Not consistently used in TypeScript code
- Python functions have docstrings describing purpose and parameters
- Example: `"""Analyze text for non-inclusive LGBTQ+ language."""`

**Example from codebase:**
```python
@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_text(request: AnalysisRequest):
    """
    Analyze text for non-inclusive LGBTQ+ language.

    **CURRENT STATUS: DEMO MODE (Rule-Based Detection)**

    This endpoint currently uses keyword matching as a placeholder.
    """
```

## Function Design

**Size:** Functions tend to be compact (50-100 lines max for complex logic)

**Parameters:**
- TypeScript: Prefer destructuring for props (e.g., `function ResultCard({ r, bgColor })`)
- Pydantic for request validation in FastAPI (automatic validation)
- Optional parameters with defaults (e.g., `language: Optional[Literal['en', 'he', 'auto']] = 'auto'`)

**Return Values:**
- Explicit types in signatures (TypeScript: `Promise<AnalysisResult>`, Python: type hints)
- Void functions avoid explicit returns
- Pydantic models for structured responses

**Example:**
```typescript
async function findOccurrences(text: string, phrase: string): Array<{ start: number; end: number }> {
  const occurrences: Array<{ start: number; end: number }> = [];
  // ... logic ...
  return occurrences;
}
```

## Module Design

**Exports:**
- TypeScript: Named exports preferred (e.g., `export async function analyzeText()`)
- Default exports for pages and main components (e.g., `export default function AnalyzePage()`)
- Python: No explicit export statements; functions are accessed via imports

**Barrel Files:**
- Used in some modules (e.g., `frontend/app/[locale]/`)
- Not consistently applied across all directories

## State Management (Frontend)

**Pattern:** React hooks (useState, useCallback) for local component state

**Example:**
```typescript
const [viewState, setViewState] = useState<ViewState>('upload');
const [selectedAnnotation, setSelectedAnnotation] = useState<Annotation | null>(null);
const handleReset = useCallback(() => { ... }, []);
```

**Internationalization (i18n):**
- next-intl for multi-language support (English/Hebrew)
- Accessed via `useTranslations()` hook (e.g., `const t = useTranslations('severity')`)
- Translations keys are hierarchical (e.g., `severity.outdated`, `recommendations.biased`)

## Database Code (Python)

**Pattern:** Repository layer with asyncpg for raw SQL execution

**Characteristics:**
- All queries are parameterized (`$1, $2` placeholders) for SQL injection prevention
- Async/await for non-blocking I/O
- Type hints on all function parameters and returns
- Examples: `backend/app/db/repository.py`

**Example:**
```python
async def create_document(
    conn: asyncpg.Connection,
    org_id,
    user_id,
    input_type: str,
    # ... more params ...
) -> int:
    row = await conn.fetchrow(
        """INSERT INTO documents ... RETURNING document_id;""",
        org_id, user_id, input_type, ...
    )
    return row["document_id"]
```

---

*Convention analysis: 2026-03-08*
