# JanMaang — one command surface across Flutter, TypeScript and Python.
#
# One Git repository, three build systems. This Makefile is the only interface
# a developer needs to learn; it delegates to pub, pnpm, uv and docker compose.

SHELL := /bin/bash
.DEFAULT_GOAL := help

COMPOSE := docker compose
API     := $(COMPOSE) exec -T api
MOBILE  := apps/mobile

# Every .env.example in the repo, and the .env it produces.
ENV_EXAMPLES := $(shell find . -name '.env.example' -not -path './.git/*' -not -path '*/node_modules/*' 2>/dev/null)

.PHONY: help setup dev up down restart logs ps doctor \
        web mobile mobile-ios shell-api shell-ai db \
        migrate migration seed seed-reference reset-db \
        test test-api test-ai test-web test-mobile test-e2e evals \
        lint format typecheck check contracts build clean

# ─── Help ────────────────────────────────────────────────────────────────────

help: ## Show this help
	@echo ""
	@echo "  JanMaang — make <target>"
	@echo ""
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ─── Setup ───────────────────────────────────────────────────────────────────

setup: ## One-time bootstrap. Idempotent — safe to re-run when things break.
	@bash scripts/setup.sh

doctor: ## Diagnose a broken environment (versions, ports, containers, DB)
	@bash scripts/doctor.sh

# ─── Running ─────────────────────────────────────────────────────────────────

dev: ## Start the whole stack (postgres, redis, api, worker, ai, web)
	$(COMPOSE) up -d
	@echo ""
	@echo "  web  → http://localhost:3000"
	@echo "  api  → http://localhost:8000/docs"
	@echo "  ai   → http://localhost:8001/docs"
	@echo ""
	@echo "  logs: make logs   |   mobile: make mobile   |   stop: make down"

up: dev

down: ## Stop the stack (data volumes survive)
	$(COMPOSE) down

restart: ## Restart one service — make restart s=api
	$(COMPOSE) restart $(s)

logs: ## Tail logs. One service: make logs s=api
	$(COMPOSE) logs -f --tail=100 $(s)

ps: ## Show container status
	$(COMPOSE) ps

web: ## Run web outside Docker for faster hot reload
	pnpm --filter @janmaang/web dev

mobile: ## Run the Flutter citizen app against the local API
	cd $(MOBILE) && flutter run

mobile-ios: ## Run the citizen app on an iOS simulator
	cd $(MOBILE) && flutter run -d iphone

# ─── Database ────────────────────────────────────────────────────────────────

migrate: ## Apply all pending migrations
	$(API) alembic upgrade head

migration: ## Create a migration — make migration name="add priority score"
	@test -n "$(name)" || (echo "usage: make migration name=\"describe the change\"" && exit 1)
	$(API) alembic revision --autogenerate -m "$(name)"

seed: ## Load reference + demo data
	$(API) python -m app.seeds

seed-reference: ## Load reference data only (production-safe subset)
	$(API) python -m app.seeds --reference

reset-db: ## Drop, recreate, migrate and reseed. Destroys local data.
	$(COMPOSE) down -v postgres
	$(COMPOSE) up -d postgres
	@bash scripts/wait-for-postgres.sh
	$(MAKE) migrate seed

db: ## Open a psql shell
	$(COMPOSE) exec postgres psql -U janmaang -d janmaang

shell-api: ## Shell into the API container
	$(COMPOSE) exec api bash

shell-ai: ## Shell into the AI container
	$(COMPOSE) exec ai bash

# ─── Contracts ───────────────────────────────────────────────────────────────

contracts: ## Regenerate OpenAPI + the TypeScript client + Dart models
	@bash scripts/gen-contracts.sh

# ─── Testing ─────────────────────────────────────────────────────────────────

test: test-api test-ai test-web test-mobile ## Run every fast suite

test-api: ## API unit + integration + contract tests
	$(API) pytest

test-ai: ## AI unit tests (LLM mocked — no API calls, no cost)
	$(COMPOSE) exec -T ai pytest

test-web: ## Web unit and component tests
	pnpm --filter @janmaang/web test

test-mobile: ## Flutter unit and widget tests
	cd $(MOBILE) && flutter test

test-e2e: ## Cross-service journeys against a running stack
	pnpm --filter @janmaang/e2e e2e

evals: ## AI quality evals against golden datasets. Makes real LLM calls — costs money.
	$(COMPOSE) exec -T ai python -m evals.report

# ─── Quality ─────────────────────────────────────────────────────────────────

check: lint typecheck test ## Everything CI runs, in the same order

lint: ## Lint every ecosystem
	pnpm -r lint
	cd services/api && uv run ruff check . && uv run lint-imports
	cd services/ai  && uv run ruff check .
	cd $(MOBILE) && flutter analyze

format: ## Auto-format every ecosystem
	pnpm -r format
	cd services/api && uv run ruff format .
	cd services/ai  && uv run ruff format .
	cd $(MOBILE) && dart format lib test

typecheck: ## Static type checks
	pnpm -r typecheck
	cd services/api && uv run mypy app
	cd services/ai  && uv run mypy app

# ─── Build / clean ───────────────────────────────────────────────────────────

build: ## Build all production images
	$(COMPOSE) -f docker-compose.yml -f docker-compose.prod.yml build

clean: ## Remove build artifacts and caches (keeps .env files and volumes)
	rm -rf apps/web/.next apps/web/node_modules node_modules packages/*/node_modules
	rm -rf $(MOBILE)/build $(MOBILE)/.dart_tool
	find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
	find . -name .pytest_cache -o -name .ruff_cache -o -name .mypy_cache \
	  -type d -prune -exec rm -rf {} + 2>/dev/null || true
