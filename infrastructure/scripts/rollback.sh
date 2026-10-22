#!/usr/bin/env bash
# Roll production back to the previously deployed image tag.
#
# Rolling back CODE is safe. Rolling back a MIGRATION usually is not — a
# destructive migration cannot be undone by redeploying the old image, which is
# why backup.sh runs first and why migrations should be additive wherever
# possible (add a column, backfill, then drop in a later release).
set -euo pipefail

echo "→ rolling back to the previous image tag"
# TODO(infra): retag :previous → :production and roll the services.
echo "TODO: implement for the chosen platform (Cloud Run / ECS / Container Apps)"
echo
echo "If the failed deploy included a migration, restore from the pre-deploy"
echo "backup instead — see infrastructure/scripts/restore.sh."
