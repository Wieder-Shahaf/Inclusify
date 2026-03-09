---
phase: 03
slug: llm-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-09
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | backend/pytest.ini |
| **Quick run command** | `cd backend && pytest -x --tb=short` |
| **Full suite command** | `cd backend && pytest --tb=short` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && pytest -x --tb=short`
- **After every plan wave:** Run `cd backend && pytest --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | LLM-01 | integration | `pytest backend/tests/test_vllm_deployment.py -k health_check` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | LLM-01 | integration | `pytest backend/tests/test_vllm_deployment.py -k lora_loaded` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 1 | LLM-02 | unit | `pytest backend/tests/test_vllm_client.py -k async_client` | ❌ W0 | ⬜ pending |
| 03-02-02 | 02 | 1 | LLM-02 | unit | `pytest backend/tests/test_vllm_client.py -k circuit_breaker` | ❌ W0 | ⬜ pending |
| 03-02-03 | 02 | 1 | LLM-02 | unit | `pytest backend/tests/test_vllm_client.py -k timeout_fallback` | ❌ W0 | ⬜ pending |
| 03-03-01 | 03 | 2 | LLM-02 | unit | `pytest backend/tests/test_hybrid_detection.py -k merge_results` | ❌ W0 | ⬜ pending |
| 03-03-02 | 03 | 2 | LLM-02 | unit | `pytest backend/tests/test_hybrid_detection.py -k deduplication` | ❌ W0 | ⬜ pending |
| 03-03-03 | 03 | 2 | LLM-02 | integration | `pytest backend/tests/test_analysis_router.py -k analysis_mode` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_vllm_deployment.py` — stubs for LLM-01 (vLLM health, LoRA loading)
- [ ] `backend/tests/test_vllm_client.py` — stubs for async client, circuit breaker, timeout
- [ ] `backend/tests/test_hybrid_detection.py` — stubs for merge logic, deduplication
- [ ] `backend/tests/test_analysis_router.py` — extend existing with analysis_mode test
- [ ] `backend/tests/conftest.py` — mock vLLM server fixtures, test text samples

*Wave 0 creates test stubs that will fail until implementation completes.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| vLLM runs on Azure T4 VM | LLM-01 | Requires Azure infrastructure | SSH to VM, verify vLLM process running, check `nvidia-smi` GPU usage |
| Analysis completes under 10s | LLM-02 | Performance depends on real model | Run `time curl -X POST localhost:8000/api/v1/analysis/analyze` with test document |
| Hebrew text detection accuracy | LLM-02 | Quality assessment | Manually verify Hebrew test cases return expected severity and explanations |

*Infrastructure and performance verifications require manual validation.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
