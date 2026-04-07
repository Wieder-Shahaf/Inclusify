---
quick_id: 260407-kps
description: Fix vLLM response parsing crash in llm_client.py
date: 2026-04-07
must_haves:
  truths:
    - _make_request never raises KeyError or IndexError on malformed vLLM responses
    - malformed response returns None (triggers existing fallback)
    - all four malformed shapes are covered by unit tests
  artifacts:
    - backend/app/modules/analysis/llm_client.py (patched)
    - backend/tests/test_vllm_client.py (new TestVLLMMalformedResponse class)
---

# Quick Task 260407-kps: Fix vLLM response parsing crash

## Root Cause
`_make_request` at lines 237-238 accesses `data["choices"][0]["message"]["content"]`
with no bounds checking. A malformed vLLM response raises KeyError/IndexError.
The `except Exception` in `analyze_sentence` catches it, but only AFTER the circuit
breaker has already recorded a failure — so repeated malformed responses will open
the circuit breaker unnecessarily.

The correct fix is to validate the shape inside `_make_request` before touching
the dict, returning `None` on malformed input. This keeps the circuit breaker healthy.

## Tasks

### Task 1 — Patch `_make_request` with safe response validation
files: backend/app/modules/analysis/llm_client.py
action: Replace bare dict/index access with `.get()` + early-return None on malformed shapes
verify: File diff shows no bare `data["choices"]` or `choice["message"]` key access
done: safe access added, warning logged for each malformed shape

### Task 2 — Add unit tests for malformed vLLM responses
files: backend/tests/test_vllm_client.py
action: Add `TestVLLMMalformedResponse` class covering 5 malformed shapes
verify: pytest passes for all new tests
done: 5 parametrized or individual test cases pass
