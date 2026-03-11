# Qwen3.5-0.8B vs Qwen2.5-3B Training Comparison

## Quick Start

After Qwen2.5-3B grid search completes, run Qwen3.5-0.8B:

```bash
ssh azureuser@52.224.246.238
cd ~/inclusify
source ~/vllm-venv/bin/activate

# Option 1: FP16 (recommended - faster training)
screen -S qwen3_grid -dm bash -c "python ml/training/train_qwen3_grid.py 2>&1 | tee ml/logs/qwen3_grid.log"

# Option 2: 4-bit quantization (saves memory, slightly slower)
screen -S qwen3_grid -dm bash -c "python ml/training/train_qwen3_grid.py --quantize 2>&1 | tee ml/logs/qwen3_grid.log"

# Monitor
screen -r qwen3_grid
# or
tail -f ~/inclusify/ml/logs/qwen3_grid.log
```

## Key Differences

### Qwen3.5-0.8B Advantages
- **4x faster inference** (0.8B vs 3B params)
- **Larger batch size** (8 vs 2) → faster, more stable training
- **Thinking mode** for explicit reasoning about bias
- **256K context** vs 32K (can analyze full papers)
- **201 languages** explicitly optimized (better Hebrew)
- **Hybrid architecture** (DeltaNet + Gated Attention)
- **~1GB** model size vs ~3-4GB

### Qwen2.5-3B Advantages
- **More parameters** = potentially more nuanced understanding
- **Already validated** on previous phases
- **Known performance** from suzume-llama baseline

## What to Compare After Both Complete

### 1. Validation Loss
Lower is better. Check `grid_search_results.json` for both:

```bash
# Qwen2.5-3B
cat ~/inclusify/ml/adapters/grid_search_results.json | grep val_loss

# Qwen3.5-0.8B
cat ~/inclusify/ml/adapters/qwen3/grid_search_results.json | grep val_loss
```

### 2. Accuracy
Target: **>80%** validation accuracy

```bash
# Compare best configs
cat ~/inclusify/ml/adapters/grid_search_results.json | grep -A3 "qwen_r8_d0.2"
cat ~/inclusify/ml/adapters/qwen3/grid_search_results.json | grep -A3 "qwen3_r16"
```

### 3. Training Time
Qwen3.5 should be **2-3x faster** per config

### 4. Qualitative Test (Most Important!)

Test both on real examples:

```python
# Test script: ml/training/compare_models.py
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

# Load both models with adapters
# Run on 10 validation examples
# Compare explanation quality

# Example:
sentence = "הטיפול בהומוסקסואליות נעשה במרפאה"  # Hebrew
# Does the model correctly identify this as biased?
# Does it provide nuanced explanation?
```

## Decision Criteria

**Use Qwen3.5-0.8B if:**
- Validation loss < Qwen2.5-3B loss
- Accuracy > 80%
- Explanations are coherent and specific
- Speed matters for user experience (analyzing papers)

**Use Qwen2.5-3B if:**
- Qwen3.5 explanations are too generic
- Missing nuance in Hebrew bias detection
- Val accuracy significantly lower

**Hybrid Approach:**
- Qwen3.5 for fast pre-screening
- Qwen2.5-3B for nuanced cases
- Best of both worlds

## Expected Timeline

### Qwen2.5-3B Grid Search
- Started: ~20:38 UTC (March 11)
- Duration: ~3.5 hours
- Complete: ~00:00 UTC (March 12)

### Qwen3.5-0.8B Grid Search
- Start: After 3B completes
- Duration: ~45 min per config × 9 = **6-7 hours**
- Complete: ~07:00 UTC (March 12)
- **With --quantize:** ~8-9 hours (slower but uses less memory)

## Next Steps After Both Complete

1. **Compare results** (loss, accuracy, speed)
2. **Qualitative evaluation** on validation set
3. **Pick winner** or design hybrid
4. **Continue Phase 05.4-04:** Integrate with vLLM service
5. **Update backend** to use best adapter
