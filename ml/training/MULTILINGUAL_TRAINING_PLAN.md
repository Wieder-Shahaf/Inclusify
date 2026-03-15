# Multilingual QLoRA Training Plan
## Qwen2.5-3B on English + Hebrew Dataset

**Created:** March 15, 2026
**Phase:** 05.5 - Multilingual Adapter Training
**Status:** Ready to execute

---

## Dataset Summary

### Combined Multilingual Dataset (19,954 samples)

| Language | Training | Validation | Total  | Percentage |
|----------|----------|------------|--------|------------|
| English  | 8,002    | 2,001      | 10,003 | 50.13%     |
| Hebrew   | 7,960    | 1,991      | 9,951  | 49.87%     |
| **Total**| **15,962**| **3,992** | **19,954** | **100%** |

### Class Distribution (Stratified)

All 5 severity labels are balanced at ~20% each:

| Severity Label         | Count | Percentage |
|------------------------|-------|------------|
| Biased                 | 3,232 | 20.25%     |
| Outdated               | 3,236 | 20.27%     |
| Potentially Offensive  | 3,230 | 20.24%     |
| Factually Incorrect    | 3,186 | 19.96%     |
| Correct                | 3,078 | 19.28%     |

**Stratification:** Train/validation split maintains class proportions within ±2% tolerance

---

## Training Configuration

### Using Proven Best Parameters from Phase 05.4

Based on grid search results (9 configs tested), **rank=8 + dropout=0.2** achieved:
- **F1 Score:** 90.0% (highest)
- **Validation Loss:** 0.4937 (lowest)
- **Precision:** 100% (zero false positives)
- **Recall:** 81.9%
- **Training Time:** 54.5 minutes on T4 GPU

### Fixed Hyperparameters

```python
# Model
model_name = "Qwen/Qwen2.5-3B-Instruct-GPTQ-Int4"
model_path = "/home/azureuser/models/Qwen2.5-3B-Instruct-GPTQ-Int4"

# LoRA Configuration
rank = 8
alpha = 16  # 2 × rank
dropout = 0.2
target_modules = [
    "q_proj", "k_proj", "v_proj", "o_proj",
    "up_proj", "down_proj", "gate_proj"
]

# Training
num_epochs = 3
batch_size = 2  # T4 16GB VRAM constraint
learning_rate = 2e-4
warmup_steps = 100
max_seq_length = 512

# Optimizer & Precision
optim = "paged_adamw_8bit"  # Critical for T4 memory
fp16 = True  # T4 doesn't support bf16

# Data Split
test_size = 0.2  # 80% train, 20% validation
random_state = 42
```

### Why These Parameters?

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **rank=8** | 8 | Smallest adapter (14.97M params), best val_loss (0.4937) |
| **dropout=0.2** | 0.2 | Highest dropout tested, prevents overfitting |
| **epochs=3** | 3 | Sweet spot: more epochs = diminishing returns |
| **batch_size=2** | 2 | Safe for T4 VRAM, proven reliable |
| **Unified adapter** | 1 model | Simpler than 2 language-specific adapters |

---

## Expected Performance

### Conservative Estimate (Realistic)
- **F1 Score:** 72-74%
  - Down from 90% English-only due to Hebrew linguistic complexity
- **Precision:** 95-100%
- **Recall:** 65-75%
- **Inference Latency:** ~200-250ms

### Optimistic Estimate
- **F1 Score:** 80-82% (90% of English performance)
- **Precision:** 100%
- **Recall:** 75-80%
- **Inference Latency:** ~200ms

### Why Lower Than English Baseline?

1. **Hebrew dataset is brand new** (translated March 2026)
2. **Limited LGBTQ+ Hebrew academic corpus** in base model
3. **Language-specific nuances** not yet explored
4. **First multilingual training** (no prior baseline)

### Success Criteria

✅ **Minimum acceptable:** F1 > 70% on both languages
🎯 **Target:** F1 > 75% on both languages
🚀 **Stretch goal:** F1 > 80% on both languages

---

## File Locations

### Datasets
```
data/combined_multilingual_20k.csv        # Full dataset (19,954 samples)
data/combined_multilingual_train_16k.csv  # Training only (15,962 samples)
data/combined_multilingual_val_4k.csv     # Validation only (3,992 samples)
```

### Training Scripts
```
ml/training/config.py                     # Updated with rank=8, dropout=0.2
ml/training/train_qwen_grid.py            # Main training script (1 config)
ml/training/prepare_data.py               # Data pipeline (unchanged)
ml/training/evaluate.py                   # Evaluation metrics
ml/training/combine_multilingual_datasets.py  # Dataset creation script
```

### VM Paths (after copying)
```
/home/azureuser/inclusify/data/combined_multilingual_20k.csv  # Dataset
/home/azureuser/inclusify/ml/adapters/qwen_r8_d0.2/           # Output adapter
/home/azureuser/inclusify/ml/logs/                            # TensorBoard logs
```

---

## Training Execution Steps

### 1. Copy Dataset to VM (5 min)

```bash
# From local machine
scp data/combined_multilingual_20k.csv \
    azureuser@52.224.246.238:~/inclusify/data/
```

Verify:
```bash
ssh azureuser@52.224.246.238 \
    "wc -l ~/inclusify/data/combined_multilingual_20k.csv"
# Expected: 19955 (including header)
```

### 2. Verify Training Config (2 min)

```bash
ssh azureuser@52.224.246.238
cd ~/inclusify
cat ml/training/config.py | grep -A 3 "csv_path"
# Should show: csv_path = "/home/azureuser/inclusify/data/combined_multilingual_20k.csv"

cat ml/training/config.py | grep -E "^RANKS|^DROPOUTS"
# Should show: RANKS = [8]
#              DROPOUTS = [0.2]
```

### 3. Test Data Pipeline (5 min)

```bash
# Activate venv
source ~/vllm-venv/bin/activate

# Test data loading
python3 -c "
from ml.training.prepare_data import prepare_datasets
from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained(
    '/home/azureuser/models/Qwen2.5-3B-Instruct-GPTQ-Int4'
)
train, val = prepare_datasets(
    '/home/azureuser/inclusify/data/combined_multilingual_20k.csv',
    tokenizer,
    test_size=0.2
)
print(f'✓ Train: {len(train)}, Val: {len(val)}')
"
# Expected: Train: ~15900, Val: ~4000
```

### 4. Run Training (~55 minutes)

```bash
# Check GPU availability
nvidia-smi
# Expected: GPU 0: NVIDIA T4 (16GB)

# Run training (single config: rank=8, dropout=0.2)
cd ~/inclusify
python3 ml/training/train_qwen_grid.py

# Monitor GPU in separate terminal
watch -n 1 nvidia-smi
# Target: <14GB VRAM utilization
```

**Estimated time:** 55 minutes (based on Phase 05.4 English-only baseline)

### 5. Monitor Progress

**TensorBoard (optional):**
```bash
# In separate terminal
source ~/vllm-venv/bin/activate
tensorboard --logdir ~/inclusify/ml/logs --port 6006

# From local machine
ssh -L 6006:localhost:6006 azureuser@52.224.246.238
# Open browser: http://localhost:6006
```

**Watch log file:**
```bash
tail -f ~/inclusify/ml/logs/train_*.log
```

### 6. Evaluate Results (5 min)

```bash
# After training completes
python3 ml/training/evaluate.py

# Check results
cat ml/adapters/grid_search_results.json
```

Expected output structure:
```json
{
  "qwen_r8_d0.2": {
    "config": {"rank": 8, "alpha": 16, "dropout": 0.2},
    "metrics": {
      "val_loss": 0.XXX,
      "f1_score": 0.XX,
      "precision": 0.XX,
      "recall": 0.XX
    },
    "training_time_min": XX.X
  }
}
```

### 7. Test Inference (10 min)

**Load adapter into vLLM:**
```bash
# Update systemd service
sudo vim /etc/systemd/system/vllm.service

# Add to ExecStart line:
--lora-modules inclusify=/home/azureuser/inclusify/ml/adapters/qwen_r8_d0.2/

# Restart service
sudo systemctl daemon-reload
sudo systemctl restart vllm

# Check status
sudo systemctl status vllm
```

**Test English:**
```bash
curl http://localhost:8001/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen2.5-3B-GPTQ-Int4",
    "prompt": "Analyze: Homosexuality is a mental disorder.",
    "max_tokens": 100
  }'
```

**Test Hebrew:**
```bash
curl http://localhost:8001/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen2.5-3B-GPTQ-Int4",
    "prompt": "נתח: הומוסקסואליות היא הפרעה נפשית.",
    "max_tokens": 100
  }'
```

---

## Troubleshooting

### Issue: OOM (Out of Memory)
**Symptoms:** CUDA out of memory error during training
**Solutions:**
- Reduce `batch_size` from 2 to 1 in `config.py`
- Reduce `max_seq_length` from 512 to 384
- Clear GPU cache: `nvidia-smi --gpu-reset`

### Issue: Validation loss not decreasing
**Symptoms:** val_loss plateaus or increases after epoch 1
**Solutions:**
- Check for data leakage (train/val overlap)
- Reduce learning rate to 1e-4
- Increase warmup_steps to 200

### Issue: Hebrew text rendering issues
**Symptoms:** Hebrew appears as ??? or boxes
**Solutions:**
- Ensure terminal supports UTF-8: `export LANG=en_US.UTF-8`
- Check tokenizer supports Hebrew: `tokenizer.encode("שלום")`

### Issue: Training too slow
**Symptoms:** >2 hours for 3 epochs
**Solutions:**
- Check GPU utilization: `nvidia-smi` (should be >90%)
- Verify batch_size=2 (not accidentally 1)
- Check for CPU bottleneck in data loading

---

## Post-Training Tasks

### 1. Copy Adapter Back to Local (5 min)

```bash
# From local machine
scp -r azureuser@52.224.246.238:~/inclusify/ml/adapters/qwen_r8_d0.2/ \
    ml/adapters/qwen_multilingual_r8_d0.2/
```

### 2. Update Documentation (15 min)

Create `ml/adapters/MULTILINGUAL_RESULTS.md`:
```markdown
# Multilingual Adapter Results
- F1 Score: XX.X%
- Training data: 15,962 samples (50/50 EN/HE)
- Validation: 3,992 samples
- Training time: XX minutes
- Date: March XX, 2026
```

### 3. Commit Results to Git (5 min)

```bash
git add ml/adapters/qwen_multilingual_r8_d0.2/
git add ml/training/MULTILINGUAL_TRAINING_PLAN.md
git add ml/adapters/MULTILINGUAL_RESULTS.md
git commit -m "feat(05.5): train multilingual Qwen2.5 adapter on 20K EN+HE dataset"
git push origin gsd
```

### 4. Update Roadmap (10 min)

Update `.planning/ROADMAP.md`:
- Mark Phase 05.5 as COMPLETE
- Add actual metrics vs. expected
- Note any deviations from plan

---

## Success Metrics Checklist

✅ **Dataset created:** 19,954 samples (50/50 EN/HE)
✅ **Config updated:** rank=8, dropout=0.2
✅ **Training completes:** <90 minutes
✅ **F1 > 70%:** Minimum acceptable performance
✅ **Precision > 95%:** Low false positive rate
✅ **Adapter size < 20MB:** Deployable
✅ **Inference < 300ms:** Production-ready latency
✅ **Both languages work:** EN + HE inference validated

---

## References

- **Phase 05.4 Results:** `ml/analysis/FINAL_MODEL_COMPARISON.md`
- **English Dataset:** `data/english_10k.csv`
- **Hebrew Dataset:** `data/hebrew_10k.csv`
- **Training Script:** `ml/training/train_qwen_grid.py`
- **Original suzume adapter:** `ml/LoRA_Adapters/adapter_config.json`

---

## Contact & Support

**Team:** Shahaf Wieder, Barak Sharon, Rasha Daher, Lama Zarka, Adan Daxa
**Organization:** Achva LGBT
**Deadline:** April 15, 2026 (second results presentation)

For issues, check:
1. This document's Troubleshooting section
2. Phase 05.4 CONTEXT.md for English-only baseline
3. VM systemd logs: `journalctl -u vllm -n 100`
