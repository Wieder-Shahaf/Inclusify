# Quick Start: vLLM Dataset Synthesis

This guide gets you from zero to generating 10,000 English samples in ~10 minutes.

## Prerequisites

- NVIDIA GPU with ≥16GB VRAM (e.g., T4, V100, A100)
- Python 3.11+
- vLLM installed (`pip install vllm`)
- OpenAI Python client (`pip install openai`)

## Step-by-Step Guide

### 1. Start vLLM Server (5 minutes)

```bash
# Start vLLM server with Qwen 2.5-3B
vllm serve Qwen/Qwen2.5-3B-Instruct \
  --port 8000 \
  --gpu-memory-utilization 0.9 \
  --max-model-len 3072 \
  --trust-remote-code
```

**Wait for:** `Application startup complete` message

**Verify GPU usage:**
```bash
# In another terminal
nvidia-smi
# Should show model loaded (~6GB VRAM used)
```

### 2. Test Server (30 seconds)

```bash
python scripts/quick_qwen_test.py
```

**Expected output:**
```
============================================================
vLLM Server Quick Test
============================================================
✓ Response received in 1.23s
✓ JSON extraction successful
✓ Schema validation passed
✓ vLLM server is ready for synthesis pipeline
============================================================
```

**If test fails:** See troubleshooting section below

### 3. Run Synthesis (10 minutes for 10K samples)

```bash
cd ml/data_synthesis
python synthesize_english.py
```

**Expected output:**
```
INFO: Using vLLM backend: http://localhost:8000/v1
INFO: Model: Qwen/Qwen2.5-3B-Instruct
INFO: Batch size: 64, Max throughput: 30 req/sec
INFO: Processing 10000 requests...
INFO: Processing batch 1/157 (64 requests)...
...
INFO: Total: 10000 requests in 665.23s (15.03 req/sec)
INFO: Results: 9876 succeeded, 124 errors (98.8% success rate)
✓ Saved 9850 valid samples to data/english_10k.csv
```

**Output files:**
- `data/english_10k.csv` - Final dataset (10K+ samples)
- `data/intermediate/english_raw_11k.jsonl` - Raw results

### 4. Validate Quality (5 minutes)

```bash
# View sample outputs
head -20 data/english_10k.csv

# Check class distribution
python -c "
import pandas as pd
df = pd.read_csv('data/english_10k.csv')
print(df['severity_label'].value_counts())
print(f'\nTotal samples: {len(df)}')
"
```

**Expected distribution (±2%):**
```
Correct                    ~2000
Outdated                   ~2000
Biased                     ~2000
Potentially Offensive      ~2000
Factually Incorrect        ~2000
Total samples: 10000+
```

## Troubleshooting

### Test Fails: Connection Refused

**Symptom:**
```
✗ Test failed: Connection refused to http://localhost:8000/v1
```

**Solutions:**
1. Check vLLM server is running:
   ```bash
   curl http://localhost:8000/health
   ```
2. Check port: `netstat -an | grep 8000`
3. Restart vLLM server

### Test Fails: CUDA Out of Memory

**Symptom:**
```
CUDA out of memory. Tried to allocate X MiB
```

**Solutions:**
1. Free GPU memory:
   ```bash
   pkill -f vllm
   nvidia-smi  # Should show GPU free
   ```
2. Reduce max model length:
   ```bash
   vllm serve Qwen/Qwen2.5-3B-Instruct \
     --port 8000 \
     --gpu-memory-utilization 0.8 \
     --max-model-len 2048 \
     --trust-remote-code
   ```

### Synthesis: Low Parse Success Rate

**Symptom:**
```
Results: 8500 succeeded, 1500 errors (85% success rate)
```

**Expected:** ≥95% success rate

**Solutions:**
1. Check error logs for patterns
2. Increase temperature for more deterministic output:
   ```bash
   export QWEN_TEMPERATURE=0.7
   python synthesize_english.py
   ```
3. Verify prompt file exists:
   ```bash
   ls -l ml/data_synthesis/prompts/english_variations_qwen.txt
   ```

### Synthesis: Slow Throughput

**Symptom:** Actual throughput <<20 req/sec

**Solutions:**
1. Check GPU utilization: `nvidia-smi dmon`
2. Increase max throughput:
   ```bash
   export VLLM_MAX_THROUGHPUT=40
   python synthesize_english.py
   ```
3. Check for network latency (if remote server)

## Configuration Options

### Change Batch Size
```bash
export VLLM_BATCH_SIZE=128  # Larger GPU
# or
export VLLM_BATCH_SIZE=32   # Smaller GPU
python synthesize_english.py
```

### Change Sample Count
Edit `ml/data_synthesis/config.py`:
```python
TOTAL_TARGET = 1100  # For 1K samples (10% buffer)
```

### Change Temperature
```bash
export QWEN_TEMPERATURE=1.0  # More diverse
# or
export QWEN_TEMPERATURE=0.7  # More conservative
python synthesize_english.py
```

### Use Different Model
```bash
export VLLM_MODEL="Qwen/Qwen2.5-7B-Instruct"
# Restart vLLM server with new model
vllm serve Qwen/Qwen2.5-7B-Instruct --port 8000 ...
python synthesize_english.py
```

## Fallback to Claude

If vLLM has issues, revert to Claude:

```bash
export VLLM_ENABLED=false
export ANTHROPIC_API_KEY="sk-ant-..."
python synthesize_english.py
```

This will use the original Claude Batch API (slower but proven).

## Next Steps

After successful generation:

1. **Manual Quality Review**
   ```bash
   # Sample 50 outputs for manual review
   python -c "
   import pandas as pd
   df = pd.read_csv('data/english_10k.csv')
   for label in df['severity_label'].unique():
       print(f'\n=== {label} ===')
       samples = df[df['severity_label'] == label].sample(2)
       for _, row in samples.iterrows():
           print(f'{row[\"sentence\"]}')
           print(f'Explanation: {row[\"explanation\"]}\n')
   "
   ```

2. **Use for Training**
   - Merge with existing dataset
   - Run deduplication
   - Train model on combined data

3. **Iterate if Needed**
   - Adjust prompts for quality issues
   - Change temperature for diversity
   - Regenerate specific severity classes

## Summary

**Total time:** ~20 minutes (5 min setup + 10 min generation + 5 min validation)

**Expected results:**
- ✅ 10,000+ samples generated
- ✅ ≥95% parse success rate
- ✅ Balanced class distribution
- ✅ $0 cost
- ✅ Ready for model training

**Support:**
- Detailed docs: `ml/data_synthesis/README_VLLM.md`
- Implementation summary: `IMPLEMENTATION_SUMMARY.md`
- Test scripts: `scripts/quick_qwen_test.py`, `scripts/test_vllm_implementation.py`
