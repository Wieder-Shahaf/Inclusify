"""Clean-text score: % of document characters NOT flagged by any finding.

score = floor(100 * (1 - flagged_chars / total_chars))

flagged_chars is the size of the UNION of finding spans (overlapping or
duplicate findings are merged so the same character never counts twice).
All severities weigh equally by design — the score is a transparent,
verifiable quantity, and severity detail lives in the findings list.
Whole numbers only; floor (not round) so a document with any finding can
never display 100.
"""
import math


def clean_text_score(total_chars: int, spans: list[tuple[int, int]]) -> tuple[int, int]:
    """Return (integer score 0-100, merged flagged char count)."""
    if total_chars <= 0:
        return 100, 0

    clamped = sorted(
        (max(0, s), min(total_chars, e))
        for s, e in spans
        if e > s and s < total_chars and e > 0
    )
    flagged = 0
    cur_start, cur_end = None, None
    for s, e in clamped:
        if cur_end is None or s > cur_end:
            if cur_end is not None:
                flagged += cur_end - cur_start
            cur_start, cur_end = s, e
        else:
            cur_end = max(cur_end, e)
    if cur_end is not None:
        flagged += cur_end - cur_start

    return math.floor(100.0 * (1.0 - flagged / total_chars)), flagged
