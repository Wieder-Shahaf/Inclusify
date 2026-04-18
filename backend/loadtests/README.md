# Load tests

Locust scripts for the two user-facing bottleneck endpoints.

| Script | Endpoint | Payload |
| --- | --- | --- |
| `locustfile_upload.py` | `POST /api/v1/ingestion/upload` | Files from `./fixtures/` (PDF/DOCX/PPTX/TXT). Falls back to a synthetic Hebrew+English TXT when the fixtures dir is empty. |
| `locustfile_analyze_mixed.py` | `POST /api/v1/analysis/analyze` | Mixed Hebrew + English paragraph. |
| `locustfile_analyze_english.py` | `POST /api/v1/analysis/analyze` | English-only paragraph — use when isolating vLLM performance without Hebrew tokenization cost. |

## Running

```bash
# From backend/ (so the default Python env has fastapi/uvicorn available
# for the local dev server you are targeting).
cd backend

# 1. Start the app you want to test (local):
uvicorn app.main:app --port 8000

# 2. In another terminal, launch locust and open http://localhost:8089
locust -f loadtests/locustfile_upload.py --host=http://localhost:8000

# 3. Headless CSV runs for the report — adjust -u to sweep 5/10/20:
locust -f loadtests/locustfile_upload.py --host=http://localhost:8000 \
       -u 5 -r 1 -t 2m --headless --csv=upload_5u
```

## Fixtures

Drop sample `.pdf`, `.docx`, `.pptx`, `.txt` files into `backend/loadtests/fixtures/`.
The directory is git-ignored so real user documents never land in the repo.
Each locust user picks a fixture at random per request.
