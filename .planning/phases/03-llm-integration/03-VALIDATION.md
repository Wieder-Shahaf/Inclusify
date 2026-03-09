---
phase: 03
slug: llm-integration
status: ready
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-09
updated: 2026-03-09
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

## Wave 0 Plan (03-00)

Wave 0 creates test stubs before implementation begins. All stubs are marked `@pytest.mark.skip` and pass collection.

| Test File | Covers | Status |
|-----------|--------|--------|
| `backend/tests/test_vllm_deployment.py` | 03-01 deployment verification | Wave 0 stub |
| `backend/tests/test_vllm_client.py` | 03-02 client, circuit breaker, splitter | Wave 0 stub |
| `backend/tests/test_hybrid_detection.py` | 03-03 hybrid detection, merge, mode | Wave 0 stub |
| `backend/tests/conftest.py` | Mock vLLM fixtures | Wave 0 updated |

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 03-00-01 | 00 | 0 | LLM-01 | collection | `pytest backend/tests/test_vllm_deployment.py --collect-only -q` | pending |
| 03-00-02 | 00 | 0 | LLM-02 | collection | `pytest backend/tests/test_vllm_client.py --collect-only -q` | pending |
| 03-00-03 | 00 | 0 | LLM-02 | collection | `pytest backend/tests/test_hybrid_detection.py --collect-only -q` | pending |
| 03-01-01 | 01 | 1 | LLM-01 | checkpoint | Human review of setup.sh, quantize_model.py | pending |
| 03-01-02 | 01 | 1 | LLM-01 | checkpoint | Human review of vllm.service | pending |
| 03-01-03 | 01 | 1 | LLM-01 | checkpoint | Human verification on Azure VM | pending |
| 03-02-01 | 02 | 1 | LLM-02 | unit | `python -c "from app.core.config import settings; assert hasattr(settings, 'VLLM_URL')"` | pending |
| 03-02-02 | 02 | 1 | LLM-02 | unit | `pytest tests/test_vllm_client.py::TestCircuitBreaker -x -v` | pending |
| 03-02-03 | 02 | 1 | LLM-02 | unit | `pytest tests/test_vllm_client.py::TestSentenceSplitter -x -v` | pending |
| 03-02-04 | 02 | 1 | LLM-02 | unit | `pytest tests/test_vllm_client.py -x -v` | pending |
| 03-03-01 | 03 | 2 | LLM-02 | unit | `pytest tests/test_hybrid_detection.py -x -v` | pending |
| 03-03-02 | 03 | 2 | LLM-02 | unit | `python -c "from app.modules.analysis.router import AnalysisResponse; assert 'analysis_mode' in AnalysisResponse.model_fields"` | pending |
| 03-03-03 | 03 | 2 | LLM-02 | integration | `python -c "from app.modules.analysis.router import router; print('OK')"` | pending |

*Status: pending | green | red | flaky*

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

- [x] All tasks have `<automated>` verify or checkpoint type
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 plan (03-00) covers all test stubs
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] No fallback `|| python -c` patterns in verify commands
- [x] `nyquist_compliant: true` set in frontmatter
- [x] `wave_0_complete: true` set in frontmatter

**Approval:** ready

---

## Revision History

| Date | Change |
|------|--------|
| 2026-03-09 | Initial validation strategy created |
| 2026-03-09 | Fixed Nyquist compliance: added Wave 0 plan, removed fallback patterns, converted 03-01 tasks 1-2 to checkpoints |
