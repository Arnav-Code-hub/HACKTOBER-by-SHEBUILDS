#!/usr/bin/env bash
# One-time bootstrap. IDEMPOTENT — a developer whose environment breaks re-runs
# this instead of asking someone. Never overwrites an existing .env.
set -euo pipefail
cd "$(dirname "$0")/.."

bold() { printf '\033[1m%s\033[0m\n' "$1"; }
ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$1"; }
fail() { printf '  \033[31m✗\033[0m %s\n' "$1"; }

missing=0
need() {
  if command -v "$1" >/dev/null 2>&1; then ok "$1"; else fail "$1 — $2"; missing=1; fi
}

bold "Checking tools"
need docker  "https://docs.docker.com/get-docker/"
need node    "https://github.com/nvm-sh/nvm  (then: nvm use)"
need pnpm    "corepack enable"
need uv      "curl -LsSf https://astral.sh/uv/install.sh | sh"
need flutter "https://docs.flutter.dev/get-started/install"

if [ "$missing" -ne 0 ]; then
  echo
  fail "Install the tools above, then re-run: make setup"
  exit 1
fi

bold "Creating .env files (existing files are never overwritten)"
while IFS= read -r example; do
  env_file="${example%.example}"
  if [ -f "$env_file" ]; then
    warn "$env_file already exists — left alone"
  else
    cp "$example" "$env_file"
    ok "$env_file"
  fi
done < <(find . -name '.env.example' -not -path './.git/*' -not -path '*/node_modules/*' | sort)

bold "Installing dependencies"
pnpm install                              && ok "pnpm workspace"
(cd services/api && uv sync --all-groups) && ok "services/api"
(cd services/ai  && uv sync --all-groups) && ok "services/ai"
(cd apps/mobile  && flutter pub get)      && ok "apps/mobile"

bold "Generating design tokens"
pnpm --filter @janmaang/tokens build >/dev/null && ok "tokens"

bold "Starting the database"
docker compose up -d postgres redis
bash scripts/wait-for-postgres.sh

bold "Applying migrations and seeding"
docker compose run --rm api alembic upgrade head  && ok "migrations"
docker compose run --rm api python -m app.seeds   && ok "seed data"

bold "Installing git hooks"
if command -v pre-commit >/dev/null 2>&1; then
  pre-commit install && ok "pre-commit (secret scanning)"
else
  warn "pre-commit not installed — 'pipx install pre-commit' then 'pre-commit install'"
  warn "CI still scans for secrets, but you will find out later rather than sooner"
fi

echo
bold "Ready."
echo "  make dev      start everything"
echo "  make mobile   run the citizen app"
echo "  make doctor   if something looks wrong"
