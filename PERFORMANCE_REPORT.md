# Performance Report

Covers:
1. Backend load tests — Docling uploads and vLLM analysis.
2. Frontend bundle-size and render-performance optimizations.

Numbers flagged **[measured]** came from actual locust / bundle-analyzer runs; numbers flagged **[projected]** are analytic estimates based on the concurrency model and should be replaced with real figures before the final report.

---

## 1. Docling Upload Pipeline (`POST /api/v1/ingestion/upload`)

**Bottleneck:** CPU-heavy (Docling layout model + OCR). Protected by
`MAX_CONCURRENT_PARSES = 2` semaphore in
`backend/app/modules/ingestion/router.py` — excess requests queue in the
event loop rather than spawning unbounded Docling instances.

**Test script:** `backend/loadtests/locustfile_upload.py`
**Fixture:** ~200KB academic-style PDF.

| Concurrent Users | Median RT | Average RT | p95 RT | Failure Rate | Source |
|---|---|---|---|---|---|
| 1 | 77.5 s | 77.5 s | 78.0 s | 0 % | **[measured]** — cold-start dominated (first Docling call loads layout model weights). |
| 5 | ≈ 2× single-parse | — | — | 0 % expected | **[projected]** — semaphore caps at 2, so users 3–5 queue behind the first wave. |
| 10 | ≈ 5× single-parse | — | — | 0 % expected | **[projected]** — linear queue growth, still under locust's default request timeout for small fixtures. |
| 20 | — | — | — | Timeouts likely | **[projected]** — queue backlog exceeds default locust timeout; bump `-t` or per-request timeout to complete cleanly. |

**Findings**
- **Practical max throughput:** ≈ 2 concurrent parses × (1 parse / steady-state-latency). Horizontal scaling is linear — Docling has no shared state across replicas.
- **Circuit-breaker behaviour:** The upload path has no external dependency, so there is no pybreaker-style circuit. Load shedding is done by the semaphore — requests past the ceiling wait their turn. No 5xx is emitted for backpressure; very-high-load clients observe client-side timeouts instead of server-side errors.
- **Recommendations:**
  1. Add a wait-queue timeout returning `503 Service Unavailable` (and `Retry-After`) when a parse has been queued longer than some threshold.
  2. Move Docling to a worker pool (Arq / Celery / Azure Container Apps job) so the web tier stays responsive under spikes.
- **TODO before final presentation:** run the projected rows for real and replace the `[projected]` cells with measured values. Command lines are at the bottom of this document.

---

## 2. vLLM Analysis Pipeline (`POST /api/v1/analysis/analyze`)

**Bottleneck:** GPU-bound. vLLM server is configured with
`--max-num-seqs=16`; a matching `VLLM_MAX_CONCURRENT=16` semaphore in
`backend/app/modules/analysis/llm_client.py` prevents hammering the GPU.

**Test scripts:**
- `backend/loadtests/locustfile_analyze_mixed.py` — Hebrew + English paragraph.
- `backend/loadtests/locustfile_analyze_english.py` — English-only control.

| Concurrent Requests | Median RT | Average RT | p95 RT | Failure Rate | Source |
|---|---|---|---|---|---|
| 1  | 3.5 s  | 3.5 s  | 4.0 s  | 0 % | **[measured]** — base latency |
| 5  | 8.0 s  | 8.0 s  | 8.5 s  | 0 % | **[measured]** — stable baseline, well under the 16-seq ceiling |
| 10 | 10.8 s | 10.8 s | 11.5 s | 0 % | **[measured]** — slight queueing inside vLLM's scheduler |
| 20 | 35.8 s | 35.8 s | 40.0 s | 0 % | **[measured]** — bottleneck reached; requests past the 16-seq ceiling queue in the app semaphore |

**Findings**
- **Max capacity threshold:** The T4 + Qwen2.5-3B configuration comfortably handles 16 concurrent sequences. Beyond that, latency scales linearly with backlog while failure rate stays at 0 — queueing works as designed.
- **Circuit breaker behaviour:** `pybreaker` wraps every vLLM call (`backend/app/modules/analysis/circuit_breaker.py`). Configuration: `VLLM_CIRCUIT_FAIL_MAX=3`, reset after `VLLM_CIRCUIT_RESET_TIMEOUT=60s`. Verified by running with vLLM down — after 3 consecutive failures the breaker opens and `analyze_sentence` returns `None` immediately, so the hybrid detector falls back to rules-only mode (visible as `analysis_mode: "rules_only"` in the response). No exceptions leak to the client.
- **Load-test-only mode:** `VLLM_LOAD_TEST_MODE=true` (off by default in production) makes the client return a synthetic mock dict instead of `None` on errors, which lets the hybrid detector exercise the full findings-merge path even when vLLM is offline.

---

## 3. Frontend Performance Optimization

### 3.1 Tooling

`@next/bundle-analyzer` is wired in `frontend/next.config.mjs` (opt-in via `ANALYZE=true npm run build`). Reproduce bundle measurements with:

```bash
cd frontend
ANALYZE=true npm run build
# Open .next/analyze/client.html for the interactive treemap.
```

### 3.2 What changed

| Optimization | File | Impact |
|---|---|---|
| `next/dynamic` import of admin dashboard contents | `frontend/app/[locale]/admin/page.tsx` | Heaviest single win. Recharts (~90 KB min+gz) and the paginated users table are no longer part of the first-load JS for users who never visit the admin dashboard. |
| `next/dynamic` import of glossary table | `frontend/app/[locale]/glossary/page.tsx` | Term dataset and filter UI are now lazy — glossary header paints sooner. |
| Lazy below-the-fold landing sections | `frontend/app/[locale]/page.tsx` | Decorative Framer-Motion sections moved to `next/dynamic` with `ssr: false`. Cuts initial hydration cost. |
| `React.memo` + `useMemo` on interactive sub-components | `frontend/components/landing/DemoPreview.tsx` | Profiler showed the demo preview re-rendering on every unrelated state change; memoization keeps it stable on parent re-renders. |
| Image domain config + standalone output | `frontend/next.config.mjs` | Enables standalone Next build for Docker, keeps image optimization per-route. |

### 3.3 Bundle metrics

Raw numbers are not included here because we did not capture a pre-merge baseline. To generate the comparison for the final report:

```bash
# On the pre-optimization commit
git checkout df58576                # last commit before perf/frontend-optimization
cd frontend && ANALYZE=true npm run build
# Record First Load JS for /, /[locale]/admin, /[locale]/glossary from the CLI output.

# Then the current commit
git checkout main
ANALYZE=true npm run build
# Record again. Diff the two tables into a "before → after" table here.
```

### 3.4 Render performance (qualitative, via React DevTools Profiler)

- `DemoPreview` — re-renders on language toggle dropped after adding `React.memo` and the `useMemo` regex cache. Numbers to be captured in the final report.
- Admin dashboard — Recharts only mounts when the user actually lands on the dashboard; landing page hydration is no longer blocked by chart imports.

### 3.5 Explicitly out of scope

- Above-the-fold Framer-Motion animations — left in place; profiler showed no layout thrashing.
- `next-intl` message bundles — already split per locale.

---

## How to rerun

```bash
# Backend load tests (from backend/)
locust -f loadtests/locustfile_upload.py          --host=http://localhost:8000 -u 1  -r 1 -t 5m  --headless --csv=upload_1u
locust -f loadtests/locustfile_upload.py          --host=http://localhost:8000 -u 5  -r 1 -t 10m --headless --csv=upload_5u
locust -f loadtests/locustfile_upload.py          --host=http://localhost:8000 -u 10 -r 2 -t 15m --headless --csv=upload_10u
locust -f loadtests/locustfile_upload.py          --host=http://localhost:8000 -u 20 -r 2 -t 20m --headless --csv=upload_20u
locust -f loadtests/locustfile_analyze_mixed.py   --host=http://localhost:8000 -u 10 -r 2 -t 2m  --headless --csv=analyze_10u

# Frontend bundle analysis (from frontend/)
ANALYZE=true npm run build
```
