.PHONY: help up down ps logs shell dev clean rebuild restart health test

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
RED := \033[0;31m
NC := \033[0m # No Color

# Docker Compose file
COMPOSE_FILE = docker-compose.yml

help:
	@echo "$(BLUE)=======================================$(NC)"
	@echo "$(BLUE)Synapxia Development Commands$(NC)"
	@echo "$(BLUE)=======================================$(NC)"
	@echo ""
	@echo "$(GREEN)Basic Commands:$(NC)"
	@echo "  make up          - Start all containers"
	@echo "  make down        - Stop all containers"
	@echo "  make restart     - Restart all containers"
	@echo "  make rebuild     - Clean rebuild (remove volumes)"
	@echo ""
	@echo "$(GREEN)Information:$(NC)"
	@echo "  make ps          - Show running containers"
	@echo "  make logs        - View logs (all services)"
	@echo "  make health      - Run health check script"
	@echo ""
	@echo "$(GREEN)Development:$(NC)"
	@echo "  make shell       - Open database shell (psql)"
	@echo "  make dev         - Start all services in development"
	@echo "  make test        - Run tests"
	@echo ""
	@echo "$(GREEN)Cleanup:$(NC)"
	@echo "  make clean       - Remove all containers & volumes"
	@echo ""
	@echo "$(BLUE)=======================================$(NC)"
	@echo ""

## Basic Commands

up:
	@echo "$(GREEN)Starting containers...$(NC)"
	docker-compose -f $(COMPOSE_FILE) up -d
	@echo "$(GREEN)✓ Containers started$(NC)"
	@echo ""
	@echo "Waiting for database initialization (20-30 seconds)..."
	@sleep 30
	@echo ""
	@echo "$(GREEN)Services are starting:$(NC)"
	@echo "  Frontend:    http://localhost:4321"
	@echo "  API Docs:    http://localhost:8000/docs"
	@echo "  PgAdmin:     http://localhost:8080"
	@echo ""
	@make health

down:
	@echo "$(GREEN)Stopping containers...$(NC)"
	docker-compose -f $(COMPOSE_FILE) down
	@echo "$(GREEN)✓ Containers stopped$(NC)"

restart: down up
	@echo "$(GREEN)✓ Containers restarted$(NC)"

rebuild:
	@echo "$(RED)Rebuilding from scratch (removing volumes)...$(NC)"
	docker-compose -f $(COMPOSE_FILE) down -v
	@echo "$(GREEN)Building containers...$(NC)"
	docker-compose -f $(COMPOSE_FILE) up -d --build
	@echo "$(GREEN)Waiting for database initialization...$(NC)"
	@sleep 30
	@make health

## Information Commands

ps:
	@docker-compose -f $(COMPOSE_FILE) ps

logs:
	docker-compose -f $(COMPOSE_FILE) logs -f

logs-api:
	docker-compose -f $(COMPOSE_FILE) logs -f api

logs-db:
	docker-compose -f $(COMPOSE_FILE) logs -f db

logs-ui:
	docker-compose -f $(COMPOSE_FILE) logs -f ui

logs-pgadmin:
	docker-compose -f $(COMPOSE_FILE) logs -f pgadmin

health:
	@echo "$(GREEN)Running health checks...$(NC)"
	@bash ./setup-database.sh

## Development Commands

shell:
	@echo "$(GREEN)Opening database shell...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec db psql -U synapxia -d synapxia

dev: up
	@echo ""
	@echo "$(GREEN)✓ Development environment ready!$(NC)"
	@echo ""
	@echo "$(BLUE)Quick Access:$(NC)"
	@echo "  Frontend:        http://localhost:4321"
	@echo "  API Swagger:     http://localhost:8000/docs"
	@echo "  PgAdmin:         http://localhost:8080"
	@echo ""
	@echo "$(BLUE)Login Credentials:$(NC)"
	@echo "  Username:        admin"
	@echo "  Password:        Admin123!"
	@echo ""
	@echo "$(BLUE)PgAdmin:$(NC)"
	@echo "  Email:           admin@synapxia.com"
	@echo "  Password:        synapxia"
	@echo ""
	@echo "$(BLUE)Database:$(NC)"
	@echo "  Host:            db"
	@echo "  Port:            5432"
	@echo "  User:            synapxia"
	@echo "  Password:        synapxia"
	@echo ""

## Test Commands

test:
	@echo "$(GREEN)Running application tests...$(NC)"
	@echo ""
	@echo "$(BLUE)API Health Check:$(NC)"
	@curl -s http://localhost:8000/api/health || echo "API not responding"
	@echo ""
	@echo "$(BLUE)Database Connection:$(NC)"
	@docker-compose -f $(COMPOSE_FILE) exec db pg_isready -U synapxia && echo "$(GREEN)✓ Database healthy$(NC)" || echo "$(RED)✗ Database unavailable$(NC)"
	@echo ""
	@echo "$(BLUE)Admin User Check:$(NC)"
	@docker-compose -f $(COMPOSE_FILE) exec db psql -U synapxia -d synapxia -c "SELECT username, email FROM users WHERE is_superuser = true LIMIT 1;" || echo "Users table not found"
	@echo ""
	@echo "$(GREEN)✓ Tests complete$(NC)"

## Cleanup Commands

clean:
	@echo "$(RED)Removing all containers and volumes...$(NC)"
	docker-compose -f $(COMPOSE_FILE) down -v
	@echo "$(GREEN)✓ Cleanup complete$(NC)"
	@echo ""
	@echo "To start fresh, run: $(BLUE)make rebuild$(NC)"

## Additional Utility Commands

stats:
	@echo "$(GREEN)Docker resource usage:$(NC)"
	@docker stats --no-stream

exec-api:
	docker-compose -f $(COMPOSE_FILE) exec api bash

exec-db:
	docker-compose -f $(COMPOSE_FILE) exec db bash

exec-ui:
	docker-compose -f $(COMPOSE_FILE) exec ui bash

backup-db:
	@echo "$(GREEN)Backing up database...$(NC)"
	@mkdir -p ./backups
	@docker-compose -f $(COMPOSE_FILE) exec db pg_dump -U synapxia synapxia > ./backups/synapxia-$(shell date +%Y%m%d-%H%M%S).sql
	@echo "$(GREEN)✓ Backup created$(NC)"

restore-db:
	@echo "$(RED)Restoring database from latest backup...$(NC)"
	@LATEST=$$(ls -t ./backups/*.sql | head -1); \
	docker-compose -f $(COMPOSE_FILE) exec -T db psql -U synapxia synapxia < $$LATEST
	@echo "$(GREEN)✓ Restore complete$(NC)"

## Advanced Commands

lint:
	@echo "$(BLUE)Checking Python syntax...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) exec api python -m py_compile app/**/*.py
	@echo "$(GREEN)✓ Python syntax OK$(NC)"

format:
	@echo "$(BLUE)Formatting Python code...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) exec api black app/
	@echo "$(GREEN)✓ Code formatted$(NC)"

migrations:
	@echo "$(BLUE)Listing migrations...$(NC)"
	@ls -lah db/sql/

## Docker Info

docker-info:
	@echo "$(BLUE)Docker Information:$(NC)"
	@echo "Docker Version: $$(docker --version)"
	@echo "Compose Version: $$(docker-compose --version)"
	@echo ""
	@echo "$(BLUE)Running Containers:$(NC)"
	@docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

prune:
	@echo "$(RED)Removing unused Docker resources...$(NC)"
	docker system prune -f
	@echo "$(GREEN)✓ Pruned$(NC)"

## Help for specific commands

logs-help:
	@echo "$(BLUE)Log Commands:$(NC)"
	@echo "  make logs          - All service logs"
	@echo "  make logs-api      - API logs only"
	@echo "  make logs-db       - Database logs only"
	@echo "  make logs-ui       - Frontend logs only"
	@echo "  make logs-pgadmin  - PgAdmin logs only"

exec-help:
	@echo "$(BLUE)Shell Access:$(NC)"
	@echo "  make shell         - Database shell (psql)"
	@echo "  make exec-api      - API container bash"
	@echo "  make exec-db       - Database container bash"
	@echo "  make exec-ui       - Frontend container bash"

backup-help:
	@echo "$(BLUE)Backup Commands:$(NC)"
	@echo "  make backup-db     - Backup database to ./backups/"
	@echo "  make restore-db    - Restore from latest backup"
	@echo "  make migrations    - List database migrations"

## Quick Start

quickstart: clean up dev
	@echo ""
	@echo "$(GREEN)✓ Synapxia is ready to use!$(NC)"
	@echo ""
	@echo "$(BLUE)Next steps:$(NC)"
	@echo "1. Open Frontend:     http://localhost:4321"
	@echo "2. Login with:        admin / Admin123!"
	@echo "3. API Docs:          http://localhost:8000/docs"
	@echo "4. Database Admin:    http://localhost:8080"
	@echo ""
	@echo "Run $(BLUE)make help$(NC) for all commands"
