#!/usr/bin/env python3
"""Phase 1.2 — Build the frozen gold evaluation set from expert-highlighted docs.

Two source documents in data/Achva New Data/מאמרים מתוקפים/ where the Achva expert
highlighted spans in the Legend.txt severity colors:
    biased=pink, correct=green, factually incorrect=red, outdated=blue, potentially offensive=yellow

  - DOCX (Hebrew): python-docx run.font.highlight_color → label
  - PDF  (English): PyMuPDF Highlight annots; stroke RGB → nearest legend color → label

Per highlight we emit the highlighted span + its containing sentence (the model is
scored on the sentence, production-style). Output: ml/eval_sets/gold_eval.jsonl
(+ .sha256). Frozen thereafter.
"""

import hashlib
import json
import os
import re

import fitz  # PyMuPDF
from docx import Document

HERE = os.path.dirname(__file__)
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
DOC_DIR = os.path.join(REPO, "data", "Achva New Data", "מאמרים מתוקפים")
DOCX = os.path.join(DOC_DIR, "כתבה בוחרים במשפחה.docx")
PDF = os.path.join(DOC_DIR, "2018-03783-002 (1).pdf")
OUT = os.path.join(HERE, "gold_eval.jsonl")

# Canonical labels (match production severity enum + Correct)
BIASED, CORRECT, FI, OUTDATED, PO = (
    "Biased", "Correct", "Factually Incorrect", "Outdated", "Potentially Offensive",
)

# DOCX highlight enum name -> label
DOCX_COLOR = {
    "PINK": BIASED, "BRIGHT_GREEN": CORRECT, "GREEN": CORRECT, "RED": FI,
    "BLUE": OUTDATED, "DARK_BLUE": OUTDATED, "TURQUOISE": OUTDATED, "CYAN": OUTDATED,
    "YELLOW": PO,
}

# PDF stroke-RGB anchors (observed) -> label; nearest-euclidean match
PDF_ANCHORS = [
    ((0.49, 0.94, 0.40), CORRECT),
    ((1.00, 0.94, 0.40), PO),
    ((0.97, 0.60, 0.82), BIASED),
    ((0.56, 0.87, 0.98), OUTDATED),
    ((0.92, 0.29, 0.29), FI),
]


def nearest_label(rgb):
    if not rgb:
        return None
    best, bl = 1e9, None
    for anchor, lab in PDF_ANCHORS:
        d = sum((a - b) ** 2 for a, b in zip(anchor, rgb))
        if d < best:
            best, bl = d, lab
    return bl


def norm(text):
    """De-hyphenate line breaks and collapse whitespace."""
    if not text:
        return ""
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)  # join "wor-\nd"
    text = text.replace("\n", " ")
    return re.sub(r"\s+", " ", text).strip()


_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|(?<=[।׃])\s+")


def split_sentences(text):
    parts = [s.strip() for s in _SENT_SPLIT.split(text) if s.strip()]
    return parts or ([text.strip()] if text.strip() else [])


def containing_sentence(full_text, span):
    """Return the sentence in full_text that best contains span (fuzzy fallback)."""
    sents = split_sentences(full_text)
    span_n = norm(span)
    if not span_n:
        return ""
    for s in sents:
        if span_n in s:
            return s
    # fallback: match on first 4 words of span
    head = " ".join(span_n.split()[:4])
    if head:
        for s in sents:
            if head in s:
                return s
    # fallback: longest sentence sharing words with span (else span itself)
    return span_n


def extract_docx():
    recs = []
    doc = Document(DOCX)
    src = os.path.basename(DOCX)
    for p in doc.paragraphs:
        para = norm(p.text)
        if not para:
            continue
        # merge consecutive highlighted runs of the same color into one span
        cur_color, cur_text = None, ""
        spans = []
        for run in p.runs:
            c = run.font.highlight_color
            cname = str(c).split(" ")[0] if c is not None else None
            if cname and cname in DOCX_COLOR:
                if cname == cur_color:
                    cur_text += run.text
                else:
                    if cur_text.strip():
                        spans.append((cur_color, cur_text))
                    cur_color, cur_text = cname, run.text
            else:
                if cur_text.strip():
                    spans.append((cur_color, cur_text))
                cur_color, cur_text = None, ""
        if cur_text.strip():
            spans.append((cur_color, cur_text))
        for cname, stext in spans:
            span = norm(stext)
            if len(span) < 2:
                continue
            recs.append({
                "source_doc": src, "lang": "he", "color": cname,
                "label": DOCX_COLOR[cname], "span_text": span,
                "sentence": containing_sentence(para, span),
            })
    return recs


def extract_pdf():
    recs = []
    doc = fitz.open(PDF)
    src = os.path.basename(PDF)
    for page in doc:
        full = norm(page.get_text("text"))
        for a in (page.annots() or []):
            if a.type[1].lower() != "highlight":
                continue
            label = nearest_label(a.colors.get("stroke"))
            if label is None:
                continue
            # quadpoints can cover multiple lines; union them for the text
            span = norm(page.get_textbox(a.rect))
            if len(span) < 2:
                continue
            recs.append({
                "source_doc": src, "lang": "en", "color": str(a.colors.get("stroke")),
                "label": label, "span_text": span,
                "sentence": containing_sentence(full, span),
            })
    return recs


def main():
    from collections import Counter
    recs = extract_docx() + extract_pdf()
    # dedup on (source_doc, sentence, span_text, label)
    seen, deduped = set(), []
    for r in recs:
        k = (r["source_doc"], r["sentence"], r["span_text"], r["label"])
        if k in seen:
            continue
        seen.add(k)
        deduped.append(r)

    with open(OUT, "w", encoding="utf-8") as f:
        for r in deduped:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    h = hashlib.sha256(open(OUT, "rb").read()).hexdigest()
    with open(OUT + ".sha256", "w") as f:
        f.write(h + "  gold_eval.jsonl\n")

    print(f"raw spans: {len(recs)}  deduped: {len(deduped)}  -> {OUT}")
    print(f"sha256: {h}")
    print("per-label:", dict(Counter(r["label"] for r in deduped)))
    print("per-lang :", dict(Counter(r["lang"] for r in deduped)))
    # quick sentence-quality signal: how many spans got a real (longer) sentence vs fell back to span
    fellback = sum(1 for r in deduped if r["sentence"] == r["span_text"])
    print(f"sentence==span (fallback / very short): {fellback}/{len(deduped)}")


if __name__ == "__main__":
    main()
