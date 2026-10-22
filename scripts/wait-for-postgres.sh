#!/usr/bin/env bash
# Block until Postgres accepts connections. Compose healthchecks cover service
# startup ordering; this covers `make reset-db` and CI, where we shell out directly.
set -euo pipefail
cd "$(dirname "$0")/.."

for i in $(seq 1 60); do
  if docker compose exec -T postgres pg_isready -U "${POSTGRES_USER:-janmaang}" >/dev/null 2>&1; then
    echo "  postgres ready"
    exit 0
  fi
  sleep 1
done
echo "postgres did not become ready in 60s" >&2
exit 1
