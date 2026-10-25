#!/usr/bin/env bash
# Diagnose a broken environment. Read-only — changes nothing.
set -uo pipefail
cd "$(dirname "$0")/.."

bold() { printf '\n\033[1m%s\033[0m\n' "$1"; }
ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$1"; }
fail() { printf '  \033[31m✗\033[0m %s\n' "$1"; }

bold "Tool versions"
for t in docker node pnpm uv flutter python3 make; do
  if command -v "$t" >/dev/null 2>&1; then
    ok "$t $("$t" --version 2>&1 | head -1)"
  else
    fail "$t not found"
  fi
done

bold "Environment files"
while IFS= read -r example; do
  env_file="${example%.example}"
  if [ -f "$env_file" ]; then
    missing_keys=$(comm -23 \
      <(grep -oE '^[A-Z_][A-Z0-9_]*' "$example" | sort -u) \
      <(grep -oE '^[A-Z_][A-Z0-9_]*' "$env_file" | sort -u) | tr '\n' ' ')
    if [ -n "${missing_keys// /}" ]; then
      warn "$env_file is missing: $missing_keys"
    else
      ok "$env_file"
    fi
  else
    fail "$env_file missing — run: make setup"
  fi
done < <(find . -name '.env.example' -not -path './.git/*' -not -path '*/node_modules/*' | sort)

bold "Ports"
for p in 3000 5432 6379 8000 8001; do
  if lsof -nP -iTCP:"$p" -sTCP:LISTEN >/dev/null 2>&1; then
    ok "$p in use — $(lsof -nP -iTCP:"$p" -sTCP:LISTEN -Fc 2>/dev/null | grep '^c' | head -1 | cut -c2-)"
  else
    warn "$p free (service not running?)"
  fi
done

bold "Containers"
docker compose ps 2>/dev/null || fail "docker compose unavailable — is Docker running?"

bold "Database"
if docker compose exec -T postgres pg_isready -U janmaang >/dev/null 2>&1; then
  ok "postgres accepting connections"
  ext=$(docker compose exec -T postgres psql -U janmaang -d janmaang -tAc \
        "select string_agg(extname, ', ') from pg_extension" 2>/dev/null)
  [ -n "$ext" ] && ok "extensions: $ext"
else
  warn "postgres not reachable — try: make dev"
fi

bold "Secret scanning"
if command -v gitleaks >/dev/null 2>&1; then
  gitleaks detect --no-banner --redact -c .gitleaks.toml >/dev/null 2>&1 \
    && ok "no secrets detected" || fail "gitleaks found something — run: gitleaks detect -c .gitleaks.toml"
else
  warn "gitleaks not installed (CI still enforces this)"
fi
echo
