# LoRA Retrain Runbook — Inclusify (Qwen2.5-3B + LoRA) on H100 DGX

**Audience:** Claude Code running in auto mode (Fable, high effort) on a fresh H100 DGX VM.
**Goal:** Retrain the Inclusify LoRA adapter end-to-end — from a freshly cloned repo to a packaged, evaluated candidate adapter — fixing the concrete quality problems documented below. You operate autonomously; the human is not watching. Follow this runbook top to bottom. Where a decision is required, the decision has already been made for you and the rationale is given. Stop only at the explicit **🛑 HUMAN GATE** markers.

---

## 0. Context you must internalize before doing anything

This is not a "rerun the old training script" task. Investigation of the existing pipeline and the new Achva data surfaced **four problems** that this retrain exists to fix. If you finish without addressing them, you have failed the task even if a model trains successfully.

1. **Train/inference format mismatch (root cause of most quality issues).**
   - The adapter was *trained* on sentence-level classification: input = one sentence, output = `{"severity": ..., "explanation": ...}` (see `ml/training/prepare_data.py::format_example_qwen`).
   - In *production* it is asked for phrase-level extraction: output = `{"issues": [{"phrase","category","severity","explanation","suggestion"}]}` (see `backend/app/modules/analysis/llm_client.py::SYSTEM_PROMPT`).
   - The model was never trained on the format it's used in. It survives on base-model in-context ability, which is exactly why it code-switches, parrots few-shot examples, and degrades badly in Hebrew.
   - **DECISION (made for you): align training to the production format.** This is the single highest-value change. See Phase 2.

2. **Use-mention confusion (the expert's #1 complaint).** ~32% of expert-reviewed samples were mislabeled: sentences that *describe or criticize* a discredited/pathologizing view were labeled Outdated/Offensive as if they *endorsed* it. Inclusify's users write critical academic prose about LGBTQ+ topics — a model that flags critical scholarship is unusable. The training labels themselves carry this bias. **You must relabel for it (Phase 2), not just prompt around it.**

3. **Hebrew data quality.** `data/hebrew_10k.csv` is machine-translated; ~46% of its `explanation` fields contain leaked translation-process commentary ("התרגום שומר על הטון האקדמי…") instead of real explanations, plus CJK artifacts and wrong terminology (`סקסואליות`→`מיניות`, `לא-בינארי`→`א־בינארי`, `LGBTQ+`→`להט״ב`). Training on this taught the model to emit meta-text in Hebrew. **Clean it (Phase 2).**

4. **No held-out evaluation existed.** Past accuracy numbers were measured on the same synthetic distribution as training. You will build a **frozen, never-trained-on** eval set from the Achva expert review (`inclusify_review_set_with_expert_notes.xlsx`, 100 rows, EN+HE) and the Achva expert-highlighted documents, and report before/after against it. This is the scoreboard.

### Hardware reality (you are on H100, the old config was for a T4)
The existing `ml/training/config.py` and `train_qwen_grid.py` are tuned for a 16GB T4: 4-bit NF4 QLoRA, `fp16=False`, `bf16=False` (T4 can't bf16), `batch_size=4`, `adamw_8bit`, and **hardcoded `/home/azureuser/...` paths**. On an 80GB H100 none of these constraints apply. You will override them (Phase 3). Do **not** blindly run the old script.

### Rules of engagement (non-negotiable)
- **Never train, fine-tune, validate-select, or tune on the eval sets** (`gold_eval.jsonl`, `expert_eval.jsonl`). Deduplicate training data against them by exact and normalized sentence match. A leak invalidates the whole run.
- **Do not deploy or promote anything to production.** This VM has no production access and should keep it that way. You produce a *candidate* adapter + a report and stop at the final HUMAN GATE.
- **Commit your work to a branch** (`retrain/achva-v2`), never to `main`. Commit after each phase so progress survives a crash.
- **Write a running log** to `ml/retrain_run/RUN_LOG.md` — every command's outcome, every metric, every deviation. The human reads this to trust the result.
- **Keep the old adapter** `ml/adapters/qwen_r8_d0.2/` untouched — it is the rollback and the baseline.
- If a phase's go/no-go criterion fails, **stop and write why** in the log rather than pushing forward.
- Set a fixed seed (42) everywhere and record library versions for reproducibility.

---

## Phase 0 — Environment bring-up & preflight

Create the work area and log first:
```bash
cd "$(git rev-parse --show-toplevel)"          # repo root; all paths below are relative to it
export REPO="$(pwd)"
git checkout -b retrain/achva-v2
mkdir -p ml/retrain_run ml/adapters_new ml/eval_sets ml/data_curated ml/logs
# Start RUN_LOG.md with date, GPU, commit SHA (use `date`, `nvidia-smi`, `git rev-parse HEAD`)
```

**0.1 Verify hardware/software.** Record outputs in the log; abort if any fail:
- `nvidia-smi` → confirm at least one H100 (~80GB). Note GPU count.
- `nvcc --version` or the CUDA in `nvidia-smi` → CUDA 12.x expected.
- `df -h .` → need ≥ ~80GB free (base model ~6GB, checkpoints, datasets).
- `python3 --version` → 3.11 or 3.12.

**0.2 Python environment.** Create an isolated venv and install. The training stack imports `trl` and `tensorboard`, which are **missing from `ml/requirements.txt`** — install them explicitly.
```bash
python3 -m venv .venv-train && source .venv-train/bin/activate
pip install --upgrade pip
# Install a PyTorch build matching the box's CUDA (check nvidia-smi). Example for CUDA 12.1:
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install -r ml/requirements.txt
# Missing-but-required for training + the format-aligned trainer:
pip install "trl>=0.9,<0.20" tensorboard sentencepiece openpyxl python-docx pymupdf
pip freeze > ml/retrain_run/pip_freeze.txt   # reproducibility record
```
> Note on TRL: the old `train_qwen_grid.py` was written against an old `SFTTrainer` API. You are writing a new trainer in Phase 3 (the format changes anyway), so pin whatever modern TRL installs cleanly and adapt the API to it. Do not fight the old script.

**0.3 Base model.** The old config points at a local `/home/azureuser/models/...` that does not exist here. Download from Hugging Face:
```bash
huggingface-cli login        # needs HF_TOKEN in env or interactive; record if it fails
huggingface-cli download Qwen/Qwen2.5-3B-Instruct --local-dir ml/base_model/Qwen2.5-3B-Instruct
```
If no HF token is available, STOP and log it — you cannot proceed without the base model.

**0.4 Confirm data inventory.** Verify these exist and log row counts (`wc -l`):
- `data/english_10k.csv`, `data/hebrew_10k.csv` (raw per-language, cols: `sentence,severity_label,explanation`)
- `data/combined_multilingual_20k.csv` (cols add `language`)
- `data/Inclusify_Dataset.csv`, `data/augmented_dataset.csv` (original seed)
- `data/Achva New Data/inclusify_review_set_with_expert_notes.xlsx` (eval source — expert notes)
- `data/Achva New Data/מאמרים מתוקפים/` (eval source — expert-highlighted gold docs + `Legend.txt`)

**0.5 Path/config strategy.** Do **not** edit hardcoded paths scattered in `config.py`. Instead create `ml/training/config_h100.py` that imports and overrides `CONFIG` (model_path → `ml/base_model/...`, csv_path → your curated file from Phase 2, output_dir → `ml/adapters_new`, log_dir → `ml/logs`), and the H100 hyperparameters from Phase 3. Reference it from your new training entrypoint.

**✅ Phase 0 done when:** venv built, GPU confirmed, base model downloaded, all data present, `RUN_LOG.md` + `pip_freeze.txt` written. Commit.

---

## Phase 1 — Build the FROZEN evaluation set (do this BEFORE touching training data)

The eval set is built first and treated as untouchable for the rest of the run. Two sources.

**1.1 Expert review set → `ml/eval_sets/expert_eval.jsonl`.**
Parse `data/Achva New Data/inclusify_review_set_with_expert_notes.xlsx`, sheet `Review Set`, columns: `Language, Sentence, Label, Explanation, Expert Notes`. 100 rows (50 EN, 50 HE; 20 per label).
- The expert notes are the source of truth, not the `Label` column. Write a script `ml/eval_sets/build_expert_eval.py` that, per row, derives the **adjudicated label**:
  - If the note plainly agrees ("Correct." / "נכון.") → keep the original `Label`.
  - If the note says the sentence merely *describes/criticizes* a view ("not outdated if used critically", "מתאר…ולא מצדיק", "the model confuses…") → adjudicated label = **Correct** (these are the use-mention cases).
  - If the note states a different label → use the note's label.
  - If the note is context-dependent ("offensive only if used to justify…") → mark `context_dependent: true` and keep original label but **exclude from the strict accuracy metric** (report separately).
- Emit JSONL records: `{"lang","sentence","original_label","adjudicated_label","note","context_dependent"}`.
- Log the distribution of adjudicated vs original labels — the delta quantifies the use-mention problem and is a headline number for the human.

**1.2 Achva gold-highlighted documents → `ml/eval_sets/gold_eval.jsonl`.**
The expert highlighted real documents in the four severity colors (`Legend.txt`: ורוד=biased, ירוק=correct, אדום=factually incorrect, כחול=outdated, צהוב=potentially offensive).
- `ml/eval_sets/extract_gold.py`:
  - **DOCX** (`כתבה בוחרים במשפחה.docx`): unzip, parse `word/document.xml`, read runs with `w:highlight` (`python-docx` exposes `run.font.highlight_color`); map highlight color → label; capture highlighted span + its sentence.
  - **PDF** (`2018-03783-002 (1).pdf`): use PyMuPDF (`fitz`); iterate `page.annots()` for `Highlight` annots; for each, get quad points, extract underlying text via `page.get_textbox(rect)`, map the annotation's stroke RGB → nearest legend color → label.
  - Emit `{"source_doc","lang","span_text","sentence","label"}` per highlight.
- These documents are PDFs/DOCX; **run them through the real ingestion path** is NOT needed for eval — you are scoring the model on the expert's spans/sentences directly. (Document parsing quality is a separate concern from model quality.)
- Expected order of magnitude: ~100+ gold spans. Log the count and per-label distribution.

**1.3 Freeze.** Concatenate nothing — keep the two eval files separate. Compute and store a checksum of each. From here on, any training-data row whose normalized sentence matches an eval sentence is **dropped from training**.

**1.4 Baseline measurement (current production adapter).**
Before improving anything, measure where you stand so improvement is provable.
- Write `ml/eval_sets/run_eval.py` that, given an adapter dir + base model + an eval JSONL, runs the model and scores it. **Critical:** evaluate in the **production format** — feed the production `SYSTEM_PROMPT` (import the canonical text; do not hand-copy) and the production user-message template, parse the `{"issues":[...]}` output, and derive a sentence-level verdict:
  - sentence severity = highest-severity issue whose `phrase` is in the sentence; if no issues → `Correct`.
  - This matches how the app actually behaves, so the number is honest.
- Metrics to compute and save to `ml/retrain_run/baseline_metrics.json`:
  - Per-label precision/recall/F1 and overall accuracy, **split by language (EN vs HE)**.
  - **Use-mention false-positive rate**: of gold/expert `Correct` (esp. critical-description) sentences, fraction the model flags as a violation. This is the key regression guard.
  - Confusion matrix.
- Run it against **both** `expert_eval.jsonl` and `gold_eval.jsonl` using `ml/adapters/qwen_r8_d0.2/`.

**✅ Phase 1 done when:** both eval JSONLs exist with checksums, `baseline_metrics.json` written and summarized in the log (EN F1, HE F1, use-mention FP rate at minimum). Commit. **These files are now read-only for the rest of the run.**

---

## Phase 2 — Data curation & relabeling (the actual fix)

Goal: produce `data/curated/train.csv` + `data/curated/val.csv` in the **production format** (see 2.4), cleaned and relabeled, leakage-free.

**2.1 Clean Hebrew data.** `ml/data_curated/clean_hebrew.py` over `data/hebrew_10k.csv`:
- Drop rows whose `explanation` matches translation-meta patterns (`^התרגום`, `^הגרסה`, `שומר על הטון`, `התאמה להקשר ישראלי`, `דקדוק עברי תקין`, etc.) **or** contain CJK / Latin-glued-to-Hebrew artifacts. (~46% of rows; ~5.3k clean rows remain, still balanced ~1k/label — confirmed during investigation.)
- Apply terminology normalization per the expert notes: `סקסואליות→מיניות`, `לא-בינארי→א־בינארי`, standalone `LGBTQ+→להט״ב` in Hebrew sentences, media `הכללה→ייצוג` where contextually it means representation. Keep a mapping table in the script; log how many rows each rule touched.
- Output `data/curated/hebrew_clean.csv`. Log before/after counts and per-label balance.

**2.2 Apply use-mention relabeling — LLM-as-judge, calibrated against the expert set (NOT plain regex).**
Use-mention is a *semantic* distinction; pure regex both over- and under-flips and would inject fresh noise on the exact axis this retrain fixes. Note the irony to avoid: the *original* labels were produced by an LLM (Gemini, see `ml/data_synthesis/`) without this rule — that is how the bias got in — so a *generic* re-label would reproduce it. The fix is a judge **prompted with the expert's explicit rule + expert-note few-shots, and validated before use.** `ml/data_curated/relabel_use_mention.py`:

- **The rule (from the expert notes):** a sentence that *describes, attributes, historicizes, or criticizes* a discredited/pathologizing view — without asserting it in the author's own voice — is `Correct`, not a violation.
- **Code does the mechanics:** only rows currently labeled as a violation (`Outdated|Biased|Potentially Offensive|Factually Incorrect`) are candidates (a `Correct` row can't gain a use-mention flip). Select those; the judge only sees that subset.
- **A strong LLM makes the call.** Run a judge model that is **clearly stronger than the 3B being trained** (otherwise it's blind-leading-blind). On the H100 download and serve a large instruct model **locally** (e.g. `Qwen2.5-32B-Instruct` or `-72B-Instruct` — fits in 80GB at 4-bit/8-bit; no external API needed, which suits the isolated VM). Prompt it with: the rule above, 4–6 few-shot examples **lifted verbatim from the expert notes** (both the "describes ≠ endorses → Correct" cases and genuine-violation counter-examples so it doesn't over-flip to Correct), and the candidate sentence. Constrain output to JSON `{"verdict": "keep" | "flip_to_correct", "reason": "<one line>"}`. Temperature 0, fixed seed — deterministic and reproducible.
- **Calibrate before trusting it (the gate that makes this safe).** First run the judge on the 100 expert-adjudicated rows from Phase 1 (`expert_eval.jsonl`) and measure agreement with the expert's adjudicated labels. This uses the eval set only to *measure the relabeling tool* — it does not put eval data into training (those rows are dropped from training in 2.3 regardless), and do **not** iteratively tune the judge prompt against all 100 (hold ~30 out if you adjust the prompt). **Go/no-go:** proceed to relabel the full set only if judge↔expert agreement ≥ **85%** (and use-mention recall is clearly non-trivial). Log the agreement + confusion. If it fails the bar, fall back to a conservative regex prefilter + leave borderline rows unflipped, and note in the log that relabel quality is limited.
- **Apply + audit.** Apply the judge's verdicts; **log every decision** to `ml/data_curated/relabel_audit.csv` (sentence, old label, new label, judge reason) so the human can spot-check. Expect a meaningful share to flip toward `Correct`, raising the `Correct`/hard-negative share — exactly the signal the model lacks.
- These flipped rows are the most valuable training signal in the whole run; do not skip or shortcut this step.

**2.3 Deduplicate against eval + within-set.**
- Normalize sentences (lowercase, collapse whitespace, strip punctuation) and **drop any training row matching an eval sentence** (`expert_eval` or `gold_eval`). Log how many were removed — expect a handful; if zero across 100 eval rows that's suspicious, verify the matcher.
- Drop exact-duplicate sentences within training (keep first).

**2.4 Reformat to the production task (the key alignment).**
The model must be trained to emit what production asks for. Convert each curated row into a chat example whose **assistant target is the production JSON shape**:
- System prompt: import the **exact** production `SYSTEM_PROMPT` from `backend/app/modules/analysis/llm_client.py` (read it programmatically; do not paste a stale copy). It already contains the severity/category definitions, the LANGUAGE rule (Hebrew in → Hebrew explanation/suggestion), and the EN+HE few-shot examples added recently.
- User message: the production template — `Analyze this passage for LGBTQ+ inclusive language compliance:\n"<sentence>"`.
- Assistant target:
  - If the row's label is `Correct` → `{"issues": []}`. **These empty-issue targets are essential** — they teach restraint and directly fix the use-mention over-flagging. Ensure a healthy share of training rows are `Correct` after Phase 2.2.
  - Otherwise → `{"issues": [{"phrase": <the problematic span or the sentence if no span is annotated>, "category": <map>, "severity": <label>, "explanation": <cleaned explanation>, "suggestion": <if available else omit>}]}`.
  - The seed data is sentence-level (no phrase spans), so for violations use the sentence as the `phrase` and let the explanation carry the reasoning. This is acceptable; the few-shot examples in the system prompt model phrase extraction, and the Achva LoRA round's goal is severity correctness + Hebrew fluency + restraint, not span precision (span precision is a later round once Achva phrase-level gold is larger).
- Severity values stay the **English enum** (`Outdated|Biased|Potentially Offensive|Factually Incorrect`) regardless of language — this matches `map_severity` and the confidence-logprob extraction in production. Explanation/suggestion follow the sentence language.
- Write `ml/data_curated/build_training_jsonl.py` producing chat-formatted examples. Use the tokenizer's `apply_chat_template`.

**2.5 Split & balance.** Stratified split by `(label × language)`, 90/10 train/val (val here is for training's early-stopping only — it is NOT the eval set). Output `data/curated/train.jsonl` and `data/curated/val.jsonl`. Log final counts: total, per-label, per-language, and `Correct` share.

**✅ Phase 2 done when:** curated train/val JSONL exist in production format, `relabel_audit.csv` written, leakage check logged (eval rows removed), label/language balance logged. Commit. Write a short `ml/data_curated/MANIFEST.md` describing exactly how the data was produced (the human must be able to trace any training row to its origin and transformation).

---

## Phase 3 — Train on the H100

**3.1 H100 hyperparameters.** In `config_h100.py`, override the T4-era settings:
- `model_path` → `ml/base_model/Qwen2.5-3B-Instruct`
- Precision: **`bf16=True`, `fp16=False`** (H100 supports bf16 natively; the T4 reason for disabling it is gone).
- Quantization: **drop 4-bit NF4.** A 3B model in bf16 LoRA fits easily in 80GB. Train the LoRA on the bf16 base (faster, higher quality than QLoRA). Keep `prepare_model_for_kbit_training` only if you keep quantization — you are not.
- `optim`: `adamw_torch` (the `adamw_8bit` memory hack is unnecessary).
- `per_device_train_batch_size`: start at **16**, with `gradient_accumulation_steps` to reach an effective batch of ~32–64; raise if VRAM allows (watch `nvidia-smi`). `per_device_eval_batch_size`: 32.
- `max_seq_length`: **1024** (production chunks + the long system prompt exceed 512; the old 512 would truncate the system prompt). Verify the longest formatted example fits; raise to 2048 if needed.
- `gradient_checkpointing`: can be **off** on H100 for speed (you have the memory); turn on only if you hit limits.
- `num_epochs`: 3 (start). `learning_rate`: 2e-4. `warmup_ratio`: 0.03. `lr_scheduler_type`: cosine.
- LoRA: keep `r=8, alpha=16, dropout=0.2, target_modules=[q,k,v,o,gate,up,down]` as the **primary** config (it was the prior winner). On H100 a full run is ~minutes-to-low-hours, so **also** train `r=16, alpha=32, dropout=0.1` as a second candidate — cheap insurance, and the larger rank may help Hebrew. Do not expand the grid further without reason.

> **⚠️ T4 production-compatibility constraint.** Production serves the base in fp16 on a 16GB **T4** (`vllm.service`: `--dtype half`, `--max-lora-rank 16`). The adapter you produce here must run there unchanged. This is fine **as long as you respect these limits** — training on H100/bf16 instead of T4/4-bit does **not** affect adapter portability (a LoRA is just low-rank matrices applied on top of any base; bf16-trained adapters load and cast cleanly onto an fp16 base — this is the normal QLoRA serving path). Hard rules:
> - **Rank ≤ 16.** Do not train r=32+ candidates — `--max-lora-rank 16` would reject them and bumping it costs T4 VRAM/CUDA-graph headroom. r=8 and r=16 are both safe.
> - **Same base model + same target modules** as the current adapter (they are, above) so shapes match `Qwen2.5-3B-Instruct`.
> - **Do not merge the adapter into the base** and do not save a fp32-only artifact — keep it as a standalone PEFT adapter (`adapter_config.json` + `adapter_model.safetensors`), the format `switch_adapter.py` and vLLM expect.

**3.2 Loss / training objective (read carefully — there is a real trap here).**
- The objective is standard **causal-LM token cross-entropy** (generative SFT). Keep it. Do **not** convert the task to a classification head with weighted CE — production generates JSON text (severity + explanation + suggestion, language-dependent), and a classification head would destroy that. There is no custom/exotic loss in this round.
- **Completion-only loss is mandatory.** The old script computed loss over the entire sequence (prompt + completion). That was tolerable with the old short training prompt, but you are now putting the **full ~1.9k-token production system prompt** into every example (Phase 2.4). It is byte-identical across all rows, so training on the full sequence wastes the gradient teaching the model to reproduce a fixed prompt and drowns the real signal (the assistant's `{"issues":...}` verdict). **Mask all tokens before the assistant turn; compute loss only on the assistant completion.**
  - Preferred: modern TRL `SFTConfig(assistant_only_loss=True)` — but this only works if the chat template emits `{% generation %}` markers. Qwen2.5's stock template may not. **Verify**, don't assume.
  - Fallback: `DataCollatorForCompletionOnlyLM(response_template="<|im_start|>assistant\n", tokenizer=...)`, which masks everything up to and including the assistant header.
  - **Verify the mask actually applied** (silent-failure-prone): on one batch, confirm `labels == -100` for the prompt span and real token ids only on the completion — e.g. assert the unmasked token count is a small fraction (roughly <25%) of the sequence. Log this check. If the mask did not apply, fix it before the full run — an unmasked run is invalid.
- **Do not address class imbalance in the loss.** The `Correct`/violation (and per-language) balance is handled by data sampling in Phase 2.5, which is the clean lever for generative SFT. No class weights, no focal loss.
- **Known characteristic, not a bug:** even with completion-only loss, the longer `explanation` text contributes more tokens to the loss than the few-token `severity` value, so the gradient is not laser-focused on the severity decision. Completion-only masking plus the eval-driven candidate selection (Phase 4, which scores severity directly) mitigate this. Up-weighting the severity field is possible future work but **out of scope** — do not implement it this round.
- **Checkpoint vs candidate selection:** `metric_for_best_model="eval_loss"` is fine for picking the best checkpoint *within* a run (it's CE on the held-out training-distribution val split). It is **not** the basis for choosing the winning adapter — that is the Phase 4 frozen-eval criteria. Keep the two distinct.
- (Future work, explicitly out of scope: the use-mention over-flagging could be attacked directly with a preference objective — DPO/ORPO on pairs of (critical-description → no-flag) vs (over-flagged). It needs preference data we don't have yet; the relabeling + empty-issues targets address it within SFT for now. Note it for the next round; do not attempt it here.)

**3.3 Trainer.** Write `ml/training/train_h100.py` (do not reuse the stale `train_qwen_grid.py` wholesale — its SFTTrainer call and quantization are outdated). It should:
- Load tokenizer + bf16 base model.
- Build `LoraConfig` and a modern `SFTTrainer` / `SFTConfig` consuming `data/curated/train.jsonl` (chat-formatted `messages` or pre-rendered `text`).
- `report_to="tensorboard"`, `logging_steps=10`, `eval_strategy="steps"`, `eval_steps` ~ every ~0.25 epoch, `save_strategy="steps"` aligned, `load_best_model_at_end=True`, `metric_for_best_model="eval_loss"`, seed 42.
- Output each candidate to `ml/adapters_new/qwen_r{R}_d{D}_achva/`.
- Save `training_args` + a `train_meta.json` (data manifest hash, base model, lib versions, final train/val loss, wall-clock).

**3.4 Run & monitor.** Launch training (use `run_in_background` and tail the log / TensorBoard). For each candidate, log: steps/sec, peak VRAM, final eval_loss, total time, **and the completion-only mask verification from 3.2**. If loss diverges or NaNs, stop that candidate, log it, continue with the other.

**✅ Phase 3 done when:** ≥1 candidate adapter trained and saved with `train_meta.json`, losses logged, no leakage (re-affirm the train data came from Phase 2 curated files). Commit (adapters are large — check repo `.gitignore`; if adapters aren't committed, copy candidates to a known path and note it in the log instead of force-committing weights).

---

## Phase 4 — Evaluate candidates against the frozen eval & compare to baseline

For **each** candidate adapter, run the **same** `ml/eval_sets/run_eval.py` (production-format scoring) used for the baseline, against **both** eval files.

Produce `ml/retrain_run/eval_report.md` containing, per candidate and for baseline:
- Overall accuracy + macro-F1, **split EN / HE**.
- Per-label precision/recall/F1.
- **Use-mention false-positive rate** (flagging `Correct`/critical-description as a violation) — the metric that most justifies this whole effort.
- Language-quality spot check on HE: sample ~15 HE violation outputs, check explanations are coherent Hebrew with no CJK/translation-meta (programmatic CJK check + log the samples for human reading).
- A clear table: **baseline vs each candidate**, deltas highlighted.

**Go / no-go criteria for a candidate to be recommended:**
1. **Use-mention FP rate strictly decreases** vs baseline (the core fix). Hard requirement.
2. **Hebrew macro-F1 increases** vs baseline. Hard requirement.
3. **English macro-F1 does not regress** by more than 2 absolute points. Guard against trading EN for HE.
4. No CJK / translation-meta in the HE explanation sample.

Pick the best candidate that passes all four (prefer the smaller `r=8` if both pass comparably). If **none** passes, that is a valid and important outcome — do **not** ship a regression. Log the failure analysis (which criterion failed, hypotheses: data still noisy / format change hurt / needs more `Correct` examples) so the next iteration is informed.

**✅ Phase 4 done when:** `eval_report.md` written with the baseline-vs-candidates table and an explicit pass/fail verdict per criterion. Commit.

---

## Phase 5 — Package the candidate & STOP

Do **not** deploy, do **not** edit `ml/adapters/active.json`, do **not** touch `vllm.service`, do **not** push to `main`.

**5.0 T4 load smoke-test (mandatory before packaging).** Confirm the candidate is production-loadable, not just H100-loadable:
- Load `Qwen2.5-3B-Instruct` in **fp16** (`torch_dtype=torch.float16`, no quantization) and apply the candidate adapter via `PeftModel.from_pretrained`; run one EN and one HE sentence and confirm coherent output. This reproduces the T4 serving dtype and catches any dtype/shape surprise. (You can't reproduce 16GB VRAM on an H100, but the fp16+adapter load is the part that can fail.)
- Read the candidate's `adapter_config.json` and assert `r <= 16` and `base_model_name_or_path` resolves to Qwen2.5-3B with the same `target_modules` as `ml/adapters/qwen_r8_d0.2/adapter_config.json`.
- Log the adapter file size (sanity: tens of MB, not GB). If any check fails, do not package — log and stop.

For the recommended candidate (if any passed):
1. Copy it to `ml/adapters/qwen_r{R}_d{D}_achva_v2/` following the existing layout (`adapter_config.json`, `adapter_model.safetensors`, tokenizer files).
2. Write its `version.json` per `ml/adapters/VERSIONING.md`: bump the **minor** version (new training data), record date, the eval numbers (EN/HE F1, use-mention FP rate, baseline deltas), data manifest hash, base model, and a one-line summary.
3. Write `ml/adapters/qwen_r{R}_d{D}_achva_v2/README.md` documenting training data provenance and known limitations (esp. context-dependent cases that sentence-level training can't fully solve, and that span-level precision is deferred to a future round).
4. Push the `retrain/achva-v2` branch (branch only — never `main`).

### 🛑 HUMAN GATE (final, mandatory)
Produce a concise handoff at the top of `ml/retrain_run/RUN_LOG.md` and as your final message:
- One-paragraph outcome: did a candidate pass all four criteria? Which one?
- The baseline-vs-winner table (EN F1, HE F1, use-mention FP rate, per-label highlights).
- Exact deployment steps for the human to run **manually if they approve** (the existing path: `python ml/scripts/switch_adapter.py --list`, then `--adapter <name> --dry-run`, then deploy to the inference VM and `--restart-service`, then `curl /v1/models` to verify) — but **you do not run these.**
- Honest caveats: anything in the eval that looked weak, any heuristic in relabeling that may have over/under-flipped, sample sizes (the eval set is only ~200 sentences — small; treat F1 deltas as directional, not precise).
- Cost/time actuals (GPU-hours used).

Then **stop and wait for the human.** Promotion to production is their decision, not yours.

---

## Quick reference — what's where

| Thing | Path |
|---|---|
| Base model (download) | `ml/base_model/Qwen2.5-3B-Instruct` |
| Old config (T4, do not run as-is) | `ml/training/config.py`, `ml/training/train_qwen_grid.py` |
| Your H100 config / trainer | `ml/training/config_h100.py`, `ml/training/train_h100.py` (you create) |
| Production system prompt (import, don't copy) | `backend/app/modules/analysis/llm_client.py::SYSTEM_PROMPT` |
| Production severity map | `backend/app/modules/analysis/llm_client.py::SEVERITY_MAP` |
| Raw data | `data/english_10k.csv`, `data/hebrew_10k.csv`, `data/combined_multilingual_20k.csv` |
| Eval sources (Achva) | `data/Achva New Data/inclusify_review_set_with_expert_notes.xlsx`, `data/Achva New Data/מאמרים מתוקפים/` |
| Frozen eval (you build) | `ml/eval_sets/expert_eval.jsonl`, `ml/eval_sets/gold_eval.jsonl` |
| Curated training data (you build) | `data/curated/train.jsonl`, `data/curated/val.jsonl`, `ml/data_curated/MANIFEST.md` |
| Current prod adapter (baseline + rollback, do not modify) | `ml/adapters/qwen_r8_d0.2/` |
| Candidate adapters (you build) | `ml/adapters_new/`, then `ml/adapters/..._achva_v2/` |
| Reports & log | `ml/retrain_run/RUN_LOG.md`, `baseline_metrics.json`, `eval_report.md` |
| Adapter versioning rules | `ml/adapters/VERSIONING.md` |
| Deploy mechanism (human runs, not you) | `ml/scripts/switch_adapter.py` |

## Definition of done
A `retrain/achva-v2` branch containing: frozen eval sets + baseline metrics; curated, relabeled, leakage-free training data with a manifest; ≥1 trained candidate adapter; an `eval_report.md` with an explicit pass/fail verdict against the four criteria; and a packaged candidate (if any passed) with `version.json`, awaiting human approval at the final gate. The run log tells the whole story end to end.
