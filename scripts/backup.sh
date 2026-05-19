#!/usr/bin/env bash
# Usage: ./scripts/backup.sh
#   BACKUP_DIR=./backups DB_PATH=./data/expenses.db ./scripts/backup.sh
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
DB_PATH="${DB_PATH:-./data/expenses.db}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

if [ ! -f "$DB_PATH" ]; then
    echo "Error: database not found at $DB_PATH" >&2
    exit 1
fi

DEST="$BACKUP_DIR/expenses_${TIMESTAMP}.db"
cp "$DB_PATH" "$DEST"
echo "Backup saved: $DEST"

# Retain only the 7 most recent backups
ls -t "$BACKUP_DIR"/expenses_*.db 2>/dev/null | tail -n +8 | xargs -r rm -f
