FROM ubuntu:24.04 AS base
USER root
SHELL ["/bin/bash", "-c"]

WORKDIR /RAGEve

# Install build dependencies and Python
RUN apt-get update -o Acquire::Retries=3 && \
    apt-get install -y --no-install-recommends \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    gcc \
    g++ \
    make \
    libssl-dev \
    libffi-dev \
    pkg-config \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv (deterministic, fast package manager)
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON=python3.12
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /RAGEve

# Copy dependency manifests and source code for build
COPY pyproject.toml uv.lock ./
COPY backend/ ./backend/
COPY rag/ ./rag/

# Install only production dependencies (no test, dev, eval)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv /RAGEve/.venv && \
    uv pip install . && \
    # Install gunicorn for production serving
    uv pip install gunicorn==23.0.0

# ============================================
# STAGE 2: Production Runtime Image
# ============================================
FROM ubuntu:24.04 AS runtime

# Metadata labels
LABEL org.opencontainers.image.title="RAGEve Backend" \
      org.opencontainers.image.description="FastAPI backend for local-first RAG platform" \
      org.opencontainers.image.vendor="RAGEve" \
      org.opencontainers.image.licenses="Apache-2.0"

# Set non-interactive
ENV DEBIAN_FRONTEND=noninteractive

# Install runtime system dependencies including Python
RUN apt-get update -o Acquire::Retries=3 && \
    apt-get install -y --no-install-recommends \
    python3.12 \
    python3.12-venv \
    curl \
    ca-certificates \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    libssl3 \
    libffi8 \
    zlib1g \
    tesseract-ocr \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root user for security
# Use high UID/GID to avoid conflicts with base image's default user (1000)
RUN groupadd -r -g 1001 rageve && \
    useradd -r -u 1001 -g rageve -s /bin/bash -d /RAGEve -m app && \
    mkdir -p /RAGEve/conf /RAGEve/data /app/conf && \
    chown -R app:rageve /RAGEve /app

WORKDIR /RAGEve

# Copy virtual environment from builder
COPY --from=builder /RAGEve/.venv /RAGEve/.venv

# Activate virtual environment
ENV PATH="/RAGEve/.venv/bin:$PATH" \
    PYTHONPATH=/RAGEve \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Copy application code (order matters for Docker layer caching)
COPY backend/ ./backend/
COPY rag/ ./rag/
COPY pyproject.toml .

# Copy configuration files to both locations for compatibility
COPY docker/conf/service_conf.yaml /RAGEve/conf/
COPY docker/service_conf.yaml.template /RAGEve/conf/
COPY docker/conf/service_conf.yaml /app/conf/
COPY docker/service_conf.yaml.template /app/conf/
COPY docker/conf/service_conf.yaml /app/

# Copy entrypoint script
COPY docker/entrypoint.sh /RAGEve/entrypoint.sh
RUN chmod +x /RAGEve/entrypoint.sh


# Create data directories with proper permissions (as non-root user)
RUN mkdir -p data/uploads data/chunks data/vectors data/logs data/hf

# Expose FastAPI port
EXPOSE 8000

# Health check (lightweight, uses Python)
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import httpx; r = httpx.get('http://localhost:8000/health', timeout=3); exit(0 if r.status_code == 200 else 1)" || exit 1

# Production server configuration with Gunicorn + Uvicorn workers
ENV GUNICORN_WORKERS=${GUNICORN_WORKERS:-4} \
    GUNICORN_THREADS=${GUNICORN_THREADS:-2} \
    GUNICORN_TIMEOUT=${GUNICORN_TIMEOUT:-120} \
    GUNICORN_BACKLOG=${GUNICORN_BACKLOG:-2048}

# Run with entrypoint to fix permissions, then Gunicorn
ENTRYPOINT ["/RAGEve/entrypoint.sh"]
CMD exec gunicorn backend.main:app \
    --bind 0.0.0.0:8000 \
    --workers ${GUNICORN_WORKERS} \
    --threads ${GUNICORN_THREADS} \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout ${GUNICORN_TIMEOUT} \
    --backlog ${GUNICORN_BACKLOG} \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
