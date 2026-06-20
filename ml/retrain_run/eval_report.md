# Phase 4 — Evaluation Report (Achva-v2 retrain)

All numbers from `ml/eval_sets/run_eval.py` (production-format scoring) against the
**frozen** eval sets: `expert_eval` (100 expert-adjudicated rows; strict = 78 after
excluding 22 context-dependent) and `gold_eval` (65 sentences from expert-highlighted
real documents). Eval is ~190 sentences — **small, so treat deltas as directional.**

## Baseline vs candidates

### expert_eval (strict, context-dependent excluded)
| model | acc | macro-F1 | EN F1 | HE F1 | use-mention FP |
|---|---|---|---|---|---|
| baseline `qwen_r8_d0.2` | 0.077 | 0.121 | 0.142 | 0.094 | **1.000** (51/51) |
| **r8_d0.2_achva** | **0.833** | **0.706** | 0.795 | 0.559 | **0.118** (6/51) |
| r16_d0.1_achva | 0.846 | 0.726 | 0.795 | 0.561 | 0.098 (5/51) |

### gold_eval (real highlighted documents — harder)
| model | acc | macro-F1 | EN F1 | HE F1 | use-mention FP |
|---|---|---|---|---|---|
| baseline `qwen_r8_d0.2` | 0.062 | 0.046 | 0.010 | 0.236 | **1.000** (28/28) |
| **r8_d0.2_achva** | **0.262** | **0.221** | 0.164 | 0.338 | **0.607** (17/28) |
| r16_d0.1_achva | 0.200 | 0.168 | 0.126 | 0.263 | 0.714 (20/28) |

### Per-label F1, expert strict (baseline → r8)
| label | F1 | support |
|---|---|---|
| Correct | 0.00 → **0.93** | 51 |
| Biased | 0.11 → **0.69** | 14 |
| Potentially Offensive | 0.19 → **0.84** | 8 |
| Factually Incorrect | 0.18 → **0.36** | 5 |
| Outdated | n/a (0 strict-expert cases; all adjudicated-Outdated were context-dependent) | 0 |

## Go / No-Go criteria
| # | Criterion | r8 | r16 |
|---|---|---|---|
| 1 | Use-mention FP **strictly decreases** vs baseline (1.00) | ✅ 0.118 expert / 0.607 gold | ✅ 0.098 / 0.714 |
| 2 | Hebrew macro-F1 **increases** vs baseline | ✅ 0.094→0.559 / 0.236→0.338 | ✅ →0.561 / →0.263 |
| 3 | English macro-F1 **doesn't regress >2pts** | ✅ improved hugely (0.142→0.795) | ✅ same |
| 4 | No CJK / translation-meta in HE explanations | ✅ 0 CJK, 0 meta over 12 samples | (winner only) |

**Both candidates PASS all four. Winner: `r8_d0.2_achva`.**

### Why r8 over r16
- **Better on `gold_eval`** (the harder, real-document set, closest to production input):
  use-mention FP 0.607 vs 0.714, macro-F1 0.221 vs 0.168, HE F1 0.338 vs 0.263.
- Comparable on expert (r16 marginally better: acc 0.846 vs 0.833, FP 0.098 vs 0.118).
- r16 has the lower train loss (0.241 vs 0.278) but worse gold generalization → mild overfit.
- Runbook prefers the smaller rank when comparable; r8 matches the current production rank
  (T4 `--max-lora-rank 16` safe either way).

## Headline
The single highest-value fix landed: **use-mention false-positive rate dropped from 1.00 to
0.118** on the expert set (the model went from flagging 100% of correct sentences to ~12%),
Correct-class F1 went **0.00 → 0.93**, and every violation class improved. Hebrew F1 ~6×.

## Honest caveats / limitations
- **gold use-mention FP is still 0.607** — on real academic prose the model over-flags ~60% of
  expert-"Correct" spans (vs 12% on synthetic-style expert sentences). It learned restraint well
  for synthetic-style inputs, less so for real-document distribution. Still ≫ better than 1.00.
- **Foreign-token code-switching in Hebrew**: occasional stray non-Hebrew tokens appear mid-
  explanation (e.g. a Vietnamese/German word) in ~a third of HE outputs. Not CJK/translation-meta
  (so criterion 4 passes literally), but a real fluency issue for a later round.
- **Outdated** is essentially untrained (113 training rows after correct use-mention relabeling;
  0 strict-expert test cases) — expect weak Outdated detection. Documented data limitation.
- **Eval is ~190 sentences** — deltas are directional, not precise.
- Category/suggestion fields not rigorously evaluated this round (span/category precision deferred).
