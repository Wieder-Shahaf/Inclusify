# Phase 3: LLM Integration - Research

**Researched:** 2026-03-09
**Domain:** vLLM deployment, LLM inference integration, hybrid detection architecture
**Confidence:** HIGH

## Summary

Phase 3 integrates the fine-tuned suzume-llama-3-8B-multilingual model with LoRA adapters into the analysis endpoint. The architecture follows a microservices pattern where vLLM runs as a separate service on an Azure T4 GPU VM, exposing an OpenAI-compatible API that the FastAPI backend calls via httpx.

The key technical challenges are: (1) fitting an 8B parameter model with LoRA on a 16GB T4 GPU, (2) implementing robust fallback when vLLM is unavailable, and (3) merging LLM results with rule-based detection while avoiding duplicates. The user decisions lock us into 4-bit GPTQ quantization, sentence-by-sentence chunking, and LLM-first execution with silent fallback.

**Primary recommendation:** Deploy vLLM with GPTQ 4-bit quantization (not AWQ due to T4 kernel compatibility), use pybreaker for circuit breaker pattern, and implement sentence splitting with pysbd (not spaCy) for better Hebrew support.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Quantization:** 4-bit GPTQ quantization. Convert model offline using auto-gptq before deployment. Gives ~4GB VRAM usage with headroom on T4.
- **Deployment mode:** Systemd service on Azure VM. Auto-restart on crash, starts on boot, managed via systemctl.
- **Network exposure:** Internal only. vLLM listens on localhost:8001. Backend connects via private IP/VNet. No public endpoint.
- **LoRA loading:** Dynamic loading via vLLM's --lora-modules flag. Enables hot-swapping adapters without restart.
- **Execution order:** LLM first, rules as backup. Always attempt LLM analysis, use rule-based only when LLM fails/times out.
- **Chunking approach:** Sentence-by-sentence. Split text into sentences, classify each individually. Provides precise character spans.
- **Duplicate handling:** Prefer LLM result when both detect same span. LLM provides richer context and explanation.
- **Per-sentence timeout:** 30 seconds. Allows for cold start and GPU warm-up. Typical inference 1-3s.
- **Fallback behavior:** Silent fallback to rules. Return rule-based results with note in response. User still gets analysis.
- **Circuit breaker:** Yes. Track vLLM failures. After 3 consecutive fails, skip LLM for 60s. Auto-recover on success.
- **Mode indicator:** Include 'analysis_mode' field in response: 'llm' | 'hybrid' | 'rules_only'. Frontend can display if desired.
- **Confidence scores:** Internal only. Use 0.0-1.0 confidence for deduplication/ranking, but don't expose in API response.
- **Severity mapping:** Direct mapping. Outdated->outdated, Biased->biased, Potentially Offensive->offensive, Factually Incorrect->incorrect, Correct->skip.
- **Explanations:** Use LLM explanation directly. Model was trained to produce academic, user-friendly explanations.
- **Suggestions:** LLM generates suggestions. Contextual replacements that are natural and language-aware.

### Claude's Discretion
- vLLM startup parameters beyond dtype and max-model-len
- Sentence splitting algorithm (spaCy, nltk, regex)
- Circuit breaker timing parameters
- GPTQ quantization calibration dataset
- System prompt refinements for production

### Deferred Ideas (OUT OF SCOPE)
None - discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| LLM-01 | vLLM deployed on Azure VM with T4 GPU | GPTQ 4-bit quantization fits in 16GB T4 VRAM (~4GB model + overhead). Systemd service pattern documented. T4 supports GPTQ kernel (not Marlin). |
| LLM-02 | LLM inference integrated into analysis endpoint | OpenAI-compatible /v1/chat/completions API. httpx async client with 30s timeout. Circuit breaker with pybreaker. Sentence-by-sentence processing. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| vLLM | 0.9.x | LLM inference server | Industry standard for production LLM serving, OpenAI-compatible API |
| gptqmodel | 1.x | GPTQ model quantization | Official vLLM-recommended replacement for auto-gptq |
| httpx | 0.26.0 | Async HTTP client | Already in backend deps, native async support |
| pybreaker | 1.2.x | Circuit breaker | Async-compatible, well-maintained, simple API |
| pysbd | 0.3.4 | Sentence boundary detection | Better multilingual support than spaCy for Hebrew |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tenacity | 8.x | Retry logic | Optional for retry-before-circuit-break pattern |
| aiohttp | 3.9.x | Alternative HTTP client | Only if httpx has issues |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pysbd | spaCy sentencizer | spaCy has known Hebrew sentence splitting issues (GitHub #5911) |
| pybreaker | purgatory | purgatory is newer but less battle-tested |
| GPTQ | AWQ | AWQ has faster kernels on Ampere+ but GPTQ works reliably on T4 (compute capability 7.5) |

**Installation (backend):**
```bash
pip install pybreaker pysbd
```

**Installation (ML VM):**
```bash
pip install vllm gptqmodel
```

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── modules/
│   └── analysis/
│       ├── router.py           # Analysis endpoint (modify)
│       ├── llm_client.py       # NEW: vLLM HTTP client
│       ├── circuit_breaker.py  # NEW: Circuit breaker wrapper
│       ├── sentence_splitter.py # NEW: pysbd wrapper
│       └── hybrid_detector.py  # NEW: Merge LLM + rules
├── core/
│   └── config.py               # Add VLLM_URL, VLLM_TIMEOUT settings
└── main.py                     # Add circuit breaker state to app.state

infra/
├── azure/
│   └── vllm-vm/
│       ├── setup.sh            # VM provisioning script
│       ├── vllm.service        # Systemd unit file
│       └── quantize_model.py   # GPTQ conversion script
```

### Pattern 1: vLLM Client with Circuit Breaker
**What:** Async HTTP client that calls vLLM with timeout and circuit breaker protection
**When to use:** All LLM inference calls from the analysis endpoint
**Example:**
```python
# Source: vLLM docs + pybreaker docs
import httpx
import pybreaker

# Circuit breaker: opens after 3 failures, resets after 60s
vllm_breaker = pybreaker.CircuitBreaker(
    fail_max=3,
    reset_timeout=60,
    state_storage=pybreaker.CircuitMemoryStorage()
)

class VLLMClient:
    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=timeout)

    @vllm_breaker
    async def analyze_sentence(self, sentence: str) -> dict | None:
        """Call vLLM for single sentence classification."""
        try:
            response = await self.client.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "model": "lightblue/suzume-llama-3-8B-multilingual",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f'Analyze: "{sentence}"'}
                    ],
                    "max_tokens": 256,
                    "temperature": 0.1,
                }
            )
            response.raise_for_status()
            return response.json()
        except (httpx.TimeoutException, httpx.HTTPStatusError):
            return None  # Trigger fallback
```

### Pattern 2: Sentence-by-Sentence Processing
**What:** Split text into sentences, classify each, track character offsets
**When to use:** Main analysis flow to get precise spans
**Example:**
```python
# Source: pysbd docs
import pysbd

def split_with_offsets(text: str, language: str = 'en') -> list[tuple[str, int, int]]:
    """Split text into sentences with character offsets."""
    segmenter = pysbd.Segmenter(language=language, clean=False)
    sentences = segmenter.segment(text)

    results = []
    offset = 0
    for sentence in sentences:
        start = text.find(sentence, offset)
        end = start + len(sentence)
        results.append((sentence, start, end))
        offset = end

    return results
```

### Pattern 3: Hybrid Detection with Deduplication
**What:** Run LLM analysis, merge with rule-based, dedupe by span overlap
**When to use:** Combining LLM and rule-based results
**Example:**
```python
def merge_results(
    llm_issues: list[Issue],
    rule_issues: list[Issue],
    overlap_threshold: float = 0.5
) -> list[Issue]:
    """Merge LLM and rule issues, preferring LLM for overlaps."""
    final = list(llm_issues)  # LLM takes priority

    for rule_issue in rule_issues:
        # Check if rule issue overlaps with any LLM issue
        overlaps = False
        for llm_issue in llm_issues:
            overlap = _calculate_overlap(rule_issue, llm_issue)
            if overlap > overlap_threshold:
                overlaps = True
                break

        if not overlaps:
            final.append(rule_issue)

    return sorted(final, key=lambda x: x.start)
```

### Pattern 4: Systemd Service for vLLM
**What:** Persistent vLLM server that auto-restarts on crash
**When to use:** Production deployment on Azure VM
**Example:**
```ini
# /etc/systemd/system/vllm.service
[Unit]
Description=vLLM Inference Server
After=network.target

[Service]
Type=simple
User=azureuser
WorkingDirectory=/home/azureuser/inclusify
Environment="CUDA_VISIBLE_DEVICES=0"
ExecStart=/home/azureuser/.local/bin/vllm serve \
    /home/azureuser/models/suzume-llama-3-8B-gptq \
    --dtype float16 \
    --max-model-len 2048 \
    --port 8001 \
    --host 127.0.0.1 \
    --enable-lora \
    --lora-modules inclusify=/home/azureuser/inclusify/ml/LoRA_Adapters \
    --gpu-memory-utilization 0.9
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Anti-Patterns to Avoid
- **Embedding model in FastAPI process:** Blocks workers, VRAM leaks, no batching. Use separate vLLM service.
- **No timeout on vLLM calls:** Cascading failures when vLLM hangs. Always use 30s timeout.
- **Synchronous HTTP calls:** Blocks async event loop. Use httpx.AsyncClient.
- **Full text to LLM at once:** Context overflow, imprecise spans. Use sentence-by-sentence.
- **Marlin kernel on T4:** T4 (compute capability 7.5) does not support Marlin. Use default GPTQ kernel.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Circuit breaker | Custom failure counter | pybreaker | State machine complexity, race conditions in async |
| Sentence splitting | Regex-based splitter | pysbd | Hebrew/Arabic abbreviations, edge cases |
| HTTP client | requests + threads | httpx.AsyncClient | Native async, timeout support, connection pooling |
| Model quantization | Custom quantization | gptqmodel | Calibration math, kernel compatibility |
| Retry logic | Custom retry decorator | tenacity or pybreaker | Exponential backoff, jitter, async support |

**Key insight:** LLM inference is deceptively complex. vLLM handles batching, KV-cache, memory management, and GPU scheduling. Never try to load models directly in the API process.

## Common Pitfalls

### Pitfall 1: vLLM OOM on T4 GPU
**What goes wrong:** 8B model + LoRA exceeds 16GB VRAM. vLLM crashes on startup or first request.
**Why it happens:** Default float16 uses ~16GB, no headroom for LoRA or KV-cache.
**How to avoid:** Use GPTQ 4-bit quantization (~4GB) with --max-model-len 2048 (not 4096).
**Warning signs:** "CUDA out of memory" errors, container restart loop, first request timeout.

### Pitfall 2: Circuit Breaker State Lost on Restart
**What goes wrong:** Each worker has its own circuit breaker state. Failures don't aggregate.
**Why it happens:** Default CircuitMemoryStorage is per-process.
**How to avoid:** Use Redis-backed storage for production, or accept per-worker isolation for MVP.
**Warning signs:** Inconsistent fallback behavior, some requests try LLM even after failures.

### Pitfall 3: Hebrew Sentence Splitting Errors
**What goes wrong:** Sentences split mid-word or at wrong punctuation (Hebrew question marks, abbreviations).
**Why it happens:** spaCy's rule-based sentencizer has known Hebrew issues (GitHub #5911).
**How to avoid:** Use pysbd which has explicit Hebrew support, or pass language='he' hint.
**Warning signs:** Incomplete sentences in analysis, wrong character offsets.

### Pitfall 4: LLM JSON Parse Failures
**What goes wrong:** LLM outputs malformed JSON, analysis fails silently.
**Why it happens:** LLM may include markdown, extra text, or incomplete JSON.
**How to avoid:** Use the JSON extraction pattern from inference_demo.py (regex for JSON boundaries).
**Warning signs:** Increasing fallback to rule-based, empty explanations in results.

### Pitfall 5: Timeout Too Short for Cold Start
**What goes wrong:** First request times out after vLLM restart because model is loading.
**Why it happens:** GPTQ model load + warm-up takes 30-60 seconds.
**How to avoid:** Set 30s timeout, add startup probe, or pre-warm with health check.
**Warning signs:** First request after deployment always fails, subsequent requests work.

### Pitfall 6: T4 Kernel Incompatibility
**What goes wrong:** vLLM fails with kernel errors on T4 GPU.
**Why it happens:** Marlin and FP8 kernels require compute capability > 8.0. T4 is 7.5 (Turing).
**How to avoid:** Use standard GPTQ kernel (default), not Marlin-GPTQ or AWQ-Marlin.
**Warning signs:** "Kernel not supported" errors, CUDA capability errors.

## Code Examples

### vLLM Chat Completions Request
```python
# Source: vLLM OpenAI-compatible API docs
import httpx

async def call_vllm(client: httpx.AsyncClient, sentence: str) -> dict:
    """Call vLLM with OpenAI-compatible chat completions API."""
    response = await client.post(
        "http://localhost:8001/v1/chat/completions",
        json={
            "model": "lightblue/suzume-llama-3-8B-multilingual",
            "messages": [
                {
                    "role": "system",
                    "content": """You are an expert academic editor for the Inclusify project.
Analyze sentences for LGBTQ+ inclusive language compliance.
OUTPUT: Valid JSON only with keys: category, severity, explanation.
Severity: Correct, Outdated, Biased, Potentially Offensive, Factually Incorrect"""
                },
                {
                    "role": "user",
                    "content": f'Analyze: "{sentence}"'
                }
            ],
            "max_tokens": 256,
            "temperature": 0.1,
        },
        timeout=30.0
    )
    return response.json()
```

### Parse LLM JSON Response
```python
# Source: ml/inference_demo.py (existing pattern)
import json
import re

def parse_llm_output(raw: str) -> dict | None:
    """Extract JSON from LLM response, handling markdown and extra text."""
    # Try markdown code block first
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', raw)
    if json_match:
        json_str = json_match.group(1).strip()
    else:
        json_str = raw.strip()

    # Find JSON object boundaries
    start = json_str.find('{')
    end = json_str.rfind('}')
    if start != -1 and end > start:
        json_str = json_str[start:end + 1]

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None
```

### GPTQ Model Conversion
```python
# Source: gptqmodel docs / HuggingFace GPTQ guide
from gptqmodel import GPTQModel, QuantizeConfig
from transformers import AutoTokenizer

# Load tokenizer and model
model_id = "lightblue/suzume-llama-3-8B-multilingual"
tokenizer = AutoTokenizer.from_pretrained(model_id)

# Calibration data (use subset of Inclusify training data)
calibration_data = [
    "The term homosexual is considered clinical and outdated.",
    "Gender identity is an individual's internal sense of being male or female.",
    # ... 100-500 samples recommended
]

# Quantization config
quant_config = QuantizeConfig(
    bits=4,
    group_size=128,
    desc_act=False,  # False for faster inference
)

# Quantize
model = GPTQModel.from_pretrained(model_id, quant_config)
model.quantize(calibration_data, tokenizer=tokenizer)

# Save
model.save_pretrained("/home/azureuser/models/suzume-llama-3-8B-gptq")
tokenizer.save_pretrained("/home/azureuser/models/suzume-llama-3-8B-gptq")
```

### Response Model Extension
```python
# Add to backend/app/modules/analysis/router.py
from typing import Literal

class AnalysisResponse(BaseModel):
    original_text: str
    analysis_status: str
    issues_found: list[Issue]
    corrected_text: Optional[str] = None
    note: Optional[str] = None
    # NEW: Analysis mode indicator
    analysis_mode: Literal['llm', 'hybrid', 'rules_only'] = 'rules_only'
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| auto-gptq | gptqmodel | 2025 | auto-gptq deprecated, gptqmodel is official replacement |
| passlib | pwdlib | 2024 | Python 3.13 compatibility (already addressed in Phase 2) |
| --lora-modules name=path | --lora-modules JSON format | vLLM 0.8+ | Can now specify base_model_name in JSON |
| Basic AWQ | Marlin-AWQ | 2025 | 50% faster on Ampere+, but T4 not supported |

**Deprecated/outdated:**
- `auto-gptq`: Replaced by `gptqmodel` for vLLM compatibility
- `vllm serve --model`: Now just `vllm serve MODEL_PATH` (positional argument)
- Marlin kernel on T4: T4 compute capability 7.5 not supported

## Open Questions

1. **LoRA adapter VRAM overhead**
   - What we know: LoRA adds ~100-500MB per adapter
   - What's unclear: Exact VRAM with GPTQ + LoRA on T4
   - Recommendation: Test VRAM usage after quantization, adjust --gpu-memory-utilization if needed

2. **Calibration dataset selection**
   - What we know: Need 100-500 representative samples
   - What's unclear: Best split of English vs Hebrew samples
   - Recommendation: Use 50/50 split from Inclusify_Dataset.csv, validate Hebrew quality

3. **vLLM version pinning**
   - What we know: 0.9.x is current stable
   - What's unclear: Which minor version has best T4 GPTQ support
   - Recommendation: Start with latest 0.9.x, test before deployment

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.23.x |
| Config file | None (pytest.ini not present) |
| Quick run command | `pytest backend/tests/test_llm.py -x -v` |
| Full suite command | `pytest backend/tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LLM-01 | vLLM server health check | integration | `pytest backend/tests/test_llm.py::test_vllm_health -x` | No - Wave 0 |
| LLM-01 | GPTQ model loads | smoke | Manual - requires GPU VM | N/A |
| LLM-02 | Analysis endpoint calls vLLM | unit (mocked) | `pytest backend/tests/test_llm.py::test_analyze_with_llm -x` | No - Wave 0 |
| LLM-02 | Circuit breaker opens on failures | unit | `pytest backend/tests/test_llm.py::test_circuit_breaker -x` | No - Wave 0 |
| LLM-02 | Fallback to rules when vLLM down | unit | `pytest backend/tests/test_llm.py::test_fallback_to_rules -x` | No - Wave 0 |
| LLM-02 | Hybrid merge deduplicates | unit | `pytest backend/tests/test_llm.py::test_hybrid_merge -x` | No - Wave 0 |
| LLM-02 | Hebrew sentence splitting | unit | `pytest backend/tests/test_llm.py::test_hebrew_sentences -x` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest backend/tests/test_llm.py -x -v`
- **Per wave merge:** `pytest backend/tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_llm.py` - covers LLM-01, LLM-02 (all test cases above)
- [ ] Mock vLLM responses in conftest.py fixtures
- [ ] Test data: Hebrew + English sentence samples

## Sources

### Primary (HIGH confidence)
- [vLLM Quantization Supported Hardware](https://docs.vllm.ai/en/v0.9.0/features/quantization/supported_hardware.html) - T4 GPTQ/AWQ compatibility confirmed
- [vLLM LoRA Adapters](https://docs.vllm.ai/en/stable/features/lora/) - --lora-modules flag, dynamic loading
- [vLLM OpenAI-Compatible Server](https://docs.vllm.ai/en/stable/serving/openai_compatible_server/) - /v1/chat/completions API
- [pybreaker GitHub](https://github.com/danielfm/pybreaker) - Circuit breaker implementation
- [pysbd GitHub](https://github.com/nipunsadvilkar/pysbd) - Sentence boundary detection

### Secondary (MEDIUM confidence)
- [vLLM CLI serve](https://docs.vllm.ai/en/stable/cli/serve/) - Command line arguments
- [GPTQModel vLLM docs](https://docs.vllm.ai/en/latest/features/quantization/gptqmodel/) - GPTQ quantization
- [spaCy Hebrew issues](https://github.com/explosion/spaCy/issues/5911) - Sentence splitting problems

### Tertiary (LOW confidence)
- vLLM systemd deployment patterns - from community blogs, not official docs
- GPTQ calibration dataset size recommendations - varies by source (100-500 samples)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - vLLM and GPTQ are official, well-documented
- Architecture patterns: HIGH - Based on existing codebase patterns and vLLM docs
- Pitfalls: HIGH - T4 limitations verified in official vLLM hardware matrix
- Hebrew sentence splitting: MEDIUM - pysbd recommended but less testing data

**Research date:** 2026-03-09
**Valid until:** 2026-04-09 (vLLM moves fast, re-verify before deployment)
