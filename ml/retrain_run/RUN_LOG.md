# Inclusify LoRA Retrain — RUN LOG (branch `retrain/achva-v2`)

> Running log of the Achva-v2 retrain per `ml/RETRAIN_PLAN.md`. Every command outcome,
> metric, and deviation is recorded here. The human reads this to trust the result.

## HANDOFF SUMMARY (filled at the final gate)
_TBD — populated in Phase 5._

---

## Environment (Phase 0)

| Fact | Value |
|---|---|
| Start (UTC) | 2026-06-20T13:37Z |
| Host | `ziv` (this is the H100 box; judge runs on a separate host) |
| Branch | `retrain/achva-v2` (off `main` @ `dc99a6e`) |
| GPUs | 4× NVIDIA H100 80GB. **GPU 1 free (0 MiB) → training.** GPU 0 ~6.5GB used; GPU 2&3 ~50GB each (local Qwen3 vLLM serving on :8078, leave alone). |
| Driver / CUDA | 570.195.03 / CUDA 12.8 (no `nvcc` toolkit — torch wheels bundle runtime, fine) |
| Python | 3.10.12 (**deviation**: runbook expected 3.11/3.12; stack runs on 3.10) |
| CPU / RAM | 128 cores / 1.0 TiB |
| Repo disk `/` | 98G total, ~18G free (tight — keep heavy artifacts OFF this fs) |
| Heavy-artifact disk | `/data` (local, 14T, 5.6T free) |
| External work root | `/data/shahafw_home/inclusify_retrain` (owned by me; teardown = delete this dir + venv) |

### Judge endpoint (remote, over network)
- URL: `http://192.168.100.112:8222/v1` — reachable from this box (verified `/v1/models` + chat OK).
- Model: `google/gemma-4-26B-A4B-it` (26B MoE, ~4B active) — comfortably stronger than the 3B being trained. `max_model_len` 65536, `allow_logprobs: true`.
- Reasoning: enable via `extra_body={"chat_template_kwargs": {"thinking": True}}`; reasoning text in `message.reasoning_content`.
- Used ONLY as the Phase-2.2 use-mention relabel judge, gated by ≥85% calibration vs expert.

### Deviations from runbook (intentional, with reason)
1. **Storage**: runbook used repo-relative `ml/base_model/`, `ml/adapters_new/`. Root fs has only 18G free, so heavy artifacts go to `/data/shahafw_home/inclusify_retrain/...` and `config_h100.py` points there. Repo keeps only small artifacts.
2. **Judge**: runbook said download a 32B/72B judge locally. Instead we use the existing remote Gemma-4-26B-A4B API (no local GPU/disk cost, isolated VM still respected — call is LAN-only).
3. **Python 3.10** instead of 3.11/3.12.
4. **Training GPU pinned to `CUDA_VISIBLE_DEVICES=1`** to avoid the busy serving GPUs.

### Recon findings that shape later phases
- **Severity labels in all 10k CSVs exactly match the prod enum**: `Outdated | Biased | Potentially Offensive | Factually Incorrect | Correct`. No normalization needed.
- **No `category` column** in `english_10k.csv` / `hebrew_10k.csv` (cols: `sentence,severity_label,explanation`). Prod requires `category ∈ {Medicalization, Generalization, Demeaning Terminology}`. → Phase 2.4 must assign category (judge-emitted or heuristic). The 100-row `Inclusify_Dataset.csv` / 1k `augmented_dataset.csv` DO have `Rule Category`.
- **Hebrew translation-meta worse than runbook's 46%**: `שומר`=84% (too broad to drop on), but targeted markers — `שומר על הטון`=8.4%, `התרגום`=7%, `הגרסה`=8.2%, `דקדוק עברי`=1.4%, `התאמה להקשר`=0.9%, CJK=0.2%. → clean on the *targeted* set, not bare `שומר`.
- **Prod user template** (exact): `Analyze this passage for LGBTQ+ inclusive language compliance:\n"{sentence}"`.
- **Prod SYSTEM_PROMPT** ≈9,443 chars (~1.9k tokens) at `backend/app/modules/analysis/llm_client.py:26-88` — import verbatim, do not copy.
- **Old training format** (`prepare_data.py::format_example_qwen`) = sentence-level `{"severity","explanation"}` — confirms the train/inference mismatch the runbook targets.
- **Old config** (`ml/training/config.py`): 4-bit NF4, fp16=False/bf16=False, bs=4, adamw_8bit, max_seq=512, hardcoded `/home/azureuser/...` paths → all overridden in `config_h100.py`.
- **`trl` + `tensorboard` missing** from `ml/requirements.txt` — install explicitly.

---

## Phase log

### Phase 0 — Environment bring-up  ✅ DONE
- [x] Branch `retrain/achva-v2` created off `main@dc99a6e`.
- [x] External work root + subdirs created on `/data/shahafw_home/inclusify_retrain`.
- [x] Repo dirs created: `ml/retrain_run`, `ml/eval_sets`, `ml/data_curated`, `data/curated`.
- [x] venv + deps installed; `pip_freeze.txt` written.
  - **GOTCHA:** `~/.config/pip/pip.conf` forces an expired private AWS CodeArtifact
    index (401). First install silently failed for everything except torch (which
    had an explicit `--index-url`). Fixed by `pip config --site set global.index-url
    https://pypi.org/simple` (writes venv-local pip.conf). Re-ran cleanly.
  - Stack: torch 2.6.0+cu124 (CUDA✓, bf16✓), transformers 4.57.6 (capped <5),
    peft 0.19.1, trl 0.19.1, datasets 5.0.0, accelerate 1.14.0, bitsandbytes 0.49.2.
  - Completion-only loss: BOTH `SFTConfig.assistant_only_loss=True` AND
    `DataCollatorForCompletionOnlyLM` are available in trl 0.19.1.
- [x] Base model downloaded: `…/base_model/Qwen2.5-3B-Instruct` (5.8 GB, ungated, no HF token needed).
  - Smoke test: loads on GPU 1 in bf16 in 2.5s, 6.2 GB peak VRAM, generates correctly.
- [x] Data inventory confirmed (all CSVs + Achva xlsx/docx/pdf/Legend present).
- [x] `config_h100.py` written.
- [ ] Phase 0 committed (next).

### Phase 1 — frozen eval (in progress)
- [x] `expert_eval.jsonl` built (100 rows) + sha256 frozen. **Adjudication done by reading
  all 100 expert notes (encoded as a reviewed table in build_expert_eval.py), not regex,
  because notes use "Correct"/"נכון" with opposite meanings by context.**
  - Original label dist: 20 each (Correct/PO/Outdated/FI/Biased).
  - **Adjudicated: Correct 51, Biased 18, PO 13, Outdated 10, FI 8.**
  - Tags: agree 46, flip 31, context 22, relabel 1.
  - **HEADLINE: 31/80 (38.8%) of violation rows are use-mention FALSE POSITIVES that
    flip to Correct** — confirms (exceeds) the runbook's ~32% use-mention claim. 22 rows
    context-dependent → excluded from the strict accuracy metric, reported separately.
- [x] `gold_eval.jsonl` built from highlighted DOCX (Hebrew) + PDF (English) + sha256.
  - 91 span records (deduped from 109): Correct 42, Biased 16, Outdated 13, PO 12, FI 8; 79 EN + 12 HE.
  - 65 distinct sentences; 10 carry >1 label (phrase-level spans of different colors).
  - **Kept as raw per-span truth.** Sentence-level collapse (Correct iff all spans Correct,
    else highest-severity violation) is done in `run_eval.py`, not baked into the frozen file.
  - Combined eval = 100 expert + 91 gold ≈ 191 sentences (small → deltas are directional).
- [x] `run_eval.py` written (production-format scoring; imports prod SYSTEM_PROMPT/SEVERITY_MAP
  via AST, no backend deps). Gold spans collapsed to one verdict/sentence in the scorer.
- [x] **Baseline measured** (current prod adapter `qwen_r8_d0.2`) → `baseline_metrics.json`.
  - **GOTCHA:** the adapter weights were missing from the repo working tree (removed in commit
    `5fa0bb8 "remove large binary"`; `.gitattributes` marks `*.safetensors` as LFS). Recovered
    the real 57MB weights from git history `git cat-file -p 8a19e7d:…/adapter_model.safetensors`
    → reconstructed full adapter at `/data/shahafw_home/inclusify_retrain/baseline_adapter/qwen_r8_d0.2`
    (repo dir left untouched per runbook; weights kept off git).

  | set | acc | macro-F1 | EN F1 | HE F1 | use-mention FP | parse_fail |
  |---|---|---|---|---|---|---|
  | expert (78 strict) | 0.077 | 0.121 | 0.142 | 0.094 | **1.00** | 1 |
  | gold (65) | 0.062 | 0.046 | 0.010 | 0.236 | **1.00** | 1 |

  - **The baseline predicted "Correct" exactly ONCE in 165 sentences.** It emits valid
    `{"issues":[...]}` JSON (base in-context ability) but flags ~99% of everything — zero restraint.
    Verified real via raw outputs: clean sentences flagged with absurd rationales; Hebrew outputs
    leak translation-meta ("המשפט שומר על ההקשר…"). This is exactly the train/inference-format
    mismatch + Hebrew contamination the retrain targets. **Baseline is honest, not a scoring bug.**
  - Headline target for the retrain: drive use-mention FP from 1.00 → low, lift HE/EN F1.

✅ **Phase 1 DONE.** Eval sets frozen (checksummed), baseline recorded. Files now read-only.
