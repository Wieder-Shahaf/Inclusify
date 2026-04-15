# Load Testing Results

## 1. Docling Upload Pipeline (`POST /api/v1/ingestion/upload`)
**Infrastructure Bottleneck:** CPU-heavy (Computer Vision & Text Extraction)

| Concurrent Users | Median Response Time | Average Response Time | 95%ile Response Time | Failure Rate (%) | Notes / Circuit Breaker Behavior |
|-----------------|----------------------|-----------------------|----------------------|------------------|--------------------------------|
| 1               | ~ 77.5 seconds       | ~ 77.5 seconds        | 78.0 seconds         | 0%               | Initial cold start observed. |
| 5               |                      |                       |                      |                  | |
| 10              |                      |                       |                      |                  | |
| 20              |                      |                       |                      |                  | |

**Findings Summary:**
* **Max Capacity Threshold:** [Write the highest number of users before failures skyrocket]
* **Circuit Breaker Behavior:** [Describe what error code is returned when the system is overwhelmed, e.g., HTTP 503 or 429]

---

## 2. vLLM Analysis Pipeline (`POST /api/v1/analysis/analyze`)
**Infrastructure Bottleneck:** GPU-bound (Max 16 sequences)

| Concurrent Requests | Median Response Time | Average Response Time | 95%ile Response Time | Failure Rate (%) | Notes / Circuit Breaker Behavior |
|--------------------|----------------------|-----------------------|----------------------|------------------|--------------------------------|
| 1                  | ~ 3.5s               | ~ 3.5s                | ~ 4.0s               | 0%               | Base latency                   |
| 5                  | ~ 8.0s               | 8.0s                  | ~ 8.5s               | 0%               | Stable baseline                |
| 10                 | ~ 10.8s              | 10.8s                 | ~ 11.5s              | 0%               | Slight increase                |
| 20                 | ~ 35.8s              | 35.8s                 | ~ 40.0s              | 0%               | Bottleneck reached             |

**Findings Summary:**
* **Max Capacity Threshold:** Bottleneck clearly reached at 20 concurrent users. The system successfully withstands the load without a single failure thanks to queueing, but latency spikes significantly.
* **Technical Note on Circuit Breaker Behavior:** The massive jump to 35.8s at 20 users effectively demonstrates the application's circuit breaker and semaphore behavior. Because the vLLM GPU inference server is strictly limited to processing 16 concurrent sequences, the requests hitting above that ceiling (users 17–20) are safely queued up by the FastAPI application. They simply wait their turn and are processed once the initial wave completes, preventing catastrophic out-of-memory container crashes at the cost of high latency.
