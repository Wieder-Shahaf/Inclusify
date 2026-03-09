# Phase 3: LLM Integration - Context

**Gathered:** 2026-03-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Text analysis uses the fine-tuned LLM for contextual inclusive language detection. This phase delivers:
- vLLM deployed on Azure T4 VM with fine-tuned model
- LLM inference integrated into the analysis endpoint
- Hybrid detection merging rule-based and LLM results
- Graceful fallback when vLLM is unavailable

</domain>

<decisions>
## Implementation Decisions

### vLLM Deployment
- Quantization: 4-bit GPTQ quantization. Convert model offline using auto-gptq before deployment. Gives ~4GB VRAM usage with headroom on T4.
- Deployment mode: Systemd service on Azure VM. Auto-restart on crash, starts on boot, managed via systemctl.
- Network exposure: Internal only. vLLM listens on localhost:8001. Backend connects via private IP/VNet. No public endpoint.
- LoRA loading: Dynamic loading via vLLM's --lora-modules flag. Enables hot-swapping adapters without restart.

### Hybrid Detection Strategy
- Execution order: LLM first, rules as backup. Always attempt LLM analysis, use rule-based only when LLM fails/times out.
- Chunking approach: Sentence-by-sentence. Split text into sentences, classify each individually. Provides precise character spans.
- Duplicate handling: Prefer LLM result when both detect same span. LLM provides richer context and explanation.

### Timeout & Fallback
- Per-sentence timeout: 30 seconds. Allows for cold start and GPU warm-up. Typical inference 1-3s.
- Fallback behavior: Silent fallback to rules. Return rule-based results with note in response. User still gets analysis.
- Circuit breaker: Yes. Track vLLM failures. After 3 consecutive fails, skip LLM for 60s. Auto-recover on success.
- Mode indicator: Include 'analysis_mode' field in response: 'llm' | 'hybrid' | 'rules_only'. Frontend can display if desired.

### API Contract & Response
- Confidence scores: Internal only. Use 0.0-1.0 confidence for deduplication/ranking, but don't expose in API response.
- Severity mapping: Direct mapping. Outdated→outdated, Biased→biased, Potentially Offensive→offensive, Factually Incorrect→incorrect, Correct→skip.
- Explanations: Use LLM explanation directly. Model was trained to produce academic, user-friendly explanations.
- Suggestions: LLM generates suggestions. Contextual replacements that are natural and language-aware.

### Claude's Discretion
- vLLM startup parameters beyond dtype and max-model-len
- Sentence splitting algorithm (spaCy, nltk, regex)
- Circuit breaker timing parameters
- GPTQ quantization calibration dataset
- System prompt refinements for production

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/modules/analysis/router.py`: Analysis endpoint with existing Issue/AnalysisResponse models. Add LLM client here.
- `ml/inference_demo.py`: Reference implementation with system prompt, JSON parsing, severity mapping. Port to async HTTP client.
- `ml/LoRA_Adapters/`: Fine-tuned adapter weights ready for deployment.
- `TERM_RULES` in router.py: 127 terms for rule-based fallback (17 English, 6 Hebrew entries).

### Established Patterns
- Subprocess isolation: Docling uses subprocess with timeout (Phase 2). Consider for local LLM testing.
- Fail-fast: 5s timeouts for DB, startup checks (Phase 1). Apply similar circuit breaker pattern.
- asyncpg pool: min=2, max=10 pattern. Apply similar connection pooling to vLLM HTTP client.
- httpx async: Use for vLLM API calls (already in deps).

### Integration Points
- `backend/app/modules/analysis/router.py`: Main integration point. Add LLM client, hybrid logic, fallback.
- `backend/app/main.py`: Add circuit breaker state, vLLM health check on startup.
- Response model: Add `analysis_mode` field to AnalysisResponse.

</code_context>

<specifics>
## Specific Ideas

- "LLM first, rules as backup" — maximize use of fine-tuned model's contextual understanding
- "Sentence-by-sentence" — aligns with model's training format (single sentence classification)
- "Silent fallback" — user experience stays consistent even when vLLM unavailable
- Circuit breaker prevents cascade failures during extended outages
- 4-bit GPTQ gives significant VRAM headroom on T4 (16GB → ~4GB model)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-llm-integration*
*Context gathered: 2026-03-09*
