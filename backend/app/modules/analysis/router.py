"""
Analysis Router - LGBTQ+ Inclusive Language Detection

=============================================================================
                        HYBRID DETECTION (LLM + Rules)
=============================================================================
This module uses hybrid detection combining:
- LLM (lightblue/suzume-llama-3-8B-multilingual) for contextual analysis
- Rule-based detection as fallback for high-precision known terms

Detection modes (reported in analysis_mode field):
- "llm": All sentences successfully analyzed by LLM
- "hybrid": Some LLM success + some rule-based fallback
- "rules_only": LLM unavailable, using rule-based only

The rule-based approach serves as:
1. A fallback when the LLM endpoint is unavailable
2. A baseline for high-precision detection of known terms
3. Complementary detection for terms not in LLM training

TODO (remaining):
- [ ] Add confidence scores from model
- [ ] Enable DB persistence (commented code below)
=============================================================================
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Literal
import asyncio
import hashlib
import time

from app.auth.users import current_active_user
from app.db.models import User

# [CONFLICT 1 SOLVED] Friend's imports are saved here but disabled
# --- PENDING DB INTEGRATION (Uncomment when DB is ready) ---
# from app.db.deps import get_db
# from app.db import repository as repo

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class AnalysisRequest(BaseModel):
    text: str = Field(..., min_length=1)
    language: Optional[Literal['en', 'he', 'auto']] = 'auto'
    private_mode: Optional[bool] = True
    
    # [CONFLICT 2 SOLVED] Friend's fields added here (as Optional) so they don't break validation
    org_slug: Optional[str] = None
    user_email: Optional[str] = None


class Issue(BaseModel):
    span: str
    severity: Literal['outdated', 'biased', 'offensive', 'incorrect']
    type: str
    description: str
    suggestion: Optional[str] = None
    start: int
    end: int


class AnalysisResponse(BaseModel):
    original_text: str
    analysis_status: str
    issues_found: list[Issue]
    corrected_text: Optional[str] = None
    note: Optional[str] = None
    analysis_mode: Literal['llm', 'hybrid', 'rules_only'] = 'rules_only'


# =============================================================================
# DEMO: Rule-Based Term Dictionary
# =============================================================================

TERM_RULES = [
    # English terms
    {
        "term": "homosexual",
        "severity": "outdated",
        "type": "Outdated Terminology",
        "description": "The term 'homosexual' is considered clinical and outdated. It has historically been used in pathologizing contexts.",
        "suggestion": "Use 'gay' or 'lesbian' depending on context, or 'LGBTQ+ person'",
    },
    {
        "term": "transsexual",
        "severity": "outdated",
        "type": "Outdated Terminology",
        "description": "The term 'transsexual' is outdated and often perceived as medicalizing. It focuses on medical transition rather than identity.",
        "suggestion": "Use 'transgender person' or 'trans person'",
    },
    {
        "term": "sexual preference",
        "severity": "incorrect",
        "type": "Incorrect Terminology",
        "description": "Sexual orientation is not a choice or preference. Using 'preference' implies it can be changed.",
        "suggestion": "Use 'sexual orientation'",
    },
    {
        "term": "born a man",
        "severity": "offensive",
        "type": "Invalidating Language",
        "description": "This phrase invalidates a person's gender identity and implies that assigned sex determines gender.",
        "suggestion": "Use 'assigned male at birth (AMAB)' if medically relevant",
    },
    {
        "term": "born a woman",
        "severity": "offensive",
        "type": "Invalidating Language",
        "description": "This phrase invalidates a person's gender identity and implies that assigned sex determines gender.",
        "suggestion": "Use 'assigned female at birth (AFAB)' if medically relevant",
    },
    {
        "term": "normal people",
        "severity": "biased",
        "type": "Biased Language",
        "description": "Using 'normal' to describe non-LGBTQ+ people implies that LGBTQ+ people are abnormal.",
        "suggestion": "Use 'cisgender' or 'heterosexual' if referring to those specific groups, or be more specific",
    },
    {
        "term": "the gays",
        "severity": "biased",
        "type": "Dehumanizing Language",
        "description": "Using 'the gays' as a noun can be dehumanizing and othering.",
        "suggestion": "Use 'gay people' or 'gay individuals'",
    },
    {
        "term": "lifestyle choice",
        "severity": "incorrect",
        "type": "Incorrect Framing",
        "description": "Being LGBTQ+ is not a lifestyle choice. This framing is often used to delegitimize LGBTQ+ identities.",
        "suggestion": "Remove or rephrase; sexual orientation and gender identity are not choices",
    },
    {
        "term": "gay lifestyle",
        "severity": "biased",
        "type": "Stereotyping",
        "description": "There is no single 'gay lifestyle.' This term promotes stereotypes and reduces diverse experiences to a monolith.",
        "suggestion": "Be specific about what you mean, or remove the phrase entirely",
    },
    {
        "term": "admitted to being gay",
        "severity": "biased",
        "type": "Stigmatizing Language",
        "description": "Using 'admitted' implies that being gay is something shameful to confess.",
        "suggestion": "Use 'came out as gay' or 'shared that they are gay'",
    },
    {
        "term": "sex change",
        "severity": "outdated",
        "type": "Outdated Terminology",
        "description": "The term 'sex change' is outdated and focuses narrowly on surgery.",
        "suggestion": "Use 'gender-affirming surgery' or 'transition' depending on context",
    },
    {
        "term": "transgenders",
        "severity": "offensive",
        "type": "Grammatically Incorrect",
        "description": "Using 'transgender' as a noun is grammatically incorrect and dehumanizing.",
        "suggestion": "Use 'transgender people' or 'transgender individuals'",
    },
    {
        "term": "transgendered",
        "severity": "incorrect",
        "type": "Incorrect Grammar",
        "description": "'Transgendered' is grammatically incorrect. Transgender is an adjective, not a verb.",
        "suggestion": "Use 'transgender' (e.g., 'transgender person')",
    },
    # Hebrew terms
    {
        "term": "הומוסקסואל",
        "severity": "outdated",
        "type": "מונח מיושן",
        "description": "המונח 'הומוסקסואל' נחשב קליני ומיושן. היסטורית שימש בהקשרים פתולוגיים.",
        "suggestion": "השתמשו ב'גיי', 'לסבית', או 'אדם מקהילת הלהט\"ב'",
    },
    {
        "term": "טרנסקסואל",
        "severity": "outdated",
        "type": "מונח מיושן",
        "description": "המונח 'טרנסקסואל' מיושן ונתפס כממדיקל. הוא מתמקד במעבר רפואי ולא בזהות.",
        "suggestion": "השתמשו ב'אדם טרנסג'נדר' או 'אדם טרנס'",
    },
    {
        "term": "העדפה מינית",
        "severity": "incorrect",
        "type": "מונח שגוי",
        "description": "נטייה מינית אינה בחירה או העדפה. שימוש ב'העדפה' מרמז שניתן לשנות אותה.",
        "suggestion": "השתמשו ב'נטייה מינית'",
    },
    {
        "term": "נולד גבר",
        "severity": "offensive",
        "type": "שפה פוגענית",
        "description": "ביטוי זה פוגע בזהות המגדרית של האדם ומרמז שהמין שהוקצה בלידה קובע את המגדר.",
        "suggestion": "השתמשו ב'הוקצה זכר בלידה' אם רלוונטי רפואית",
    },
    {
        "term": "נולדה אישה",
        "severity": "offensive",
        "type": "שפה פוגענית",
        "description": "ביטוי זה פוגע בזהות המגדרית של האדם ומרמז שהמין שהוקצה בלידה קובע את המגדר.",
        "suggestion": "השתמשו ב'הוקצתה נקבה בלידה' אם רלוונטי רפואית",
    },
    {
        "term": "אנשים נורמליים",
        "severity": "biased",
        "type": "שפה מוטה",
        "description": "שימוש ב'נורמלי' לתיאור אנשים שאינם מקהילת הלהט\"ב מרמז שאנשים מהקהילה אינם נורמליים.",
        "suggestion": "השתמשו ב'סיסג'נדר' או 'הטרוסקסואל' אם מתכוונים לקבוצות אלו",
    },
]


# =============================================================================
# DEMO: Rule-Based Detection Function
# =============================================================================

def find_issues(text: str) -> list[Issue]:
    """
    DEMO/PLACEHOLDER: Find problematic terms using simple keyword matching.
    """
    issues = []
    text_lower = text.lower()

    for rule in TERM_RULES:
        term = rule["term"]
        term_lower = term.lower()

        # Find all occurrences (case-insensitive)
        start = 0
        while True:
            idx = text_lower.find(term_lower, start)
            if idx == -1:
                break

            # Get the actual text from original (preserving case)
            actual_span = text[idx:idx + len(term)]

            issues.append(Issue(
                span=actual_span,
                severity=rule["severity"],
                type=rule["type"],
                description=rule["description"],
                suggestion=rule.get("suggestion"),
                start=idx,
                end=idx + len(term),
            ))

            start = idx + len(term)

    # Sort by position in text
    issues.sort(key=lambda x: x.start)
    return issues


# =============================================================================
# ACTIVE ENDPOINT (Hybrid Detection)
# =============================================================================

from app.modules.analysis.hybrid_detector import HybridDetector

# Module-level detector instance (created once, reused)
_hybrid_detector = HybridDetector()


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_text(
    request: AnalysisRequest,
    # TODO: Re-enable auth once FastAPI Users schema matches DB
    # current_user: User = Depends(current_active_user)
):
    """
    Analyze text for non-inclusive LGBTQ+ language.

    **PRIVACY MODE:**
    When private_mode=True (default), analysis runs entirely in-memory.
    No documents, analysis_runs, or findings are persisted to the database.
    This ensures user privacy for sensitive academic content.

    **CURRENT STATUS: HYBRID DETECTION (LLM + Rules)**

    Uses LLM for contextual analysis with rule-based fallback.
    Response includes analysis_mode field indicating detection method:
    - "llm": All LLM success
    - "hybrid": Partial LLM + partial rules
    - "rules_only": LLM unavailable, rules only

    Requires authentication. User info available for logging/tracking.
    """
    # Use hybrid detector (LLM + rules fallback)
    issues, analysis_mode = await _hybrid_detector.analyze(
        request.text,
        language=request.language or "auto"
    )

    return AnalysisResponse(
        original_text=request.text,
        analysis_status="Success",
        issues_found=issues,
        corrected_text=None,  # TODO: Generate with LLM
        note=f"Found {len(issues)} issue(s). Mode: {analysis_mode}",
        analysis_mode=analysis_mode,
    )


# =============================================================================
# SAVED: FRIEND'S DB IMPLEMENTATION (Commented Out)
# =============================================================================
# TODO: Uncomment this section (and imports at top) when Docker/Postgres is running.
# --- DB PERSISTENCE (only for non-private mode) ---
# When private_mode=False, the commented code below can be enabled to persist
# documents, analysis_runs, and findings to the database.
# When private_mode=True, skip all DB operations entirely.
# -----------------------------------------------------------------------------

"""
# [CONFLICT 3 & 4 SAVED HERE] Your friend's entire logic is preserved below:

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_text(request: AnalysisRequest, conn=Depends(get_db)):
    t0 = time.time()

    await asyncio.sleep(0.3)

    issues = find_issues(request.text)

    # ---- Resolve org/user (לפי org_slug/user_email אם סופקו, אחרת "האחרונים" לדמו) ----
    org = await repo.get_org_by_slug(conn, request.org_slug) if request.org_slug else await repo.get_latest_org(conn)
    if not org:
        raise HTTPException(status_code=400, detail="No organization found. Run seed.sql or provide org_slug.")

    org_id = org["org_id"]
    default_private_mode = org["default_private_mode"]

    user = await repo.get_user_by_email(conn, request.user_email) if request.user_email else await repo.get_latest_user(conn)
    if not user:
        raise HTTPException(status_code=400, detail="No user found. Run seed.sql or provide user_email.")

    user_id = user["user_id"]
    user_org_id = user["org_id"]
    if user_org_id != org_id:
        raise HTTPException(status_code=403, detail="User does not belong to the selected organization.")

    private_mode = bool(request.private_mode) if request.private_mode is not None else bool(default_private_mode)

    # לא שומרים טקסט מלא אם private_mode=True, רק hash
    text_sha256 = hashlib.sha256(request.text.encode("utf-8")).hexdigest()

    # ---- DB transaction ----
    try:
        async with conn.transaction():
            doc_id = await repo.create_document(
                conn=conn,
                org_id=org_id,
                user_id=user_id,
                input_type="paste",
                language=request.language or "auto",
                private_mode=private_mode,
                mime_type="text/plain",
                text_storage_ref=None,
                text_sha256=text_sha256,
            )

            run_id = await repo.create_run(
                conn=conn,
                document_id=doc_id,
                model_version="rules-v0",
                status="running",
                config_snapshot={"mode": "rule-based", "language": request.language, "private_mode": private_mode},
            )

            # Insert findings + suggestions
            def map_severity(s: str) -> str:
                # mapping ל-db (low/medium/high)
                if s == "offensive":
                    return "high"
                if s in ("biased", "incorrect"):
                    return "medium"
                return "low"  # outdated

            for iss in issues:
                finding_id = await repo.insert_finding(
                    conn=conn,
                    run_id=run_id,
                    category=iss.type,
                    severity=map_severity(iss.severity),
                    start_idx=iss.start,
                    end_idx=iss.end,
                    explanation=iss.description,
                    excerpt_redacted=iss.span,
                    rule_id=None,
                    confidence=None,
                )
                if iss.suggestion:
                    await repo.insert_suggestion(
                        conn=conn,
                        finding_id=finding_id,
                        language=(request.language if request.language in ("he", "en") else "he"),
                        replacement_text=iss.suggestion,
                        rationale="Auto-suggestion from rule-based demo",
                        source_id=None,
                    )

            runtime_ms = int((time.time() - t0) * 1000)
            await repo.finish_run(conn, run_id=run_id, status="succeeded", runtime_ms=runtime_ms)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")

    return AnalysisResponse(
        original_text=request.text,
        analysis_status="Success",
        issues_found=issues,
        corrected_text=None,
        note=f"Saved to DB: document_id={doc_id}, run_id={run_id}. DEMO MODE: {len(issues)} issue(s)."
    )
"""