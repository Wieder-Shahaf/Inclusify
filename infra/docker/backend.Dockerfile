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

# Copy application code
COPY --chown=appuser:appuser backend/app ./app
COPY --chown=appuser:appuser backend/requirements.txt .

USER appuser

# Bake Docling/HF model weights into the image by running the real warm-up at
# build time. Railway containers are ephemeral, so without this the HF cache is
# empty on every boot and startup re-downloads all-MiniLM-L6-v2 unauthenticated
# (rate-limit exposed, HF-availability dependent). This lands them in HF_HOME.
RUN python -c "import asyncio; from app.modules.ingestion.service import warm_up_docling; asyncio.run(warm_up_docling())"

# Weights are baked above — load them offline at runtime so startup never touches
# the network. Set AFTER the warm-up RUN so the build itself can still download.
ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

EXPOSE 8000

# Production entrypoint (no hot-reload)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
