#!/usr/bin/env python3
"""Phase 1.1 — Build the frozen expert evaluation set.

Source: data/Achva New Data/inclusify_review_set_with_expert_notes.xlsx, sheet
"Review Set" (100 rows: 50 EN, 50 HE, 20 per original Label).

The `Label` column is the MODEL's original verdict. The `Expert Notes` column is
the SOURCE OF TRUTH. We derive an `adjudicated_label` per the runbook rule:
  - note plainly agrees                          -> keep original Label  (tag: agree)
  - note says sentence merely describes/criticizes
    a discredited view (use-mention)             -> adjudicated = Correct (tag: flip)
  - note states a different specific label       -> use note's label     (tag: relabel)
  - note is genuinely context-dependent
    ("offensive only if used to justify…")       -> keep original label,
                                                    context_dependent=True, EXCLUDED
                                                    from the strict metric (tag: context)

WHY A REVIEWED TABLE, NOT REGEX: the notes use "Correct"/"נכון" to mean opposite
things depending on context (row 0 affirms a Correct label; row 17 "Correct. It is
not offensive to point that out" FLIPS a Potentially-Offensive label). A lexical
rule both over- and under-flips on exactly the axis this eval must measure. So the
adjudication below was produced by reading all 100 expert notes once and encoding
the result. Every record carries the original note + tag so a human can audit it.

Output: ml/eval_sets/expert_eval.jsonl  (+ .sha256 checksum, frozen thereafter).
"""

import hashlib
import json
import os

import openpyxl

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
XLSX = os.path.join(REPO, "data", "Achva New Data", "inclusify_review_set_with_expert_notes.xlsx")
OUT = os.path.join(os.path.dirname(__file__), "expert_eval.jsonl")

LABELS = {"Correct", "Outdated", "Biased", "Potentially Offensive", "Factually Incorrect"}

# Per-row adjudication, keyed by 0-based data-row index (matches sheet order).
# (adjudicated_label, context_dependent, tag)
PO, OUT_L, FI, BI, COR = (
    "Potentially Offensive", "Outdated", "Factually Incorrect", "Biased", "Correct",
)
ADJ = {
    # EN Correct (0-9) — all agree
    0: (COR, False, "agree"), 1: (COR, False, "agree"), 2: (COR, False, "agree"),
    3: (COR, False, "agree"), 4: (COR, False, "agree"), 5: (COR, False, "agree"),
    6: (COR, False, "agree"), 7: (COR, False, "agree"), 8: (COR, False, "agree"),
    9: (COR, False, "agree"),
    # EN Potentially Offensive (10-19)
    10: (PO, True, "context"), 11: (PO, False, "agree"), 12: (PO, False, "agree"),
    13: (PO, False, "agree"), 14: (PO, False, "agree"), 15: (PO, False, "agree"),
    16: (PO, True, "context"), 17: (COR, False, "flip"), 18: (COR, False, "flip"),
    19: (COR, False, "flip"),
    # EN Outdated (20-29)
    20: (COR, False, "flip"), 21: (OUT_L, True, "context"), 22: (OUT_L, True, "context"),
    23: (COR, False, "flip"), 24: (OUT_L, True, "context"), 25: (COR, False, "flip"),
    26: (OUT_L, True, "context"), 27: (COR, False, "flip"), 28: (OUT_L, True, "context"),
    29: (COR, False, "flip"),
    # EN Factually Incorrect (30-39)
    30: (FI, True, "context"), 31: (FI, False, "agree"), 32: (COR, False, "flip"),
    33: (COR, False, "flip"), 34: (FI, False, "agree"), 35: (FI, False, "agree"),
    36: (BI, False, "relabel"), 37: (FI, False, "agree"), 38: (FI, True, "context"),
    39: (COR, False, "flip"),
    # EN Biased (40-49)
    40: (BI, False, "agree"), 41: (BI, True, "context"), 42: (BI, False, "agree"),
    43: (COR, False, "flip"), 44: (BI, True, "context"), 45: (BI, False, "agree"),
    46: (BI, False, "agree"), 47: (COR, False, "flip"), 48: (BI, False, "agree"),
    49: (BI, False, "agree"),
    # HE Correct (50-59) — all agree (notes are terminology fixes; sentence is correct)
    50: (COR, False, "agree"), 51: (COR, False, "agree"), 52: (COR, False, "agree"),
    53: (COR, False, "agree"), 54: (COR, False, "agree"), 55: (COR, False, "agree"),
    56: (COR, False, "agree"), 57: (COR, False, "agree"), 58: (COR, False, "agree"),
    59: (COR, False, "agree"),
    # HE Potentially Offensive (60-69)
    60: (PO, False, "agree"), 61: (COR, False, "flip"), 62: (COR, False, "flip"),
    63: (PO, False, "agree"), 64: (PO, True, "context"), 65: (PO, True, "context"),
    66: (COR, False, "flip"), 67: (PO, False, "agree"), 68: (PO, True, "context"),
    69: (COR, False, "flip"),
    # HE Outdated (70-79)
    70: (COR, False, "flip"), 71: (OUT_L, True, "context"), 72: (OUT_L, True, "context"),
    73: (COR, False, "flip"), 74: (COR, False, "flip"), 75: (OUT_L, True, "context"),
    76: (OUT_L, True, "context"), 77: (COR, False, "flip"), 78: (OUT_L, True, "context"),
    79: (COR, False, "flip"),
    # HE Factually Incorrect (80-89)
    80: (FI, True, "context"), 81: (COR, False, "flip"), 82: (FI, False, "agree"),
    83: (COR, False, "flip"), 84: (COR, False, "flip"), 85: (COR, False, "flip"),
    86: (COR, False, "flip"), 87: (COR, False, "flip"), 88: (COR, False, "flip"),
    89: (COR, False, "flip"),
    # HE Biased (90-99)
    90: (BI, False, "agree"), 91: (BI, False, "agree"), 92: (BI, True, "context"),
    93: (BI, False, "agree"), 94: (COR, False, "flip"), 95: (BI, False, "agree"),
    96: (BI, False, "agree"), 97: (BI, True, "context"), 98: (BI, False, "agree"),
    99: (BI, False, "agree"),
}


def main():
    wb = openpyxl.load_workbook(XLSX, data_only=True)
    ws = wb["Review Set"]
    rows = [r for r in ws.iter_rows(values_only=True)][1:]
    data = [r for r in rows if any(c is not None for c in r)]
    assert len(data) == 100, f"expected 100 rows, got {len(data)}"
    assert len(ADJ) == 100, f"adjudication table must have 100 entries, has {len(ADJ)}"

    from collections import Counter
    orig_c, adj_c, tag_c = Counter(), Counter(), Counter()
    n_ctx = 0
    records = []
    for i, r in enumerate(data):
        lang = str(r[0]).strip().lower()      # EN/HE -> en/he
        sentence = str(r[1]).strip()
        original = str(r[2]).strip()
        explanation = (str(r[3]).strip() if r[3] else "")
        note = (str(r[4]).strip() if r[4] else "")
        adj_label, ctx, tag = ADJ[i]
        assert original in LABELS, f"row {i}: bad original label {original!r}"
        assert adj_label in LABELS, f"row {i}: bad adjudicated label {adj_label!r}"
        records.append({
            "row": i,
            "lang": lang,
            "sentence": sentence,
            "original_label": original,
            "adjudicated_label": adj_label,
            "context_dependent": ctx,
            "adjudication_tag": tag,      # agree | flip | relabel | context
            "explanation": explanation,
            "note": note,
        })
        orig_c[original] += 1
        adj_c[adj_label] += 1
        tag_c[tag] += 1
        n_ctx += int(ctx)

    with open(OUT, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # checksum (freeze)
    h = hashlib.sha256(open(OUT, "rb").read()).hexdigest()
    with open(OUT + ".sha256", "w") as f:
        f.write(h + "  expert_eval.jsonl\n")

    print(f"wrote {len(records)} records -> {OUT}")
    print(f"sha256: {h}")
    print(f"original label dist : {dict(orig_c)}")
    print(f"adjudicated label dist: {dict(adj_c)}")
    print(f"adjudication tags    : {dict(tag_c)}")
    print(f"context_dependent (excluded from strict metric): {n_ctx}")
    flips = tag_c.get("flip", 0)
    n_viol_orig = sum(v for k, v in orig_c.items() if k != "Correct")
    print(f"use-mention flips to Correct: {flips} "
          f"({100*flips/max(1,n_viol_orig):.1f}% of {n_viol_orig} originally-violation rows)")


if __name__ == "__main__":
    main()
