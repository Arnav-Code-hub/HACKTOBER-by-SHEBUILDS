#!/usr/bin/env bash
# Database backup. Runs before every production migration — a migration is the
# least reversible thing that ships, so it never runs without a restore point.
set -euo pipefail

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${BACKUP_DIR:-/tmp}/janmaang-${STAMP}.dump"

: "${DATABASE_URL:?DATABASE_URL must be set}"

echo "→ backing up to $OUT"
pg_dump --format=custom --no-owner --no-acl "$DATABASE_URL" > "$OUT"
echo "✓ backup written ($(du -h "$OUT" | cut -f1))"

# TODO(infra): upload to object storage with a retention policy. A backup that
# lives only on the machine being migrated is not a backup.
echo "TODO: upload $OUT to durable storage"
