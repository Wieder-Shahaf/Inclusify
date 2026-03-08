# Pitfalls & Prevention

**Project:** Inclusify - LGBTQ+ Inclusive Language Analyzer
**Researched:** 2026-03-08
**Confidence:** HIGH

## Executive Summary

This document catalogs common pitfalls in deploying production LLM-powered NLP applications, with specific focus on the Inclusify stack (vLLM + Docling + FastAPI + Azure). Each pitfall includes detection methods, prevention strategies, and recovery procedures.

---

## Critical Pitfalls (Project Blockers)

### Pitfall 1: vLLM OOM on T4 GPU

**What happens:** suzume-llama-3-8B (8B params × 2 bytes FP16 = 16GB) + QLoRA adapters exceeds T4's 16GB VRAM. vLLM crashes on first request.

**Detection:**
- CUDA OOM error in vLLM logs
- Container restart loop
- 503 errors from inference endpoint

**Prevention:**
```bash
# Option 1: Use float16 instead of bfloat16
--dtype float

# Option 2: Reduce max context
--max-model-len 2048  # Instead of 4096

# Option 3: Quantization (if still OOM)
pip install auto-gptq
# Convert model to GPTQ 4-bit offline
```

**Recovery:**
1. Check `nvidia-smi` for VRAM usage
2. Reduce `--max-model-len` to 2048
3. If still failing, quantize model to 4-bit GPTQ

### Pitfall 2: Docling Memory Exhaustion on Large PDFs

**What happens:** 100+ page PDFs consume 8-16GB RAM during parsing. Worker process killed by OOM killer.

**Detection:**
- Worker process disappears mid-request
- Linux OOM killer messages in dmesg
- 502 errors during upload

**Prevention:**
```python
# Option 1: Process in chunks
from docling.datamodel.pipeline_options import PdfPipelineOptions

options = PdfPipelineOptions()
options.do_ocr = False  # Disable OCR if not needed
options.page_range = (1, 50)  # Process in batches

# Option 2: Use separate worker process
import multiprocessing

def parse_in_subprocess(file_path):
    with multiprocessing.Pool(1) as pool:
        result = pool.apply(converter.convert, (file_path,))
    return result
```

**Recovery:**
1. Set page limits (50 pages max per request)
2. Queue large documents for background processing
3. Add memory limits to container (prevent cascade to other services)

### Pitfall 3: passlib Breaks on Python 3.13

**What happens:** FastAPI Users <13.0 uses passlib, which has deprecated modules removed in Python 3.13. Auth completely broken.

**Detection:**
- `ModuleNotFoundError: No module named 'passlib'`
- Or cryptic deprecation warnings
- Login/register endpoints return 500

**Prevention:**
```bash
# Use FastAPI Users 13.x which migrated to pwdlib
pip install 'fastapi-users[sqlalchemy]==13.0.0' pwdlib[argon2]==1.0.0
```

**Recovery:**
1. Pin Python to 3.11/3.12 until upgrade
2. Migrate to FastAPI Users 13.x
3. Rehash passwords on first login (pwdlib supports passlib hashes)

### Pitfall 4: asyncpg Pool Exhaustion

**What happens:** All pool connections in use, new requests queue indefinitely. App appears hung.

**Detection:**
- Request latency spikes to 30s+
- `asyncpg.pool.PoolConnectionLostError`
- "timeout expired while waiting for connection" errors

**Prevention:**
```python
pool = await asyncpg.create_pool(
    dsn=DATABASE_URL,
    min_size=10,
    max_size=40,  # Increase based on load
    command_timeout=30,  # Prevent queries from holding connections
    max_inactive_connection_lifetime=300,  # Recycle idle connections
)
```

**Recovery:**
1. Increase `max_size` based on concurrent requests
2. Add connection timeout to all queries
3. Use `conn.execute()` with timeout, not raw SQL
4. Monitor with Azure PostgreSQL metrics

### Pitfall 5: Azure Managed Identity Token Expiration

**What happens:** Azure tokens expire after 24 hours. Connection strings stop working, DB operations fail silently.

**Detection:**
- DB operations fail after 24 hours uptime
- `invalid_grant` errors in logs
- Works after container restart

**Prevention:**
```python
from azure.identity import DefaultAzureCredential

credential = DefaultAzureCredential()

async def get_connection_string():
    # Refresh token before each connection pool recreation
    token = credential.get_token("https://ossrdbms-aad.database.windows.net/.default")
    return f"postgresql://user@host:5432/db?password={token.token}"

# Recreate pool periodically or on token expiry
```

**Recovery:**
1. Implement token refresh callback
2. Recreate connection pool on auth errors
3. Use shorter pool lifetime (< 24 hours)

---

## High-Risk Pitfalls (Demo Failures)

### Pitfall 6: vLLM Streaming Broken by Proxy

**What happens:** NGINX or Azure reverse proxy buffers streaming response. User sees no output for 30+ seconds, then entire response at once.

**Detection:**
- Long TTFT (time to first token)
- Response arrives all at once
- Works locally, broken in production

**Prevention (NGINX):**
```nginx
location /v1/completions {
    proxy_pass http://vllm:8000;
    proxy_http_version 1.1;
    proxy_buffering off;
    proxy_cache off;
    chunked_transfer_encoding on;
}
```

**Prevention (Azure Container Apps):**
```yaml
# In container app config
configuration:
  ingress:
    transport: http2  # Or disable buffering
```

### Pitfall 7: CORS Blocks Frontend in Production

**What happens:** Works in dev (localhost), 403 CORS errors in production. Frontend can't reach backend.

**Detection:**
- Browser console: "CORS policy: No 'Access-Control-Allow-Origin'"
- Network tab shows preflight OPTIONS request failing

**Prevention:**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://inclusify.azurecontainerapps.io",
        "http://localhost:3000",  # Keep for dev
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Pitfall 8: Next.js Standalone Missing Static Files

**What happens:** Deployed Next.js app shows 404 for CSS, JS, images. Page loads but is unstyled/broken.

**Detection:**
- 404 errors for `/_next/static/*` paths
- Page loads but no styles
- Works in dev, broken in production

**Prevention:**
```dockerfile
# In Dockerfile, copy static files separately
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
```

### Pitfall 9: Hebrew RTL Rendering Breaks

**What happens:** Hebrew text displays backwards, mixed LTR/RTL content garbled. Unusable for Hebrew users.

**Detection:**
- Hebrew text reads right-to-left incorrectly
- Numbers in wrong position
- Mixed Hebrew/English breaks layout

**Prevention:**
```tsx
// In Next.js layout
<html lang={locale} dir={locale === 'he' ? 'rtl' : 'ltr'}>

// For specific elements with mixed content
<span dir="auto">{text}</span>

// CSS for proper alignment
.rtl-text {
  direction: rtl;
  text-align: right;
}
```

### Pitfall 10: JWT Refresh Race Condition

**What happens:** Multiple tabs refresh simultaneously. Each gets new refresh token, invalidating others. User logged out in other tabs.

**Detection:**
- Random logouts when multiple tabs open
- "Invalid refresh token" errors
- Single-tab use works fine

**Prevention:**
```typescript
// Frontend: Mutex for refresh
let isRefreshing = false;
let refreshSubscribers: ((token: string) => void)[] = [];

async function refreshToken() {
  if (isRefreshing) {
    return new Promise(resolve => refreshSubscribers.push(resolve));
  }
  isRefreshing = true;
  try {
    const newToken = await api.refresh();
    refreshSubscribers.forEach(cb => cb(newToken));
    return newToken;
  } finally {
    isRefreshing = false;
    refreshSubscribers = [];
  }
}
```

---

## Medium-Risk Pitfalls (Degraded Experience)

### Pitfall 11: Slow First Request (Cold Start)

**What happens:** First request after deployment takes 30-60 seconds. vLLM loading model, Docling loading weights.

**Detection:**
- First request timeout
- Subsequent requests fast
- Happens after every deployment

**Prevention:**
```yaml
# Azure Container Apps: Startup probe
readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 60
  periodSeconds: 10

# Keep minimum replicas warm
minReplicas: 1  # Never scale to zero
```

### Pitfall 12: Unhandled Hebrew Tokenization

**What happens:** LLM tokenizer breaks Hebrew words incorrectly. Analysis misses terms or creates false positives.

**Detection:**
- Hebrew analysis quality poor
- Same text in English works
- Tokenization splits mid-word

**Prevention:**
- Use multilingual model (suzume-llama-3-8B-multilingual) ✓
- Test with Hebrew-specific validation set
- Consider Hebrew-first prompt templates

### Pitfall 13: PDF Layout Lost in Extraction

**What happens:** Multi-column academic papers extracted as single column. Context lost, analysis incorrect.

**Detection:**
- Two-column PDF becomes garbled text
- Tables extracted as random strings
- Headers mixed with body

**Prevention:**
```python
from docling.datamodel.pipeline_options import PdfPipelineOptions

options = PdfPipelineOptions()
options.do_table_structure = True
options.generate_page_images = False  # Speed optimization
options.table_structure_options.mode = "accurate"

converter = DocumentConverter(
    allowed_formats=[DocumentFormat.PDF],
    pdf_pipeline_options=options,
)
```

### Pitfall 14: Missing Rate Limiting Causes Abuse

**What happens:** Single user sends 1000 requests. GPU overloaded, other users blocked. No protection.

**Detection:**
- Sudden spike in requests from single IP
- vLLM queue depth explodes
- Legitimate users timeout

**Prevention:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/v1/analysis/analyze")
@limiter.limit("10/minute")
async def analyze(request: Request):
    ...
```

### Pitfall 15: Secrets Leaked in Error Messages

**What happens:** Stack trace exposes database URL with password, API keys in logs.

**Detection:**
- Passwords visible in error responses
- API keys in log files
- Security audit fails

**Prevention:**
```python
# Custom exception handler
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    # Log full error internally
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    # Return sanitized error to client
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again."}
    )

# Never log connection strings
import re
def sanitize_log(message: str) -> str:
    return re.sub(r'password=[^&\s]+', 'password=***', message)
```

### Pitfall 16: Private Mode Text Stored Anyway

**What happens:** User enables private mode, but text still written to DB due to bug. Privacy violation.

**Detection:**
- DB audit shows text in private documents
- User privacy complaint
- Compliance audit failure

**Prevention:**
```sql
-- DB constraint (already in schema)
ALTER TABLE documents
ADD CONSTRAINT chk_private_no_content
CHECK (NOT is_private OR content IS NULL);
```

```python
# Application layer double-check
if request.private_mode:
    assert document.content is None, "Private mode violation"
```

---

## Recovery Procedures

### General Recovery Steps

1. **Identify:** Check logs, metrics, user reports
2. **Isolate:** Disable affected component (feature flag, routing)
3. **Fix:** Apply mitigation from this document
4. **Verify:** Test in staging before production
5. **Document:** Add to post-mortem, update this document

### Emergency Contacts

- Azure Support: Azure Portal → Support + Troubleshooting
- vLLM Issues: https://github.com/vllm-project/vllm/issues
- Docling Issues: https://github.com/docling-project/docling/issues

---

## Monitoring Checklist

| Metric | Threshold | Action |
|--------|-----------|--------|
| vLLM VRAM usage | >14GB | Consider quantization |
| API latency p99 | >5s | Check vLLM queue, DB connections |
| Error rate | >1% | Check logs, trigger alert |
| Connection pool usage | >80% | Increase pool size |
| Container restarts | >2/hour | Check OOM, startup issues |
| Token refresh failures | >10/hour | Check Redis, token logic |

---

## Sources

- vLLM Production Guide: https://docs.vllm.ai/en/stable/serving/
- FastAPI Security: https://fastapi.tiangolo.com/tutorial/security/
- Azure Container Apps Troubleshooting: https://learn.microsoft.com/azure/container-apps/
- asyncpg Best Practices: https://magicstack.github.io/asyncpg/

---

*Last updated: 2026-03-08*
