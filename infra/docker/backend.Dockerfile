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

# Install Python dependencies
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

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
    GIT_COMMIT=${GIT_COMMIT}

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
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Create non-root user with home directory (needed for Docling cache)
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid 1000 --shell /bin/bash --create-home appuser \
    && chown -R appuser:appuser /app

# Copy application code
COPY --chown=appuser:appuser backend/app ./app
COPY --chown=appuser:appuser backend/requirements.txt .

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
    GIT_COMMIT=${GIT_COMMIT}

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Create non-root user with home directory (needed for Docling cache)
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid 1000 --shell /bin/bash --create-home appuser \
    && chown -R appuser:appuser /app

# Copy application code
COPY --chown=appuser:appuser backend/app ./app
COPY --chown=appuser:appuser backend/requirements.txt .

USER appuser

EXPOSE 8000

# Production entrypoint (no hot-reload)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
