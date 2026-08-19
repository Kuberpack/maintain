#!/usr/bin/env bash
# Daily PostgreSQL backup for the Machine Maintenance & Cleaning Tracker.
# Dumps the database to backups/ (compressed), pruning dumps older than
# BACKUP_RETENTION_DAYS. Meant to be run once a day via host cron -- see
# README.md for how to schedule it.
#
# Works whether Postgres is running via docker-compose (which publishes
# 5432 to the host) or as a bare-metal install; connects over TCP either
# way, so it always runs on the host, never inside a container.
#
# Usage: ./scripts/backup.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$REPO_ROOT/backups"

# Same POSTGRES_USER/PASSWORD/DB variables docker-compose.yml already uses,
# read from the same root .env -- one source of truth for these values.
if [ -f "$REPO_ROOT/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$REPO_ROOT/.env"
  set +a
fi

POSTGRES_USER="${POSTGRES_USER:-maintain}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-maintain}"
POSTGRES_DB="${POSTGRES_DB:-maintain}"
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"

mkdir -p "$BACKUP_DIR"

timestamp="$(date +%Y%m%d_%H%M%S)"
dump_file="$BACKUP_DIR/${POSTGRES_DB}_${timestamp}.sql.gz"
tmp_file="${dump_file}.tmp"
trap 'rm -f "$tmp_file"' EXIT

echo "Backing up $POSTGRES_DB@$POSTGRES_HOST:$POSTGRES_PORT -> $dump_file"
PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
  -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" "$POSTGRES_DB" \
  | gzip > "$tmp_file"
mv "$tmp_file" "$dump_file"

echo "Wrote $(du -h "$dump_file" | cut -f1)"

echo "Pruning backups older than ${BACKUP_RETENTION_DAYS}d"
find "$BACKUP_DIR" -name "${POSTGRES_DB}_*.sql.gz" -mtime "+$BACKUP_RETENTION_DAYS" -print -delete
