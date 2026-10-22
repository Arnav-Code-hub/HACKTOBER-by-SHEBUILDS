# Setup

Target: clone to a working system in **under 10 minutes, two commands**.

```bash
git clone https://github.com/<org>/janmaang.git
cd janmaang
make setup
make dev
```

`make setup` is **idempotent**. When your environment breaks, re-run it rather
than asking someone. It never overwrites an existing `.env`.

## Prerequisites

| Tool | Why | Install |
|---|---|---|
| Docker | Postgres, Redis, api, ai, web | <https://docs.docker.com/get-docker/> |
| Node 20+ | web and packages | `nvm use` (reads `.nvmrc`) |
| pnpm 9 | TypeScript workspace | `corepack enable` |
| uv | Python services | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Flutter 3.24+ | citizen app | <https://docs.flutter.dev/get-started/install> |
| pre-commit | secret scanning before commit | `pipx install pre-commit` |

`make doctor` checks all of these and tells you what is missing.

> **Already running Postgres or Redis locally?** They will collide with the
> containers on 5432/6379. Either stop them, or change `POSTGRES_PORT` /
> `REDIS_PORT` in the root `.env`.

## What `make setup` does

1. Verifies tool versions
2. Copies every `.env.example` → `.env` (existing files untouched)
3. `pnpm install`, `uv sync` ×2, `flutter pub get`
4. Generates design tokens
5. Starts Postgres and Redis, applies migrations, loads seed data
6. Installs the pre-commit hooks

## Daily commands

```bash
make dev        # start everything
make mobile     # run the citizen app
make web        # web outside Docker, faster hot reload
make logs       # tail everything;  make logs s=api  for one
make check      # exactly what CI runs, in the same order
make doctor     # when something looks wrong
make help       # every target
```

Once running: web on <http://localhost:3000>, API docs on
<http://localhost:8000/docs>, AI docs on <http://localhost:8001/docs>.

## Real API keys

`make setup` gives you a working local system with **no** real keys — mocks and
seed data cover the demo path. You only need real credentials for AI features:
put `LLM_API_KEY` in `services/ai/.env`. Ask the team lead; never paste a key
into chat, a commit, or an issue.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `port already allocated` | native Postgres/Redis running | change ports in root `.env`, or stop them |
| API container restarts | migrations failed | `make logs s=api`, then `make reset-db` |
| Web can't reach the API | missing `.env` | `make setup` |
| Flutter build fails after a pull | stale generated files | `cd apps/mobile && flutter clean && flutter pub get` |
| Types wrong after an API change | stale contracts | `make contracts` |
