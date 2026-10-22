#!/usr/bin/env bash
# Restore from a backup produced by backup.sh. DESTRUCTIVE — requires an
# explicit confirmation so it cannot be run by reflex.
set -euo pipefail

DUMP="${1:?usage: restore.sh <dump-file>}"
: "${DATABASE_URL:?DATABASE_URL must be set}"

echo "This will OVERWRITE the database at:"
echo "  ${DATABASE_URL%%\?*}"
read -r -p "Type 'restore' to continue: " confirm
[ "$confirm" = "restore" ] || { echo "aborted"; exit 1; }

pg_restore --clean --if-exists --no-owner --no-acl -d "$DATABASE_URL" "$DUMP"
echo "✓ restored from $DUMP"
