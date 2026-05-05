#!/bin/bash
set -e

# RAGEve Backend Services Launcher
# Checks dependencies, starts FastAPI backend with auto-restart

# Get project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Config
MAX_RETRIES=${WS_MAX_RETRIES:-5}
WS=${WS:-1}
ENV_FILE=${WS_ENV_FILE:-".env"}

# Global state
STOP=false
PIDS=()

# Load environment from file
load_env() {
  local env_path="$1"
  if [ -f "$env_path" ]; then
    echo "Loading: $env_path"
    set -a
    source "$env_path"
    set +a
  else
    echo "Warning: env file not found: $env_path"
  fi
}

# Clean shutdown
cleanup() {
  echo "Shutting down..."
  STOP=true
  for pid in "${PIDS[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
  exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# Check TCP port
check_port() {
  local host=$1 port=$2
  if command -v nc &>/dev/null; then
    nc -z -w 3 "$host" "$port" &>/dev/null
    return $?
  fi
  timeout 3 bash -c "cat < /dev/null > /dev/tcp/$host/$port" &>/dev/null 2>&1 || \
  curl -s --max-time 3 "http://$host:$port/health" &>/dev/null || \
  curl -s --max-time 3 "http://$host:$port/collections" &>/dev/null
  return $?
}

# Service checks
check_mysql() {
  echo -n "MySQL... "
  if check_port "localhost" "${MYSQL_PORT:-3306}"; then
    echo "OK"
    return 0
  fi
  echo "FAIL (localhost:${MYSQL_PORT:-3306})"
  return 1
}

check_qdrant() {
  echo -n "Qdrant... "
  if check_port "localhost" "${QDRANT_PORT:-6333}" && \
     curl -s --max-time 3 "http://localhost:${QDRANT_PORT:-6333}/collections" | grep -q '"result"'; then
    echo "OK"
    return 0
  fi
  echo "FAIL"
  return 1
}

check_redis() {
  echo -n "Redis... "
  if ! check_port "localhost" "${REDIS_PORT:-6379}"; then
    echo "FAIL"
    return 1
  fi
  if command -v redis-cli &>/dev/null; then
    if redis-cli -h localhost -p "${REDIS_PORT:-6379}" ping 2>/dev/null | grep -q "PONG"; then
      echo "OK"
      return 0
    fi
  fi
  echo "OK (port open)"
  return 0
}

check_minio() {
  echo -n "MinIO... "
  if check_port "localhost" "${MINIO_PORT:-9000}"; then
    echo "OK"
    return 0
  fi
  echo "FAIL"
  return 1
}

check_services() {
  echo "Checking services:"
  check_mysql || return 1
  check_qdrant || return 1
  check_redis || return 1
  check_minio || return 1
  return 0
}

# Backend runner with retry
run_backend() {
  local retry=0
  cd "$PROJECT_ROOT"
  export PYTHONPATH="$PROJECT_ROOT"
  export PYTHONUNBUFFERED=1

  while [ $retry -lt $MAX_RETRIES ] && [ "$STOP" = false ]; do
    echo "Starting backend (attempt $((retry+1))/$MAX_RETRIES)..."

    if [ "$WS" -gt 1 ] && command -v gunicorn &>/dev/null; then
      CMD="gunicorn backend.main:app -w $WS -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000"
    elif command -v uv &>/dev/null; then
      CMD="uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000"
    else
      CMD="python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000"
    fi

    echo "Command: $CMD"
    bash -c "$CMD"
    local code=$?

    if [ $code -eq 0 ]; then
      echo "Backend exited cleanly."
      break
    fi

    echo "Backend exited with code $code, retrying in 2s..." >&2
    retry=$((retry+1))
    sleep 2
  done

  if [ $retry -ge $MAX_RETRIES ]; then
    echo "Max retries reached, exiting." >&2
    return 1
  fi
}

main() {
  echo "RAGEve Backend Launcher"
  echo "======================="

  # Load env (try both locations)
  if [ -f ".env" ]; then
    load_env ".env"
  elif [ -f "docker/.env" ]; then
    (cd "$PROJECT_ROOT/docker" && load_env ".env")
  fi

  # Check services
  echo
  if ! check_services; then
    echo
    echo "Services not ready. Start with:"
    echo "  docker compose -f docker/docker-compose.yml up -d"
    exit 1
  fi
  echo "All services healthy."

  # Start backend
  echo
  run_backend &
  PIDS+=($!)
  wait "${PIDS[@]}"
}

main "$@"
