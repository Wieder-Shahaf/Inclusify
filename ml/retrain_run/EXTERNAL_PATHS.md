# EXTERNAL PATHS LEDGER — for teardown

Everything heavy lives OUTSIDE the repo (root fs is tight). At the end of the run,
deleting the paths below reclaims all disk used by this retrain. Keep this current.

## Teardown command (run after human approves / archives results)
```bash
rm -rf /data/shahafw_home/inclusify_retrain
# venv is inside that root (see below), so the single rm covers it.
```

## Paths created by this run (all under one root)
| Path | Purpose | Approx size |
|---|---|---|
| `/data/shahafw_home/inclusify_retrain/` | **single root for all external artifacts** | (sum below) |
| `…/venv-train/` | Python venv (torch, trl, peft, …) | ~8–12 GB |
| `…/base_model/Qwen2.5-3B-Instruct/` | downloaded base model | ~6 GB |
| `…/checkpoints/` | trainer intermediate checkpoints | up to ~tens of GB |
| `…/adapters_new/` | candidate LoRA adapters (small) | ~tens of MB each |
| `…/logs/` | TensorBoard logs | small |
| `…/judge_cache/` | cached Gemma judge responses (relabel) | small |

## Artifacts kept IN the repo (committed, small — NOT deleted by teardown)
- `ml/retrain_run/` — RUN_LOG.md, pip_freeze.txt, baseline_metrics.json, eval_report.md, this ledger
- `ml/eval_sets/` — expert_eval.jsonl, gold_eval.jsonl, build/eval scripts, checksums
- `ml/data_curated/` — cleaning/relabel scripts, relabel_audit.csv, MANIFEST.md
- `data/curated/` — train.jsonl, val.jsonl
- `ml/training/config_h100.py`, `ml/training/train_h100.py`
- Winning candidate copied to `ml/adapters/qwen_r*_*_achva_v2/` (if any passes)

_Last updated: Phase 0._
