# Quick Task 260407-kps: Fix vLLM response parsing crash — Summary

**Completed:** 2026-04-07
**Commit:** aa049b7

## What was done

### Task 1 — Patched `_make_request` in `llm_client.py`
Replaced bare `data["choices"][0]["message"]["content"]` access (lines 237-238)
with safe `.get()` + `isinstance` checks. Four malformed shapes now return `None`
with a warning log instead of raising KeyError/IndexError:
- missing or empty `choices` field
- choice is not a dict
- missing or invalid `message` in choice
- missing `content` in message

### Task 2 — Added `TestVLLMMalformedResponse` tests
Added 5 parametrized cases to `TestVLLMClient` in `test_vllm_client.py`.
All 24 tests pass (19 pre-existing + 5 new).

## Why it matters
Malformed responses previously crashed inside `_make_request` (decorated with
circuit breaker), which counted as a failure and could open the circuit breaker
unnecessarily. Now malformed responses return `None` cleanly before the circuit
breaker records anything — fallback triggers, circuit stays healthy.
