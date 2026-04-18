"""Locust load test for POST /api/v1/ingestion/upload.

Usage:
    cd backend
    locust -f loadtests/locustfile_upload.py --host=http://localhost:8000

Or headless (5 users, 1 spawn/sec, 2-minute run):
    locust -f loadtests/locustfile_upload.py --host=http://localhost:8000 \\
        -u 5 -r 1 -t 2m --headless --csv=upload_5u

Put sample documents to upload under backend/loadtests/fixtures/.
If the fixtures dir is missing or empty, a small synthetic TXT is
generated on the fly so the script still runs.
"""
from __future__ import annotations

import random
from pathlib import Path

from locust import HttpUser, between, task

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# (filename, content_type) — extensions must match one of ALLOWED_CONTENT_TYPES
# in backend/app/modules/ingestion/router.py.
_CONTENT_TYPES = {
    ".pdf":  "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".txt":  "text/plain",
}

_SYNTHETIC_HEBREW_TXT = (
    "זוהי דוגמה קצרה לטקסט אקדמי בעברית המכיל מונחים שהמודל אמור לסקור "
    "ולהציע להם חלופות מכילות.\n"
    "For bilingual coverage we also include a short English paragraph "
    "with outdated clinical terminology so the analyzer has something to flag."
)


def _load_fixtures() -> list[tuple[str, bytes, str]]:
    fixtures: list[tuple[str, bytes, str]] = []
    if FIXTURES_DIR.is_dir():
        for path in sorted(FIXTURES_DIR.iterdir()):
            ct = _CONTENT_TYPES.get(path.suffix.lower())
            if ct and path.is_file():
                fixtures.append((path.name, path.read_bytes(), ct))
    if not fixtures:
        fixtures.append(
            ("synthetic_he_en.txt", _SYNTHETIC_HEBREW_TXT.encode("utf-8"), "text/plain")
        )
    return fixtures


class IngestionUploadUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self) -> None:
        self.fixtures = _load_fixtures()

    @task
    def upload_document(self) -> None:
        name, data, ct = random.choice(self.fixtures)
        files = {"file": (name, data, ct)}
        # 180s timeout — Docling on first call pulls model weights on some
        # machines; subsequent parses are O(seconds). Keep slack so that
        # slow runs register as slow, not as failures.
        with self.client.post(
            "/api/v1/ingestion/upload",
            files=files,
            catch_response=True,
            timeout=180,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                body = resp.text[:200] if resp.text else ""
                resp.failure(f"{resp.status_code}: {body}")
