# Testing Patterns

**Analysis Date:** 2026-03-09

## Test Framework Status

**Current State:** NO TESTING FRAMEWORK CONFIGURED

**Frontend:**
- No Jest/Vitest configured
- No test scripts in `package.json`
- ESLint is present but no test runner

**Backend:**
- No pytest in `requirements.txt`
- No pytest.ini, setup.cfg, or pyproject.toml with test config
- No `backend/tests/` directory

**Existing Test-Related Scripts:**
- `scripts/db_test.py` - Manual DB connection verification (not automated tests)
- `scripts/db_insert_test.py` - Manual DB insert verification using repository layer

## Recommended Test Framework Setup

### Frontend (Next.js 16 + TypeScript)

**Primary:** Vitest + React Testing Library

```bash
# Installation
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom @vitest/coverage-v8
```

**Config:** Create `vitest.config.ts`
```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./vitest.setup.ts'],
    include: ['**/*.test.{ts,tsx}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      include: ['components/**', 'lib/**'],
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './'),
    },
  },
});
```

**Add to `package.json`:**
```json
{
  "scripts": {
    "test": "vitest",
    "test:run": "vitest run",
    "test:coverage": "vitest run --coverage"
  }
}
```

### Backend (FastAPI + Python 3.11)

**Primary:** pytest + pytest-asyncio + httpx

**Add to `requirements.txt`:**
```
pytest==8.0.0
pytest-asyncio==0.23.0
pytest-cov==4.1.0
```

**Config:** Create `backend/pytest.ini`
```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_functions = test_*
addopts = -v --tb=short
```

**Run commands:**
```bash
cd backend && pytest                    # Run all tests
cd backend && pytest -v                 # Verbose output
cd backend && pytest --cov=app          # With coverage
cd backend && pytest -k "test_analysis" # Filter by name
```

## Test File Organization

### Frontend Structure

```
frontend/
├── components/
│   ├── AnalysisSummary.tsx
│   ├── AnalysisSummary.test.tsx     # Co-located unit test
│   ├── AnnotatedText.tsx
│   └── AnnotatedText.test.tsx
├── lib/
│   ├── api/
│   │   ├── client.ts
│   │   └── client.test.ts           # API client tests
│   └── utils/
│       ├── demoData.ts
│       └── demoData.test.ts         # Demo data transformation tests
├── __fixtures__/                     # Test fixtures directory
│   ├── analysis-response.ts
│   └── annotation-data.ts
└── vitest.setup.ts
```

### Backend Structure

```
backend/
├── app/
│   ├── modules/
│   │   ├── analysis/
│   │   │   └── router.py
│   │   └── ingestion/
│   │       └── router.py
│   └── db/
│       └── repository.py
├── tests/
│   ├── conftest.py                  # Pytest fixtures
│   ├── fixtures/
│   │   ├── sample_texts.py          # Hebrew/English test texts
│   │   └── mock_responses.py        # Mock API/DB responses
│   ├── unit/
│   │   ├── test_find_issues.py      # Rule-based detection tests
│   │   └── test_repository.py       # DB function tests
│   ├── integration/
│   │   ├── test_analysis_api.py     # API endpoint tests
│   │   └── test_ingestion_api.py    # Upload endpoint tests
│   └── e2e/
│       └── test_full_flow.py        # End-to-end with test DB
└── pytest.ini
```

## Test Priorities for Inclusify

### Priority 1: Core Detection Logic (Unit Tests)

**Target Files:**
- `backend/app/modules/analysis/router.py` - `find_issues()` function
- `frontend/lib/utils/demoData.ts` - `analyzeDemoText()` function
- `frontend/lib/api/client.ts` - `mapSeverity()`, `findOccurrences()`, `transformResponse()`

**Example: Testing `find_issues()` (Backend)**
```python
# backend/tests/unit/test_find_issues.py
import pytest
from app.modules.analysis.router import find_issues

class TestFindIssues:
    def test_detects_outdated_english_term(self):
        text = "The homosexual population faces challenges."
        issues = find_issues(text)

        assert len(issues) >= 1
        assert any(i.span.lower() == "homosexual" for i in issues)
        assert any(i.severity == "outdated" for i in issues)

    def test_detects_hebrew_term(self):
        text = "המחקר על אנשים הומוסקסואליים"
        issues = find_issues(text)

        assert len(issues) >= 1
        assert any("הומוסקסואל" in i.span for i in issues)

    def test_preserves_original_case(self):
        text = "HOMOSEXUAL vs homosexual vs Homosexual"
        issues = find_issues(text)

        spans = [i.span for i in issues]
        assert "HOMOSEXUAL" in spans
        assert "homosexual" in spans
        assert "Homosexual" in spans

    def test_correct_text_positions(self):
        text = "Start homosexual end"
        issues = find_issues(text)

        issue = issues[0]
        assert issue.start == 6
        assert issue.end == 16
        assert text[issue.start:issue.end] == "homosexual"

    def test_multiple_occurrences(self):
        text = "homosexual homosexual homosexual"
        issues = find_issues(text)

        assert len(issues) == 3
        positions = sorted([i.start for i in issues])
        assert positions == [0, 11, 22]

    def test_no_false_positives_on_clean_text(self):
        text = "LGBTQ+ individuals deserve equal rights."
        issues = find_issues(text)

        assert len(issues) == 0

    def test_handles_empty_text(self):
        text = ""
        issues = find_issues(text)

        assert issues == []
```

**Example: Testing `analyzeDemoText()` (Frontend)**
```typescript
// frontend/lib/utils/demoData.test.ts
import { describe, it, expect } from 'vitest';
import { analyzeDemoText, extendedTermMapEN, extendedTermMapHE } from './demoData';

describe('analyzeDemoText', () => {
  it('detects English outdated terms', () => {
    const result = analyzeDemoText('The homosexual community faces stigma.', 'en');

    expect(result.annotations.length).toBeGreaterThan(0);
    expect(result.counts.outdated).toBeGreaterThan(0);
  });

  it('detects Hebrew terms with correct locale', () => {
    const result = analyzeDemoText('מחקר על אנשים הומוסקסואליים', 'he');

    expect(result.annotations.length).toBeGreaterThan(0);
    expect(result.results[0].term).toContain('הומוסקסואל');
  });

  it('calculates inclusivity score correctly', () => {
    const cleanText = 'LGBTQ+ individuals deserve respect.';
    const result = analyzeDemoText(cleanText, 'en');

    expect(result.summary.score).toBe(100);
  });

  it('returns correct annotation positions', () => {
    const text = 'The homosexual term is outdated.';
    const result = analyzeDemoText(text, 'en');

    const annotation = result.annotations.find(a => a.label.toLowerCase() === 'homosexual');
    expect(annotation).toBeDefined();
    expect(text.slice(annotation!.start, annotation!.end).toLowerCase()).toBe('homosexual');
  });
});
```

### Priority 2: API Client Tests (Frontend)

**Target File:** `frontend/lib/api/client.ts`

```typescript
// frontend/lib/api/client.test.ts
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { analyzeText, healthCheck, uploadFile } from './client';

describe('API Client', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  describe('analyzeText', () => {
    it('sends correct request body', async () => {
      const mockResponse = {
        original_text: 'test',
        analysis_status: 'Success',
        issues_found: [],
      };

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      } as Response);

      await analyzeText('test text', { language: 'en', privateMode: true });

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/analysis/analyze'),
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text: 'test text',
            language: 'en',
            private_mode: true,
          }),
        })
      );
    });

    it('transforms response to frontend format', async () => {
      const backendResponse = {
        original_text: 'homosexual',
        analysis_status: 'Success',
        issues_found: [
          {
            span: 'homosexual',
            severity: 'outdated',
            type: 'Terminology',
            description: 'Outdated term',
            suggestion: 'gay',
            start: 0,
            end: 10,
          },
        ],
      };

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(backendResponse),
      } as Response);

      const result = await analyzeText('homosexual');

      expect(result.annotations).toHaveLength(1);
      expect(result.annotations[0].severity).toBe('outdated');
      expect(result.counts.outdated).toBe(1);
    });

    it('throws error on API failure', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: () => Promise.resolve('Server error'),
      } as Response);

      await expect(analyzeText('test')).rejects.toThrow('Analysis failed: 500');
    });
  });

  describe('mapSeverity', () => {
    // Test the internal mapping function
    it('maps backend severities to frontend format', () => {
      // This requires exporting mapSeverity or testing via transformResponse
    });
  });
});
```

### Priority 3: API Endpoint Tests (Backend)

**Target File:** `backend/app/modules/analysis/router.py`

```python
# backend/tests/integration/test_analysis_api.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
class TestAnalysisEndpoint:
    async def test_analyze_returns_success(self, client):
        response = await client.post(
            "/api/v1/analysis/analyze",
            json={"text": "Test text", "language": "en", "private_mode": True}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["analysis_status"] == "Success"
        assert "issues_found" in data

    async def test_analyze_detects_known_term(self, client):
        response = await client.post(
            "/api/v1/analysis/analyze",
            json={"text": "The homosexual community", "language": "en"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["issues_found"]) >= 1
        assert any(i["span"].lower() == "homosexual" for i in data["issues_found"])

    async def test_analyze_empty_text_fails(self, client):
        response = await client.post(
            "/api/v1/analysis/analyze",
            json={"text": "", "language": "en"}
        )

        assert response.status_code == 422  # Pydantic validation error

    async def test_analyze_hebrew_text(self, client):
        response = await client.post(
            "/api/v1/analysis/analyze",
            json={"text": "מחקר על אנשים הומוסקסואליים", "language": "he"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["issues_found"]) >= 1

    async def test_private_mode_defaults_to_true(self, client):
        response = await client.post(
            "/api/v1/analysis/analyze",
            json={"text": "Test text"}
        )

        assert response.status_code == 200
        # When DB is integrated, verify no text is stored
```

### Priority 4: Repository Layer Tests (Backend)

**Target File:** `backend/app/db/repository.py`

```python
# backend/tests/unit/test_repository.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.db import repository as repo

@pytest.fixture
def mock_connection():
    conn = AsyncMock()
    return conn

@pytest.mark.asyncio
class TestRepository:
    async def test_get_org_by_slug(self, mock_connection):
        mock_connection.fetchrow.return_value = {
            'org_id': 1,
            'name': 'Test Org',
            'default_private_mode': True,
        }

        result = await repo.get_org_by_slug(mock_connection, 'test-org')

        assert result['org_id'] == 1
        mock_connection.fetchrow.assert_called_once()

    async def test_create_document_returns_id(self, mock_connection):
        mock_connection.fetchrow.return_value = {'document_id': 123}

        doc_id = await repo.create_document(
            conn=mock_connection,
            org_id=1,
            user_id=1,
            input_type='paste',
            language='en',
            private_mode=True,
        )

        assert doc_id == 123

    async def test_insert_finding_returns_finding_id(self, mock_connection):
        mock_connection.fetchrow.return_value = {'finding_id': 456}

        finding_id = await repo.insert_finding(
            conn=mock_connection,
            run_id=1,
            category='Terminology',
            severity='low',
            start_idx=0,
            end_idx=10,
            explanation='Test explanation',
        )

        assert finding_id == 456
```

### Priority 5: Component Tests (Frontend)

**Target Files:** Key UI components

```typescript
// frontend/components/SeverityBadge.test.tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SeverityBadge } from './SeverityBadge';

describe('SeverityBadge', () => {
  it('renders correct label for outdated severity', () => {
    render(<SeverityBadge severity="outdated" />);
    expect(screen.getByText(/outdated/i)).toBeInTheDocument();
  });

  it('applies correct color class for offensive severity', () => {
    const { container } = render(<SeverityBadge severity="offensive" />);
    expect(container.firstChild).toHaveClass('bg-red-500');
  });
});
```

```typescript
// frontend/components/AnnotatedText.test.tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import AnnotatedText from './AnnotatedText';

describe('AnnotatedText', () => {
  const sampleAnnotations = [
    {
      start: 4,
      end: 14,
      severity: 'outdated' as const,
      label: 'homosexual',
      explanation: 'Outdated term',
      suggestion: 'gay',
    },
  ];

  it('renders text with highlighted annotation', () => {
    render(
      <AnnotatedText
        text="The homosexual community"
        annotations={sampleAnnotations}
      />
    );

    expect(screen.getByText('homosexual')).toBeInTheDocument();
  });

  it('calls onAnnotationClick when annotation is clicked', async () => {
    const onClick = vi.fn();
    render(
      <AnnotatedText
        text="The homosexual community"
        annotations={sampleAnnotations}
        onAnnotationClick={onClick}
      />
    );

    await userEvent.click(screen.getByText('homosexual'));
    expect(onClick).toHaveBeenCalledWith(sampleAnnotations[0]);
  });
});
```

## Test Fixtures

### Backend Fixtures (`backend/tests/conftest.py`)

```python
import pytest
from app.modules.analysis.router import AnalysisRequest

@pytest.fixture
def sample_english_text():
    return """
    The study examined homosexual populations in academic contexts.
    Researchers noted that sexual preference varies across demographics.
    Some participants were born as a man but identify as women.
    """

@pytest.fixture
def sample_hebrew_text():
    return """
    המחקר בדק אוכלוסיות הומוסקסואליות בהקשרים אקדמיים.
    חוקרים ציינו שהעדפה מינית משתנה בין קבוצות דמוגרפיות.
    """

@pytest.fixture
def clean_text():
    return "LGBTQ+ individuals deserve equal rights and respect."

@pytest.fixture
def analysis_request_factory():
    def _create(text: str, language: str = 'en', private_mode: bool = True):
        return AnalysisRequest(
            text=text,
            language=language,
            private_mode=private_mode,
        )
    return _create
```

### Frontend Fixtures (`frontend/__fixtures__/analysis.ts`)

```typescript
import type { Annotation } from '@/components/AnnotatedText';
import type { AnalysisResult } from '@/lib/api/client';

export const mockAnnotations: Annotation[] = [
  {
    start: 4,
    end: 14,
    severity: 'outdated',
    label: 'homosexual',
    explanation: 'The term "homosexual" is considered outdated and clinical.',
    suggestion: 'gay, lesbian, or same-sex attracted',
    references: [{ label: 'GLAAD Guide', url: 'https://glaad.org/reference' }],
  },
  {
    start: 30,
    end: 47,
    severity: 'incorrect',
    label: 'sexual preference',
    explanation: 'Sexual orientation is not a choice.',
    suggestion: 'sexual orientation',
    references: [],
  },
];

export const mockAnalysisResult: AnalysisResult = {
  annotations: mockAnnotations,
  results: [
    {
      phrase: 'homosexual',
      severity: 'outdated',
      explanation: 'The term "homosexual" is considered outdated.',
      suggestion: 'gay, lesbian',
      references: [],
    },
  ],
  counts: { outdated: 1, biased: 0, offensive: 0, incorrect: 1 },
  originalText: 'The homosexual community and sexual preference research.',
};

export const emptyAnalysisResult: AnalysisResult = {
  annotations: [],
  results: [],
  counts: { outdated: 0, biased: 0, offensive: 0, incorrect: 0 },
  originalText: 'This text is already inclusive.',
};
```

## Coverage Requirements

**Target Coverage (When Implemented):**

| Module | Target | Rationale |
|--------|--------|-----------|
| `find_issues()` | 95% | Core business logic |
| `repository.py` | 90% | Database integrity |
| `client.ts` (API) | 85% | Frontend-backend contract |
| `analyzeDemoText()` | 90% | Demo mode accuracy |
| UI Components | 70% | Visual elements harder to test |
| Page components | 50% | Integration/E2E covers these |

**View Coverage:**
```bash
# Frontend
npm run test:coverage

# Backend
cd backend && pytest --cov=app --cov-report=html
open htmlcov/index.html
```

## CI Integration (Future)

**GitHub Actions Workflow (`.github/workflows/test.yml`):**

```yaml
name: Tests

on:
  push:
    branches: [main, feature/*]
  pull_request:
    branches: [main]

jobs:
  test-frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm run lint
      - run: npm run test:run
      - run: npm run test:coverage
      - uses: codecov/codecov-action@v4
        with:
          files: coverage/lcov.info

  test-backend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      - run: pip install -r requirements.txt
      - run: pytest --cov=app --cov-report=xml
      - uses: codecov/codecov-action@v4
        with:
          files: coverage.xml
```

## Bilingual Testing Considerations

**Hebrew Text Handling:**
- Ensure tests cover RTL text with proper position indices
- Test Unicode normalization (some Hebrew characters have multiple representations)
- Verify position calculations work correctly for Hebrew strings

**Example:**
```python
def test_hebrew_position_tracking():
    text = "מחקר על הומוסקסואל"
    #       0123456789...
    # "הומוסקסואל" starts at index 8
    issues = find_issues(text)

    assert issues[0].start == 8
    assert text[issues[0].start:issues[0].end] == "הומוסקסואל"
```

## ML Model Testing (Future)

When the fine-tuned LLM is integrated:

```python
# backend/tests/integration/test_ml_inference.py
@pytest.mark.asyncio
@pytest.mark.skipif(not ML_ENDPOINT_CONFIGURED, reason="ML endpoint not available")
async def test_llm_analysis():
    """Integration test with real ML model (requires Azure endpoint)"""
    request = AnalysisRequest(
        text="Academic text with problematic terminology...",
        language="en",
    )

    response = await analyze_text_with_llm(request)

    assert response.confidence_scores is not None
    assert all(0 <= s <= 1 for s in response.confidence_scores)
```

---

*Testing analysis: 2026-03-09*
