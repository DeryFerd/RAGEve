# RAGEve Backend Dockerfile
# Multi-stage build for production-ready FastAPI application

FROM python:3.12-slim AS builder

# Install uv (fast Python package manager)
ENV UV_LINK_MODE=copy
ENV UV_COMPILE_BYTECODE=1
ENV UV_PYTHON=python3.12
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml .

# Install dependencies into a virtual environment
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv /app/.venv && \
    uv pip install -e ".[test]"


# ── Final image ───────────────────────────────────────────────────────────────
FROM python:3.12-slim

# Install system dependencies required by OCR and PDF processing
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    libgl1 \
    libglib2.0-0 \
    tesseract-ocr \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Make sure we use the virtual environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Copy backend application code and rag package
COPY backend/ ./backend/
COPY rag/ ./rag/
COPY pyproject.toml .

# Create necessary directories with proper permissions
RUN mkdir -p data/uploads data/chunks data/vectors data/logs data/hf && \
    chown -R app:app /app

# Switch to non-root user
USER app

# Expose FastAPI port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
