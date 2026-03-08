# Testing Patterns

**Analysis Date:** 2026-03-08

## Test Framework

**Status:** No testing framework configured

**Runner:**
- Frontend: NOT CONFIGURED (ESLint is configured but no Jest/Vitest)
- Backend: NOT CONFIGURED (no pytest.ini, setup.cfg, or test runner in requirements.txt)

**Current State:**
- No `.test.ts`, `.spec.ts`, `test_*.py`, or `*_test.py` files found in codebase (excluding node_modules)
- No test directory structure established
- No test scripts in `package.json`

## Recommendation for Future Implementation

**Frontend (Next.js 16):**
- Recommended: **Vitest** (modern, ESM-native, fast)
- Alternative: Jest (Next.js default, but slower)
- Assertion library: any (Vitest bundles Chai, or add @testing-library/react)

**Backend (FastAPI):**
- Recommended: **pytest** with pytest-asyncio for async tests
- Client: httpx (already in requirements.txt, perfect for testing)
- Fixtures: pytest fixtures for database setup/teardown

## Test Structure (Guidance for Future)

**Frontend Location:** Co-locate with source files or in `__tests__` directories

**Pattern:**
```
frontend/
├── components/
│   ├── ResultCard.tsx
│   ├── ResultCard.test.tsx        # Co-located
│   └── __tests__/
│       └── ResultCard.test.tsx    # Alternative
├── lib/
│   ├── api/
│   │   ├── client.ts
│   │   └── client.test.ts
```

**Backend Location:** Parallel structure in `tests/` directory

**Pattern:**
```
backend/
├── app/
│   ├── modules/
│   │   ├── analysis/
│   │   │   └── router.py
│   │   └── ingestion/
│   │       └── router.py
├── tests/
│   ├── test_analysis.py
│   └── test_ingestion.py
```

## Test Structure (When Implemented)

**Suite Organization (TypeScript Example):**
```typescript
import { describe, it, expect, beforeEach, afterEach } from 'vitest';

describe('AnalysisSummary Component', () => {
  let props: AnalysisSummaryProps;

  beforeEach(() => {
    props = {
      counts: { outdated: 2, biased: 1, offensive: 0, incorrect: 1 },
      score: 75,
      recommendations: ['Use inclusive language'],
      wordCount: 500,
    };
  });

  it('should render score and metrics', () => {
    const { getByText } = render(<AnalysisSummary {...props} />);
    expect(getByText('75')).toBeInTheDocument();
  });

  it('should apply correct color for score >= 70', () => {
    const { container } = render(<AnalysisSummary {...props} />);
    expect(container.querySelector('.text-amber-500')).toBeInTheDocument();
  });
});
```

**Patterns:**
- Setup: `beforeEach()` or `beforeAll()` for test data initialization
- Teardown: `afterEach()` or `afterAll()` for cleanup
- Assertion: Direct `expect()` statements with descriptive matchers

## Mocking

**Framework:** Recommended: **vitest** for frontend (built-in mocking), **unittest.mock** for backend

**Frontend Pattern (Vitest + MSW recommended):**
```typescript
import { vi } from 'vitest';

vi.mock('@/lib/api/client', () => ({
  analyzeText: vi.fn().mockResolvedValue({
    annotations: [],
    results: [],
    counts: { outdated: 0, biased: 0, offensive: 0, incorrect: 0 },
  }),
}));
```

**Backend Pattern (pytest):**
```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_analyze_with_db_mocked():
    mock_conn = AsyncMock()
    mock_conn.fetchrow.return_value = {'org_id': 1}

    response = await analyze_text(request, mock_conn)
    assert response.analysis_status == 'Success'
```

**What to Mock:**
- External API calls (e.g., `fetch()` in `analyzeText()`)
- Database queries (mock `asyncpg.Connection`)
- File I/O operations
- Network requests in ingestion

**What NOT to Mock:**
- Core business logic (rule-based term detection)
- Internal utility functions (e.g., `findOccurrences()`)
- Type constructors and data models
- Library functions unless truly external

## Fixtures and Factories

**Test Data (Not Yet Implemented):**

**Recommended Frontend Structure:**
```typescript
// lib/test-fixtures/analysis.ts
export const mockAnalysisResult: AnalysisResult = {
  annotations: [
    {
      start: 0,
      end: 10,
      severity: 'outdated',
      label: 'homosexual',
      explanation: 'Outdated term',
      suggestion: 'gay',
    },
  ],
  results: [...],
  counts: { outdated: 1, biased: 0, offensive: 0, incorrect: 0 },
  originalText: 'Sample text with issues',
};
```

**Recommended Backend Structure:**
```python
# tests/fixtures.py
@pytest.fixture
async def mock_db_connection():
    conn = AsyncMock()
    conn.fetchrow.return_value = {
        'org_id': 1,
        'name': 'Test Org',
        'default_private_mode': True,
    }
    return conn

@pytest.fixture
def sample_analysis_request():
    return AnalysisRequest(
        text='Test text with homosexual term',
        language='en',
        private_mode=True,
    )
```

**Location:**
- Frontend: `frontend/lib/test-fixtures/` or `frontend/__fixtures__/`
- Backend: `backend/tests/fixtures.py`

## Coverage

**Requirements:** Not yet enforced

**Recommendation:** Once tests are implemented, aim for:
- **Critical paths:** 80%+ (e.g., analysis endpoint, text transformation)
- **Utilities:** 90%+ (e.g., `findOccurrences()`, `mapSeverity()`)
- **Components:** 70%+ (visual components can be harder to test)
- **Database layer:** 85%+ (critical for data consistency)

**View Coverage (When Implemented):**

Frontend:
```bash
npm run test:coverage
# Output: coverage/lcov-report/index.html
```

Backend:
```bash
pytest --cov=app --cov-report=html
# Output: htmlcov/index.html
```

## Test Types

**Unit Tests (Recommended First):**
- Scope: Individual functions or components
- Approach: Test pure logic without dependencies
- Examples:
  - `analyzeText()` with mocked fetch
  - `mapSeverity()` with different string inputs
  - `getScoreColor()` with various score values
  - `find_issues()` with sample text

**Integration Tests (For DB + API):**
- Scope: API endpoints with real database
- Approach: Spin up test database, test end-to-end flow
- Examples:
  - POST `/api/v1/analysis/analyze` with database transaction
  - Verify findings are stored in DB
  - Test org/user resolution from database

**E2E Tests (Optional for UI):**
- Framework: Not configured (could use Playwright or Cypress)
- Scope: Full user flow (upload → processing → results)
- Approach: Automate browser interactions
- Deferred to later phase

## Common Patterns (When Implemented)

**Async Testing (Frontend - Vitest):**
```typescript
it('should fetch and transform analysis result', async () => {
  const { result } = renderHook(() => useAnalysis());

  await act(async () => {
    await result.current.analyzeText('test text');
  });

  expect(result.current.isLoading).toBe(false);
  expect(result.current.data).toBeDefined();
});
```

**Async Testing (Backend - pytest):**
```python
@pytest.mark.asyncio
async def test_analyze_returns_issues():
    request = AnalysisRequest(text='homosexual is outdated', language='en')
    response = await analyze_text(request)

    assert response.analysis_status == 'Success'
    assert len(response.issues_found) >= 1
    assert response.issues_found[0].severity == 'outdated'
```

**Error Testing (Backend - pytest):**
```python
@pytest.mark.asyncio
async def test_analyze_empty_text_raises_validation_error():
    request = AnalysisRequest(text='', language='en')  # min_length=1

    with pytest.raises(ValueError):
        await analyze_text(request)
```

**Error Testing (Frontend - Vitest):**
```typescript
it('should handle API errors gracefully', async () => {
  vi.mocked(analyzeText).mockRejectedValueOnce(
    new Error('Network error')
  );

  const { result } = renderHook(() => useAnalysis());

  await act(async () => {
    await expect(result.current.analyzeText('test')).rejects.toThrow();
  });

  expect(result.current.error).toBeTruthy();
});
```

## Current Code Suitable for Testing

**Highly Testable Functions:**
- `findOccurrences()` in `client.ts` - pure function, no side effects
- `mapSeverity()` in `client.ts` - deterministic lookup
- `find_issues()` in `analysis/router.py` - pure logic on text
- `getScoreColor()`, `getScoreLabel()` in `AnalysisSummary.tsx` - pure functions

**Partially Testable:**
- `analyzeText()` in `client.ts` - needs mocked fetch
- `analyze_text()` endpoint - needs mocked database
- Components with state (use renderHook for hooks, mock children)

**Hard to Test (Without Infrastructure):**
- Database connection (`connection.py`) - needs test database
- File upload handler (`ingestion/router.py`) - needs file fixtures
- Page components with deep nesting - consider breaking into smaller components

---

*Testing analysis: 2026-03-08*
