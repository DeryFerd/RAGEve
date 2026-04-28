#!/usr/bin/env bash
# ── RAGEve — Backend only ─────────────────────────────────────────────────────
# Starts: Qdrant + MySQL + FastAPI backend (all via Docker Compose)
# Does NOT start the Next.js frontend.
#
# For technical users who run the frontend manually (e.g. npm run dev).
#   ./scripts/backend.sh
#
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/rageve.sh

# ── Banner ─────────────────────────────────────────────────────────────────────
clear
show_banner

log_info "Starting backend services (no frontend)..."
echo

# ── Docker check ──────────────────────────────────────────────────────────────
if ! check_docker; then
  log_error "Docker must be running. Please start Docker Desktop and re-run."
  exit 1
fi

# ── Start services ────────────────────────────────────────────────────────────
log_info "Starting Qdrant + MySQL + Backend via Docker Compose..."
docker compose -f docker/docker-compose.yml up -d qdrant mysql backend

# ── Wait for Qdrant ───────────────────────────────────────────────────────────
for i in $(seq 1 30); do
  if curl -sf http://localhost:6333/collections &>/dev/null; then
    break
  fi
  sleep 1
done
if curl -sf http://localhost:6333/collections &>/dev/null; then
  log_success "Qdrant ready."
else
  log_error "Qdrant failed to start. Check: docker compose -f docker/docker-compose.yml logs qdrant"
  docker compose -f docker/docker-compose.yml logs qdrant
  exit 1
fi

# ── Wait for Backend ──────────────────────────────────────────────────────────
for i in $(seq 1 30); do
  if curl -sf http://localhost:8000/health &>/dev/null; then
    break
  fi
  sleep 1
done
if curl -sf http://localhost:8000/health &>/dev/null; then
  log_success "Backend ready."
else
  log_warn "Backend may still be starting..."
fi

log_success "All backend services are running."
echo
log_info "Streaming backend logs (press Ctrl+C to stop):"
echo

# ── Stream logs & cleanup ─────────────────────────────────────────────────────
trap 'docker compose -f docker/docker-compose.yml down' INT TERM
docker compose -f docker/docker-compose.yml logs -f backend
docker compose -f docker/docker-compose.yml down
