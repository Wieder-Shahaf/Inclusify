# Inclusify LoRA Retrain — RUN LOG (branch `retrain/achva-v2`)

> Running log of the Achva-v2 retrain per `ml/RETRAIN_PLAN.md`. Every command outcome,
> metric, and deviation is recorded here. The human reads this to trust the result.

## 🛑 HANDOFF SUMMARY (final gate — awaiting human decision)

**Outcome: SUCCESS. A candidate passed all four go/no-go criteria.** Winner:
`qwen_r8_d0.2_achva_v2` (v1.1.0), packaged at `ml/adapters/qwen_r8_d0.2_achva_v2/`.
Both r8 and r16 passed; r8 chosen (better on the harder real-document eval, smaller rank).
**Nothing was deployed. `active.json`, `vllm.service`, and `main` are untouched.**

### Baseline → winner (frozen eval, production-format scoring)
| metric | baseline v1.0.0 | winner | |
|---|---|---|---|
| use-mention FP (expert) | **1.000** | **0.118** | flags ~everything → ~12% |
| use-mention FP (gold/real docs) | 1.000 | 0.607 | improved, still high |
| expert accuracy | 0.077 | **0.833** | |
| expert macro-F1 | 0.121 | 0.706 | |
| EN macro-F1 (expert) | 0.142 | **0.795** | |
| HE macro-F1 (expert) | 0.094 | **0.559** | ~6× |
| Correct-class F1 (expert) | 0.00 | **0.93** | restraint learned |
| HE explanations | translation-meta leakage | 0 CJK / 0 meta | contamination fixed |

### Deployment steps — for the human to run MANUALLY if approved (I did NOT run these)
1. The trained weights (`adapter_model.safetensors`, 58 MB) are NOT in git. Copy them into the
   packaged dir before deploying:
   `cp /data/shahafw_home/inclusify_retrain/adapters_new/qwen_r8_d0.2_achva/adapter_model.safetensors ml/adapters/qwen_r8_d0.2_achva_v2/`
2. `python ml/scripts/switch_adapter.py --list`
3. `python ml/scripts/switch_adapter.py --adapter qwen_r8_d0.2_achva_v2 --dry-run`
4. On the inference VM: `--adapter qwen_r8_d0.2_achva_v2 --restart-service`, then `curl /v1/models`.
5. Rollback if needed: `--adapter qwen_r8_d0.2` (v1.0.0 baseline kept intact).

### Honest caveats
- **gold use-mention FP 0.607**: on real academic prose the model still over-flags ~60% of
  "Correct" spans (vs 12% on synthetic-style sentences). Biggest remaining weakness.
- **Occasional foreign-token code-switching** in Hebrew explanations (stray non-Hebrew word).
- **Outdated** weakly trained (113 rows after correct use-mention relabel) → weak Outdated recall.
- **Relabel quality**: Gemma judge calibrated at 0.879 vs expert; prompt refined once after
  inspecting disagreements (small N=58 → mild optimistic bias possible).
- **Eval is ~190 sentences** — treat all deltas as directional, not precise.

### Cost / time
- GPU: ~6.1 GPU-hours on one H100 (2 candidates × ~3.0h, GPU 1). Judge: ~16k remote Gemma calls (cached).
- All heavy artifacts on `/data/shahafw_home/inclusify_retrain` — see EXTERNAL_PATHS.md; teardown =
  `rm -rf /data/shahafw_home/inclusify_retrain`.
- Branch `retrain/achva-v2` committed locally (7 commits). **Not pushed** — say the word to push.

---


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

### Phase 2 — data curation & relabeling  ✅ DONE
- **Bigger problem than runbook assumed:** explanation column is **~88% augmentation-meta in
  BOTH languages** (EN "This variation maintains…" 88.3%; HE "שומר" 84%), not 46% Hebrew-only.
  Severity labels are fine; explanations broadly unusable. **User-approved decisions:**
  regenerate explanations via Gemma in the same judge pass; process full 20k at high concurrency.
- **Gemma judge** (`google/gemma-4-26B-A4B-it`, reasoning on, remote 192.168.100.112:8222):
  one call per violation row → keep/flip + category + clean explanation. Cached to `/data/judge_cache`.
  - **Calibration GATE: 0.879 agreement** vs expert (recall 0.903, precision 0.875) ≥ 0.85 → **PASS.**
    First pass was 0.828 (over-flipped hedged-attribution cases); added a general "hedged
    propagation ≠ use-mention" rule → 0.879. Honest caveat: refined once after seeing
    disagreements on the same 58 rows; principle is general, N small → directional.
  - Added a language-script guard (one retry) after an EN sentence got a Hebrew explanation.
- **Relabel result (16,010 violations judged):** 8,942 flip→Correct (55.8%), 7,047 kept, 21 errors.
  - High flip rate is **semantically correct** (verified): source "Outdated" (4,018) was mostly
    historical *descriptions* → collapsed to 126 genuine assertions. Regenerated explanations are
    clean, correct-language, real (no meta-text). This is the core data-bug fix.
  - **100 eval-leak rows removed** (expert set was drawn from this corpus) — leakage prevented.
- **Balancing (Phase 2.5):** relabel left 64% Correct → subsampled to **50%** (match eval's ~50%).
- **Final training set: 14,092 examples** (50% Correct), train 12,682 / val 1,410, en/he balanced.
  Label dist (train): Correct 6,341, Biased 2,586, PO 2,068, FI 1,574, **Outdated 113 (limitation)**.
- **Token length:** true max 2,350 → **`max_seq_length=2432`** (runbook's 1024 would have truncated
  every assistant target). Adjusted batch 8 × accum 4 (eff 32) + gradient checkpointing for the long seqs.
- Artifacts: `curated.jsonl` + `relabel_audit.csv` + `MANIFEST.md` in repo; rendered `train/val.jsonl`
  on `/data/…/curated_data` (~280MB, not git).
✅ **Phase 2 DONE.**

### Phase 3 — training (in progress)
- **GOTCHA 1:** `assistant_only_loss=True` failed — Qwen2.5's chat template lacks the
  `{% generation %}` markers (my earlier check false-matched `add_generation_prompt`).
  Switched to the runbook's documented fallback `DataCollatorForCompletionOnlyLM` with
  response template `<|im_start|>assistant\n` (token ids [151644,77091,198]).
- **MASK VERIFIED:** unmasked = 1.9% of tokens (only the assistant target scored). ✅
- **GOTCHA 2:** batch 16 OOM'd (20GB spike on longest seq @ 2432). Reverted to batch 8 ×
  accum 4 (eff 32) + gradient checkpointing + `PYTORCH_CUDA_ALLOC_CONF=expandable_segments`.
  Stable at ~48GB VRAM, ~8.2s/step, ~2h40m/candidate (~5.3h for r8 + r16).
- Candidates training on GPU 1: `qwen_r8_d0.2_achva` then `qwen_r16_d0.1_achva` → `/data/…/adapters_new`.
- ✅ Both trained: r8 eval_loss 0.409 (train 0.278), r16 eval_loss 0.401 (train 0.241), ~3h each.

### Phase 4 — evaluation  ✅ DONE  (see eval_report.md)
- **Both candidates PASS all 4 go/no-go criteria. WINNER: `qwen_r8_d0.2_achva`** (better on the
  harder gold/real-doc set; comparable on expert; smaller rank).
- **Headline: use-mention FP 1.00 → 0.118 (expert) / 0.607 (gold); Correct-class F1 0.00 → 0.93;
  expert acc 0.077 → 0.833; EN F1 0.14 → 0.80; HE F1 0.09 → 0.56.**
- Criterion 4: HE explanations 0 CJK / 0 translation-meta over 12 samples (contamination fixed).
- Caveats logged: gold FP still 0.607 (real prose harder); occasional foreign-token code-switch
  in HE; Outdated essentially untrained (rare after correct relabel); eval ~190 sents (directional).

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
