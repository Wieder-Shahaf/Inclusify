# Inclusify Backend Dockerfile
# Multi-stage build for FastAPI application

# ============================================
# Stage 1: Builder - Install dependencies
# ============================================
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY backend/requirements.txt .

# Install everything in ONE resolution with the PyTorch CPU index as primary
# and PyPI as fallback. Inference runs remotely over HTTP (VLLM_URL), so the
# GPU/CUDA builds of torch + torchvision (which drag in ~3.5GB of nvidia/triton)
# are dead weight here. With the CPU index primary, both torch and torchvision
# resolve to their +cpu wheels (the +cpu local version outranks the PyPI CUDA
# build), and everything else falls back to PyPI. A single pip install avoids
# the --prefix "already satisfied" blind spot that previously let a CUDA
# torchvision sneak back in on a second install.
RUN pip install --no-cache-dir --prefix=/install \
    --index-url https://download.pytorch.org/whl/cpu \
    --extra-index-url https://pypi.org/simple \
    -r requirements.txt

# ============================================
# Stage 2: Development - Hot-reload enabled
# ============================================
FROM python:3.12-slim AS development

# Build args for version info
ARG BUILD_TIME
ARG GIT_COMMIT

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    BUILD_TIME=${BUILD_TIME} \
    GIT_COMMIT=${GIT_COMMIT} \
    # Cache directories for Docling/RapidOCR (writable by appuser)
    HF_HOME=/home/appuser/.cache/huggingface \
    TORCH_HOME=/home/appuser/.cache/torch \
    XDG_CACHE_HOME=/home/appuser/.cache

WORKDIR /app

# Install runtime dependencies (including Docling PDF processing libs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    libxcb1 \
    libx11-6 \
    libxext6 \
    libxrender1 \
    libgl1 \
    libglib2.0-0 \
    tesseract-ocr \
    tesseract-ocr-heb \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Fix permissions for RapidOCR model downloads (Docling dependency)
RUN chmod -R 777 /usr/local/lib/python3.12/site-packages/rapidocr*/models 2>/dev/null || true

# Create non-root user with home directory (needed for Docling cache)
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid 1000 --shell /bin/bash --create-home appuser \
    && chown -R appuser:appuser /app

# Install dev/test dependencies (base deps already present from builder; pip
# only adds the extra test tooling). Kept out of the runtime stage.
COPY backend/requirements-dev.txt backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

# Copy application code
COPY --chown=appuser:appuser backend/app ./app

USER appuser

EXPOSE 8000

# Development entrypoint with hot-reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ============================================
# Stage 3: Runtime - Production optimized
# ============================================
FROM python:3.12-slim AS runtime

# Build args for version info
ARG BUILD_TIME
ARG GIT_COMMIT

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    BUILD_TIME=${BUILD_TIME} \
    GIT_COMMIT=${GIT_COMMIT} \
    # Cache dirs for Docling/HF weights — baked below so startup needs no network
    HF_HOME=/home/appuser/.cache/huggingface \
    TORCH_HOME=/home/appuser/.cache/torch \
    XDG_CACHE_HOME=/home/appuser/.cache \
    # Cap CPU parallelism so a single docling conversion uses less peak RAM
    # (torch allocates per-thread scratch buffers). Slower inference, lower peak
    # — the accepted memory-for-time trade on a constrained host. Inherited by
    # the spawned parse worker.
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    # glibc otherwise opens one 64MB arena PER thread; each fragments and inflates
    # RSS. Two arenas keeps container RSS close to real usage.
    MALLOC_ARENA_MAX=2

WORKDIR /app

# Install runtime dependencies (including Docling PDF processing libs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    libxcb1 \
    libx11-6 \
    libxext6 \
    libxrender1 \
    libgl1 \
    libglib2.0-0 \
    tesseract-ocr \
    tesseract-ocr-heb \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Fix permissions for RapidOCR model downloads (Docling dependency)
RUN chmod -R 777 /usr/local/lib/python3.12/site-packages/rapidocr*/models 2>/dev/null || true

# Create non-root user with home directory (needed for Docling cache)
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid 1000 --shell /bin/bash --create-home appuser \
    && chown -R appuser:appuser /app

# Copy application code
COPY --chown=appuser:appuser backend/app ./app
COPY --chown=appuser:appuser backend/requirements.txt .

USER appuser

# Bake Docling/HF model weights into the image. Railway containers are
# ephemeral, so without this every boot re-downloads from HF. Docling loads its
# layout/table vision models LAZILY on the first real .convert() — merely
# constructing the converter does NOT cache them — so we convert a throwaway
# one-page PDF here to force every model (MiniLM tokenizer, docling-layout-heron,
# TableFormer) into HF_HOME. This must stay a real conversion, not just object
# construction, or HF_HUB_OFFLINE=1 below breaks the first upload in prod.
RUN python -c "import tempfile; from pypdf import PdfWriter; from app.modules.ingestion.service import _get_docling_converter, _get_hybrid_chunker; w=PdfWriter(); w.add_blank_page(width=595, height=842); p=tempfile.mktemp(suffix='.pdf'); f=open(p,'wb'); w.write(f); f.close(); _get_docling_converter().convert(p); _get_hybrid_chunker(); print('Docling build warm-up conversion OK')"

# Weights are baked above — load them offline at runtime so startup never touches
# the network. Set AFTER the warm-up RUN so the build itself can still download.
ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

EXPOSE 8000

# Production entrypoint (no hot-reload).
# --proxy-headers + --forwarded-allow-ips=* make request.client.host the real
# caller instead of Railway's edge proxy. Without this, uvicorn only trusts
# X-Forwarded-For from 127.0.0.1, so every client collapses into a handful of
# proxy-IP buckets and per-IP rate limits are shared across unrelated users.
# "*" is safe here because the container is only reachable through Railway's
# proxy, which always overwrites X-Forwarded-For.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
