# Achva Feedback Data — Ingestion Plan & Model Improvement Strategy

**Date:** June 12, 2026
**Data location:** `data/Achva New Data/`

## 1. What we received (and why it's more valuable than it looks)

The drop contains two distinct assets:

### A. `מאמרים מתוקפים/` — expert-validated (gold-labeled) articles
Two documents hand-annotated by Achva domain experts with color highlights, plus `Legend.txt` mapping colors to labels:

| Color | Label | Maps to system severity |
|---|---|---|
| ורוד (pink/magenta) | biased | `biased` |
| ירוק (green) | correct | — (validated **negative** — no issue) |
| אדום (red) | factually incorrect | `factually_incorrect` |
| כחול (blue/cyan) | outdated | `outdated` |
| צהוב (yellow) | potentially offensive | `potentially_offensive` |

I verified the annotations are machine-extractable:
- `כתבה בוחרים במשפחה.docx` — 14 native Word highlight runs (9 red, 2 cyan, 2 yellow, 1 magenta).
- `2018-03783-002 (1).pdf` — **97 PDF Highlight annotations** (with paired popup/markup objects).

The crucial point: **Achva annotated in exactly our four-severity taxonomy, plus an explicit "correct" class.** This is the project's first real ground truth. Everything we've measured so far (the 79.11% adapter accuracy) was against our own synthetic/augmented data; this is the first time we can measure against the people whose judgment the tool exists to encode. The green "correct" class is the rarest kind of training signal — expert-confirmed negatives, which is precisely what we need to attack false positives.

### B. `מאמרים לבדיקה של המערכת/` — 11-article evaluation corpus
A deliberately mixed test set, unlabeled:
- **Hebrew academic texts** (ענתבי on fluidity, גרוס on LGBT rights politics, טרנסקונספציה, two Hebrew press articles) — exercises our weakest pipeline path (Hebrew detection quality).
- **Adversarial / high-density texts** (Shrier's *Irreversible Damage*, "Cass-informed psychotherapy", "Censorship of Essential Debate in Gender Medicine") — texts that should produce dense, high-severity findings. These are recall stress tests.
- **Benign/clinical baselines** (the bioethics paper s12910-024, the 2018 APA-style paper — which also appears in the validated set, giving overlap for calibration).

This composition tells us what Achva will judge us on: Hebrew coverage, recall on genuinely problematic texts, and restraint on legitimate academic discussion of contested topics.

---

## 2. Ingestion pipeline (concrete, this sprint)

**Step 1 — Extract gold annotations → `data/achva_gold/gold_annotations.jsonl`**
New script `ml/data_pipeline/extract_achva_annotations.py`:
- DOCX: walk runs with `python-docx`, capture `w:highlight` color + run text + surrounding sentence.
- PDF: use PyMuPDF (`page.annots()`) — each Highlight annot gives quads + stroke color; map quads → underlying text via `page.get_text("words")` intersection; map RGB → legend label.
- Output one record per span: `{source_doc, language, sentence, span_text, start, end, label, annotator: "achva"}`.
- Expected yield: ~110 expert spans (plus every green span as an explicit negative).

**Step 2 — Build the evaluation harness → `ml/evaluation/achva_eval.py`**
- Run each validated article through the *production* pipeline (Docling parse → chunking → LLM), not the notebook path, so we measure what users get.
- Match predictions to gold spans by character-overlap (IoU ≥ 0.5 counts as a hit; report exact-severity and any-severity separately).
- Report per-severity precision / recall / F1, plus FP rate on green ("correct") spans.

**Step 3 — Snapshot the test corpus results**
Run all 11 test articles through the pipeline and freeze the outputs as `data/achva_eval_runs/baseline_<date>/`. This becomes our regression baseline: every future adapter or prompt change gets diffed against it before deploying.

---

## 3. Five concrete ways to leverage this for model performance

1. **Honest scoreboard first.** Run the eval harness against the current `qwen_r8_d0.2` adapter before touching anything. Per-severity F1 on Achva gold is the number for the **April → July (Part B) presentations** — "79% on our synthetic set" becomes "X% agreement with Achva's own experts," a much stronger claim (or a much clearer to-do list).

2. **Confidence threshold calibration with real labels.** The frontend currently hard-filters findings to confidence 0.30–0.85 (`analyze/page.tsx`), thresholds chosen by eyeballing. With gold labels we can plot precision/recall vs. confidence per severity and set thresholds empirically — likely different cutoffs per category. This is a pure-config win available *without retraining*.

3. **Fine-tune with expert spans — but as seeds, not as a dataset.** ~110 spans is too small to fine-tune on directly without overfitting. Instead:
   - Hold out 100% of the gold set for evaluation in round one (never train on your only ground truth while it's your only ground truth).
   - Use the spans as **seeds for the existing synthesis pipeline** (`ml/data_synthesis/`): generate paraphrases and contextual variants of each expert-flagged phrase, and — critically — variants of the **green spans as hard negatives**. A few thousand expert-anchored synthetic examples, mixed into `augmented_dataset.csv`, targets exactly the error modes Achva cares about.
   - Once Achva validates more articles (see §4), graduate to a proper train/test split.

4. **Hebrew gap analysis.** The Hebrew test articles + the Hebrew validated docx give us the first measure of the HE pipeline end-to-end (Docling Hebrew extraction → Hebrew prompting → Hebrew category names, which the admin dashboard already normalizes). If Hebrew F1 lags English significantly, the next LoRA round should oversample Hebrew synthesis — we already have the `combine_multilingual_datasets.py` machinery for it.

5. **False-positive audit against the adversarial set.** The Shrier/Cass/censorship texts will generate hundreds of findings. Have Achva review a *sample* (say, 30 findings per document, stratified by severity) rather than everything — each reviewed finding becomes a new labeled example. This is the cheapest possible labeling protocol: experts judge our outputs (binary correct/incorrect + severity fix) instead of annotating raw documents.

---

## 4. Close the loop: make this a recurring workflow, not a one-off

We already have the infrastructure for a continuous improvement cycle — it just isn't connected:

```
users vote 👍/👎 on findings  ──►  feedback table (already live)
                                        │
        admin dashboard Feedback tab (already live)
                                        │ monthly export
                                        ▼
        Achva expert review (the workflow this data drop just established:
        highlights in their own taxonomy)
                                        │
                                        ▼
   gold_annotations.jsonl grows ──► eval scoreboard + synthesis seeds
                                        │
                                        ▼
            next LoRA refresh ──► regression-diff vs frozen baseline ──► deploy
```

Proposed cadence and ownership (matching current team roles):
- **Lama (doc pipeline):** extraction script (§2 step 1) — the DOCX/PDF highlight parsing is squarely a document-pipeline task.
- **Barak (ML/vLLM):** eval harness, baseline run, threshold calibration, seeded synthesis + next adapter round.
- **Rasha (backend/infra):** monthly feedback-export endpoint/script (down-voted findings → CSV for Achva).
- **Shahaf (PM):** agree the review protocol + cadence with Achva (one batch before the **July 8 Part B presentation**; the validated-articles format they chose works — just ask them to keep using the same five colors).

**Definition of done for this data drop:** gold JSONL extracted and committed; baseline eval report (per-severity F1 + Hebrew vs English split) checked into `ml/evaluation/`; thresholds recalibrated if the data supports it; one slide of "expert agreement" numbers ready for the next presentation.
