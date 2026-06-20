# qwen_r8_d0.2_achva_v2 (v1.1.0) — CANDIDATE, not deployed

LoRA adapter for `Qwen/Qwen2.5-3B-Instruct`, retrained on the Achva-v2 curated data.
Supersedes `qwen_r8_d0.2` (v1.0.0). **Awaiting human approval — not promoted.**

## What changed vs v1.0.0
1. **Trained in the production format.** v1.0.0 was trained on sentence-level
   `{"severity","explanation"}` but used in production for `{"issues":[...]}` phrase
   extraction. This adapter is trained on the exact production system prompt + the
   `{"issues":[...]}` target — the root-cause fix for code-switching / over-flagging.
2. **Use-mention relabeling.** Training labels systematically marked sentences that
   *describe/historicize/criticize* discredited views as violations. A Gemma-4-26B judge
   (calibrated 0.879 vs the expert set) relabeled them; ~56% of source "violations" were
   actually Correct. Empty-issues (`{"issues":[]}`) targets teach restraint.
3. **Hebrew (and English) explanations regenerated.** ~88% of source explanations were
   augmentation-process meta-text ("…שומר על הטון", "This variation maintains…"); all were
   discarded and replaced with clean, in-language explanations.

## Eval (frozen sets, production-format scoring — see ml/retrain_run/eval_report.md)
| metric | baseline v1.0.0 | this adapter |
|---|---|---|
| use-mention FP (expert) | 1.000 | **0.118** |
| use-mention FP (gold/real docs) | 1.000 | **0.607** |
| expert accuracy | 0.077 | **0.833** |
| EN macro-F1 (expert) | 0.142 | **0.795** |
| HE macro-F1 (expert) | 0.094 | **0.559** |

## Serving compatibility
- Standalone PEFT adapter (`adapter_config.json` + `adapter_model.safetensors`), rank 8 ≤ 16,
  same base + target modules as v1.0.0 → loads on the production T4 (fp16, `--max-lora-rank 16`)
  unchanged. Verified by an fp16-base + adapter load smoke test (EN flagged, HE use-mention abstained).
- **`adapter_model.safetensors` (58 MB) is committed via Git LFS** (`.gitattributes` routes
  `*.safetensors` to LFS). A fresh clone needs `git lfs pull` to materialize the weights.
  A copy also lives at `/data/shahafw_home/inclusify_retrain/adapters_new/qwen_r8_d0.2_achva/`.

## Known limitations
- **gold use-mention FP 0.607** — still over-flags ~60% of "Correct" spans in real academic prose
  (vs 12% on synthetic-style sentences). Restraint generalizes less well to real-document distribution.
- **Occasional foreign-token code-switching** in Hebrew explanations (stray non-Hebrew word).
- **Outdated** weakly trained (113 rows after correct relabeling) → weak Outdated detection.
- **Category/suggestion** fields are best-effort; span/category precision deferred to a future round.
- Eval is ~190 sentences — deltas are directional, not precise.
