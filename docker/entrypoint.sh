#!/bin/bash
set -x

echo "=== Entrypoint starting ==="
id
ls -la /RAGEve/
ls -la /RAGEve/data 2>&1 || echo "data dir does not exist yet"

# Fix ownership of data directory (volume mounts may be owned by root)
if [ -d "/RAGEve/data" ]; then
    echo "Fixing ownership of /RAGEve/data"
    chown -R app:rageve /RAGEve/data
    ls -la /RAGEve/data
fi

# Ensure logs directory exists
echo "Creating logs directory"
mkdir -p /RAGEve/data/logs
ls -la /RAGEve/data/logs 2>&1 || echo "Failed to create logs"

echo "=== Entrypoint done, executing: $@ ==="
exec "$@"
