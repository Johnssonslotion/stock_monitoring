.PHONY: help up down restart logs verify clean

help: ## Display this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

up: ## Start all services
	docker compose -f deploy/docker-compose.yml up -d

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
