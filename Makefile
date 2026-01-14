.PHONY: help up down restart logs verify clean

# Smart OS Detection
OS_NAME := $(shell uname -s)

# Default Settings (Server/Linux)
COMPOSE_BASE := -f deploy/docker-compose.yml
PROFILE := real
ENV_FILE := .env.dev
COMPOSE_ARGS := $(COMPOSE_BASE) --env-file $(ENV_FILE)

# Mac (Darwin) Override
ifeq ($(OS_NAME),Darwin)
	PROFILE := local
	ENV_FILE := .env.local
	COMPOSE_ARGS := $(COMPOSE_BASE) -f deploy/docker-compose.local.yml
endif

.PHONY: help up up-dev up-prod down logs ps clean test lint

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## Start environment (Smart Detect: Mac=Local, Linux=Real)
	@echo "🍎/🐧 Detected OS: $(OS_NAME)"
	@echo "🚀 Starting Profile: $(PROFILE) using $(ENV_FILE)"
	docker compose $(COMPOSE_ARGS) --profile $(PROFILE) up -d

build-api: ## Rebuild API Server
	docker compose -f deploy/docker-compose.yml build api-server

up-dev: ## Force start development environment (Linux mode)
	@./scripts/preflight_check.sh dev
	docker compose --env-file .env.dev -f deploy/docker-compose.yml --profile real up -d

up-prod: ## Start production environment (Danger Zone)
	@./scripts/preflight_check.sh production
	docker compose --env-file .env.prod -f deploy/docker-compose.yml --profile real up -d
	@echo "Cleaning up unused Docker resources for Stability..."
	docker system prune -af

test: ## Run unit tests in isolated test environment (Resource Limited)
	docker run --rm --cpus="0.5" --memory="512m" -v $$(pwd):/app -w /app --env-file .env.test deploy-api-server /bin/sh -c "pip install pytest pytest-asyncio httpx<0.28 && export PYTHONPATH=. && python3 -m pytest tests/"

down: ## Stop all services
	docker compose -f deploy/docker-compose.yml down

restart: down up ## Restart all services

logs: ## View logs from all services
	docker compose -f deploy/docker-compose.yml logs -f

verify: ## Verify data collection (run after 2-3 minutes)
	@echo "=== Checking Tick Data ==="
	@docker exec tick-archiver python -c "import duckdb; conn = duckdb.connect('data/market_data.duckdb'); print('Ticks:', conn.execute('SELECT count(*) FROM ticks').fetchone()[0])" || echo "No ticks yet"
	@echo "\n=== Checking News Data ==="
	@docker exec news-collector python -c "import duckdb; conn = duckdb.connect('data/market_data.duckdb'); print('News:', conn.execute('SELECT count(*) FROM news').fetchone()[0])" || echo "No news yet"

# --- Data Sync (Hybrid Workflow) ---
PROD_HOST ?= stock-monitor-prod  # Can be overridden: make sync-db-prod PROD_HOST=myserver

.PHONY: sync-db-prod
sync-db-prod: ## [Local] Fetch Snapshot from Production (Requires Tailscale/SSH)
	@echo "🔄 Syncing TimescaleDB from Production ($(PROD_HOST))..."
	@# 1. Dump Remote(Zip) -> Stream -> Unzip -> Restore Local
	ssh $(PROD_HOST) "docker exec stock-db pg_dump -U postgres stockval --clean --if-exists | gzip" | \
		gunzip | docker compose $(COMPOSE_ARGS) exec -T stock-db psql -U postgres stock_dev
	@echo "✅ TimescaleDB Synced!"
	@echo "🔄 Syncing DuckDB from Production..."
	@# 2. Rsync DuckDB Files
	rsync -avz --progress $(PROD_HOST):/app/data/market_data.duckdb ./data/dev_market_data.duckdb
	@echo "✅ DuckDB Synced!"
	@echo "🎉 Development environment is now running with REAL Data."

audit: ## Run governance checks (Branch, Commit, Docstrings)
	@echo "🛡️ Governance Check..."
	@python3 scripts/governance.py

clean: ## Remove all containers, volumes, and data
	docker compose -f deploy/docker-compose.yml down -v
	rm -rf data/*.duckdb
## debug-redis: Watch Redis traffic in real-time
debug-redis:
	docker exec stock-redis redis-cli MONITOR

## debug-pubsub: Check pub/sub subscribers count
debug-pubsub:
	docker exec stock-redis redis-cli PUBSUB NUMSUB "tick.*"

## debug-channels: List all active channels
debug-channels:
	docker exec stock-redis redis-cli PUBSUB CHANNELS

# --- Backtest Environment Commands ---
.PHONY: backtest-up backtest-down backtest-logs backtest-clean backtest-shell

backtest-up: ## Start backtest environment (Isolated)
	@echo "🧪 Starting Backtest Environment..."
	@echo "   - Redis: 6380"
	@echo "   - TimescaleDB: 5433"
	@echo "   - API: 8001"
	docker compose -f deploy/docker-compose.backtest.yml --env-file .env.backtest up -d
	@echo "✅ Backtest environment is running!"

backtest-down: ## Stop backtest environment
	@echo "🛑 Stopping Backtest Environment..."
	docker compose -f deploy/docker-compose.backtest.yml down

backtest-logs: ## View backtest logs
	docker compose -f deploy/docker-compose.backtest.yml logs -f

backtest-clean: ## Clean backtest data and volumes
	@echo "⚠️  This will remove ALL backtest data!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker compose -f deploy/docker-compose.backtest.yml down -v; \
		echo "✅ All backtest data has been removed"; \
	else \
		echo "❌ Cancelled"; \
	fi

backtest-shell: ## Enter backtest engine container
	docker exec -it backtest-engine /bin/sh

backtest-verify: ## Verify backtest database
	@echo "=== Checking Backtest DB ==="
	@docker exec backtest-timescale psql -U postgres -d backtest_db -c "SELECT COUNT(*) as tick_count FROM ticks;" || echo "Table not created yet"
