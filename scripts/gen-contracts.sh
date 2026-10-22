#!/usr/bin/env bash
# Regenerate the API contract and both clients.
#
#   FastAPI ──► openapi.json ──┬──► TypeScript types + client  (apps/web)
#                              └──► Dart models                (apps/mobile)
#
# Types flow ONE direction. Nothing here is hand-edited; ci-contracts.yml fails
# the build when the committed output is stale, so a schema change cannot merge
# without its clients updated in the same PR.
set -euo pipefail
cd "$(dirname "$0")/.."

OUT=packages/contracts/openapi/openapi.json

echo "→ exporting OpenAPI schema from services/api"
docker compose exec -T api python -c \
  "import json;from app.main import create_app;print(json.dumps(create_app().openapi(), indent=2))" \
  > "$OUT"

echo "→ generating TypeScript client"
pnpm --filter @janmaang/contracts exec openapi-typescript "$OUT" \
  -o packages/contracts/src/generated/api.ts

echo "→ generating Dart models"
# TODO(contracts): openapi-generator dart-dio, or a small script into
# apps/mobile/lib/shared/models/generated/.
echo "  (dart generation not yet wired)"

echo "✓ contracts regenerated — commit the output alongside the schema change"
