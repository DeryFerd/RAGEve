#!/bin/bash
# RAGEve Docker Backup Script
# Creates backups of MySQL database and Qdrant vectors

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
MYSQL_CONTAINER="${MYSQL_CONTAINER:-rageve-mysql}"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS="${RETENTION_DAYS:-30}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}RAGEve Backup - ${DATE}${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if containers are running
if ! docker ps | grep -q "$MYSQL_CONTAINER"; then
    echo -e "${RED}Error: MySQL container '$MYSQL_CONTAINER' is not running${NC}"
    exit 1
fi

# Load environment variables from .env if exists
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

# Backup MySQL
echo -e "${YELLOW}Backing up MySQL database...${NC}"
MYSQL_PASSWORD="${MYSQL_ROOT_PASSWORD:-rag_eve}"
MYSQL_DB="${MYSQL_DBNAME:-rag_eve}"

docker exec "$MYSQL_CONTAINER" mysqldump \
    --single-transaction \
    --routines \
    --triggers \
    --events \
    --add-drop-database \
    --default-character-set=utf8mb4 \
    "$MYSQL_DB" > "$BACKUP_DIR/mysql_$MYSQL_DB_$DATE.sql"

gzip "$BACKUP_DIR/mysql_$MYSQL_DB_$DATE.sql"
echo -e "${GREEN}MySQL backup created: mysql_$MYSQL_DB_$DATE.sql.gz${NC}"

# Backup Qdrant collections (snapshot)
echo -e "${YELLOW}Backing up Qdrant vector collections...${NC}"
COLLECTIONS=$(docker exec rageve-qdrant curl -s "http://localhost:6333/collections" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for coll in data.get('result', {}).get('collections', []):
    print(coll['name'])
" 2>/dev/null || echo "")

for collection in $COLLECTIONS; do
    echo "  Creating snapshot for collection: $collection"
    SNAPSHOT_NAME="qdrant_${collection}_${DATE}"
    docker exec rageve-qdrant curl -s -X POST \
        "http://localhost:6333/collections/$collection/snapshots" \
        -H "Content-Type: application/json" \
        -d '{"location": "'"$SNAPSHOT_NAME"'"}'
    # Download snapshot if API key is set
    if [ -n "${QDRANT_API_KEY:-}" ]; then
        curl -s -H "api-key: $QDRANT_API_KEY" \
            "http://localhost:6333/collections/$collection/snapshots/$SNAPSHOT_NAME" \
            -o "$BACKUP_DIR/$SNAPSHOT_NAME.snapshot"
    fi
done
echo -e "${GREEN}Qdrant snapshots created${NC}"

# Backup MinIO data (if using MinIO)
echo -e "${YELLOW}Checking MinIO for data backup...${NC}"
if docker ps | grep -q "rageve-minio"; then
    echo "  MinIO is running, creating bucket backup..."
    # Install mc client if not present
    if ! command -v mc &> /dev/null; then
        echo "  mc (MinIO client) not found. Install from: https://min.io/docs/minio/linux/reference/minio-mc.html"
        echo "  Skipping MinIO backup..."
    else
        # Configure mc
        mc alias set minio http://localhost:9000 "${MINIO_USER:-rag_eve}" "${MINIO_PASSWORD:-rag_eve}"
        mc mirror --overwrite minio/rageve "$BACKUP_DIR/minio_$DATE/"
        echo -e "${GREEN}MinIO backup created: minio_$DATE/${NC}"
    fi
else
    echo "  MinIO container not running, skipping..."
fi

# Create backup manifest
echo "Backup created: $DATE" > "$BACKUP_DIR/backup_$DATE.manifest"
echo "MySQL: mysql_$MYSQL_DB_$DATE.sql.gz" >> "$BACKUP_DIR/backup_$DATE.manifest"
echo "Qdrant: snapshots for collections" >> "$BACKUP_DIR/backup_$DATE.manifest"
if [ -d "$BACKUP_DIR/minio_$DATE" ]; then
    echo "MinIO: minio_$DATE/" >> "$BACKUP_DIR/backup_$DATE.manifest"
fi

# Cleanup old backups (retention policy)
echo -e "${YELLOW}Cleaning up backups older than ${RETENTION_DAYS} days...${NC}"
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "*.snapshot" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "backup_*.manifest" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
find "$BACKUP_DIR" -type d -name "minio_*" -mtime +$RETENTION_DAYS -exec rm -rf {} + 2>/dev/null || true

# List current backups
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Backup Summary${NC}"
echo -e "${GREEN}========================================${NC}"
echo "Backup directory: $BACKUP_DIR"
echo "Recent backups:"
ls -lh "$BACKUP_DIR"/*.sql.gz 2>/dev/null | tail -5 || echo "  No SQL backups found"
ls -lh "$BACKUP_DIR"/*.manifest 2>/dev/null | tail -3 || echo "  No manifests found"
echo ""
echo -e "${GREEN}Backup completed successfully!${NC}"
