# Curated Training Data — Provenance (Achva-v2 retrain)

How `curated.jsonl` and the rendered `train/val.jsonl` were produced, so any training
row can be traced to its origin and transformation.

## Source
`data/combined_multilingual_20k.csv` (19,954 rows; cols `sentence, severity_label, explanation, language`;
he 9,951 / en 10,003). The synthetic dataset (Gemini-generated variations of seed sentences).

## Why this curation exists (problems found)
- **Train/inference format mismatch**: the old adapter was trained on sentence-level
  `{"severity","explanation"}`; production asks for `{"issues":[...]}`. We retrain in the
  production format (see `build_training_jsonl.py`).
- **Systematic use-mention mislabeling**: the source labels mark sentences that *describe/
  historicize/criticize* discredited views as violations. Measured on the frozen expert set,
  ~39% of violation rows are actually Correct. On the full source it is higher (see below).
- **~88% of the `explanation` column (BOTH languages) is augmentation-process meta-text**
  ("This variation maintains…", "המשפט שומר על הטון…"), not user-facing explanations.
  Training on it is what made the model emit meta-text. We DISCARD all source explanations
  and regenerate clean ones for kept violations.

## Pipeline (`relabel_and_regenerate.py` → `build_training_jsonl.py`)
1. **Sentence-quality filter**: drop rows whose *sentence* is corrupt (CJK, empty). Dropped 15.
2. **Dedup / anti-leak**: drop exact-duplicate sentences (3) and any sentence matching a frozen
   eval sentence, normalized — **100 rows matched the expert eval and were removed** (the expert
   review set was drawn from this same corpus; removing them prevents train/eval leakage). → 19,836.
3. **Use-mention relabel + regenerate (Gemma judge, `google/gemma-4-26B-A4B-it`, reasoning on)**:
   - Correct rows (3,826): kept as Correct → target `{"issues": []}` (no judge call).
   - Violation rows (16,010): judge returns keep/flip + (for keeps) category + a clean
     explanation in the sentence's language. Prompt encodes the expert's use-mention rule
     incl. "hedged/attributed propagation is still a violation."
   - **Calibration gate**: judge vs human-adjudicated expert labels = **0.879 agreement**
     (flip recall 0.903, precision 0.875) ≥ 0.85 → PASS. (Prompt refined once with a general
     principle after inspecting disagreements; small N=58, treat as directional.)
   - Result: **8,942 flipped to Correct (55.8%)**, 7,047 kept, 21 judge errors (dropped at build).
     The high flip rate is semantically correct — verified by spot-check, e.g. the source
     "Outdated" class (4,018) was overwhelmingly historical *descriptions* and collapsed to
     126 genuine assertions.
4. **Render to production format** (`build_training_jsonl.py`): system prompt imported verbatim
   from `backend/app/modules/analysis/llm_client.py`; user = production template; assistant =
   `{"issues":[]}` or `{"issues":[{phrase,category,severity,explanation}]}` (suggestion omitted —
   not generated this round). severity stays the English enum.
5. **Balance (Phase 2.5)**: the relabel left ~64% Correct; subsampled Correct (stratified by
   language) to **50%** to match the eval's natural ~50% Correct and avoid over-leniency.
   All violations kept.
6. **Split**: stratified 90/10 by (label × language).

## Outputs
| File | Location | Notes |
|---|---|---|
| `curated.jsonl` | repo (`ml/data_curated/`) | 19,836 rows pre-balance: sentence, language, label, category, phrase, explanation, origin |
| `relabel_audit.csv` | repo (`ml/data_curated/`) | every judge decision (spot-check) |
| `relabel_stats.json`, `split_stats.json`, `calibration_summary.json` | repo | metrics |
| `train.jsonl` / `val.jsonl` | **/data** (`…/curated_data/`) | rendered, ~280MB (system prompt per row); regenerable; not in git |

## Final training set
14,092 examples (50% Correct), train 12,682 / val 1,410, en 6,380 / he 6,302.
Label dist (train): Correct 6,341, Biased 2,586, Potentially Offensive 2,068, Factually
Incorrect 1,574, Outdated 113. Max token length 2,350 → `max_seq_length=2432`.

## Known limitations
- **Outdated** is tiny (113 train) — genuine Outdated-violations are rare after correct
  relabeling; expect weak Outdated recall (flagged in eval / handoff).
- **Category** is best-effort (Generalization 5,482 / Medicalization 1,543 / Demeaning 22);
  span/category precision is deferred to a future round per the runbook.
- Explanations are Gemma-authored (the originals were Gemini-authored — an upgrade).
