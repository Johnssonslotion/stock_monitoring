.PHONY: help up down clean

help:
	@echo "Stock Monitoring Project Management"
	@echo "Usage:"
	@echo "  make up    : Start services"
	@echo "  make down  : Stop services"
	@echo "  make clean : Remove artifacts"

up:
	docker-compose -f deploy/docker-compose.yml up -d

down:
	docker-compose -f deploy/docker-compose.yml down

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
