#!/usr/bin/env bash
# Post-deploy verification. Fails the deploy (and triggers rollback) if the
# service is up but not actually working.
set -euo pipefail

BASE_URL="${1:?usage: smoke-test.sh <base-url>}"
fail() { echo "✗ $1" >&2; exit 1; }

echo "→ smoke testing $BASE_URL"

code=$(curl -fsS -o /dev/null -w '%{http_code}' "$BASE_URL/health" || echo 000)
[ "$code" = "200" ] || fail "health returned $code"
echo "  ✓ health"

# The OpenAPI schema serving proves routing and app construction, not just that
# a process is listening.
code=$(curl -fsS -o /dev/null -w '%{http_code}' "$BASE_URL/api/v1/openapi.json" || echo 000)
[ "$code" = "200" ] || fail "openapi schema returned $code"
echo "  ✓ api routes registered"

# An unauthenticated call to a protected endpoint must be rejected. If this ever
# returns 200, authorisation is off and the deploy must not proceed.
code=$(curl -fsS -o /dev/null -w '%{http_code}' "$BASE_URL/api/v1/audit" || echo 000)
[ "$code" = "401" ] || [ "$code" = "403" ] || [ "$code" = "404" ] \
  || fail "protected endpoint returned $code — authorisation may be disabled"
echo "  ✓ protected endpoints reject anonymous callers"

echo "✓ smoke tests passed"
