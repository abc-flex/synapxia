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

# Default target: print the categorized list of available commands.
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

# Start all containers in the background, wait ~30s for the DB to initialize,
# print the service URLs and run a health check.
# NOTE: relies on ./setup-database.sh (via `make health`), which is not in the repo yet.
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

# Stop and remove the running containers. Volumes (DB data) are preserved.
down:
	@echo "$(GREEN)Stopping containers...$(NC)"
	docker-compose -f $(COMPOSE_FILE) down
	@echo "$(GREEN)✓ Containers stopped$(NC)"

# Restart the whole stack: runs `down` then `up`.
restart: down up
	@echo "$(GREEN)✓ Containers restarted$(NC)"

# Clean rebuild: removes volumes (wipes DB data), rebuilds images, restarts,
# and re-runs all db/sql migrations on the fresh database.
rebuild:
	@echo "$(RED)Rebuilding from scratch (removing volumes)...$(NC)"
	docker-compose -f $(COMPOSE_FILE) down -v
	@echo "$(GREEN)Building containers...$(NC)"
	docker-compose -f $(COMPOSE_FILE) up -d --build
	@echo "$(GREEN)Waiting for database initialization...$(NC)"
	@sleep 30
	@make health

## Information Commands

# Show the status of all containers.
ps:
	@docker-compose -f $(COMPOSE_FILE) ps

# Follow (tail) the combined logs of all services. Ctrl+C to exit.
logs:
	docker-compose -f $(COMPOSE_FILE) logs -f

# Follow the logs of the API service only.
logs-api:
	docker-compose -f $(COMPOSE_FILE) logs -f api

# Follow the logs of the database service only.
logs-db:
	docker-compose -f $(COMPOSE_FILE) logs -f db

# Follow the logs of the frontend (UI) service only.
logs-ui:
	docker-compose -f $(COMPOSE_FILE) logs -f ui

# Follow the logs of the PgAdmin service only.
logs-pgadmin:
	docker-compose -f $(COMPOSE_FILE) logs -f pgadmin

# Run the health-check script.
# WARNING: ./setup-database.sh does not exist in the repo yet, so this will fail
# until the script is added (also affects `up`, `rebuild` and `quickstart`).
health:
	@echo "$(GREEN)Running health checks...$(NC)"
	@bash ./setup-database.sh

## Development Commands

# Open an interactive psql shell inside the db container.
shell:
	@echo "$(GREEN)Opening database shell...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec db psql -U synapxia -d synapxia

# Start the stack (via `up`) and print all access URLs and login credentials.
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

# Quick smoke tests: API health endpoint, DB readiness, and superuser existence.
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

# Remove all containers AND volumes. Destroys all database data.
clean:
	@echo "$(RED)Removing all containers and volumes...$(NC)"
	docker-compose -f $(COMPOSE_FILE) down -v
	@echo "$(GREEN)✓ Cleanup complete$(NC)"
	@echo ""
	@echo "To start fresh, run: $(BLUE)make rebuild$(NC)"

## Additional Utility Commands

# Show a one-shot snapshot of container resource usage (CPU, memory, etc.).
stats:
	@echo "$(GREEN)Docker resource usage:$(NC)"
	@docker stats --no-stream

# Open an interactive bash shell inside the API container.
exec-api:
	docker-compose -f $(COMPOSE_FILE) exec api bash

# Open an interactive bash shell inside the database container.
exec-db:
	docker-compose -f $(COMPOSE_FILE) exec db bash

# Open an interactive bash shell inside the frontend (UI) container.
exec-ui:
	docker-compose -f $(COMPOSE_FILE) exec ui bash

# Dump the database to a timestamped .sql file under ./backups/.
backup-db:
	@echo "$(GREEN)Backing up database...$(NC)"
	@mkdir -p ./backups
	@docker-compose -f $(COMPOSE_FILE) exec db pg_dump -U synapxia synapxia > ./backups/synapxia-$(shell date +%Y%m%d-%H%M%S).sql
	@echo "$(GREEN)✓ Backup created$(NC)"

# Restore the database from the most recent .sql backup in ./backups/.
restore-db:
	@echo "$(RED)Restoring database from latest backup...$(NC)"
	@LATEST=$$(ls -t ./backups/*.sql | head -1); \
	docker-compose -f $(COMPOSE_FILE) exec -T db psql -U synapxia synapxia < $$LATEST
	@echo "$(GREEN)✓ Restore complete$(NC)"

## Advanced Commands

# Check Python syntax in the API container with py_compile.
lint:
	@echo "$(BLUE)Checking Python syntax...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) exec api python -m py_compile app/**/*.py
	@echo "$(GREEN)✓ Python syntax OK$(NC)"

# Format the API's Python code with black inside the container.
format:
	@echo "$(BLUE)Formatting Python code...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) exec api black app/
	@echo "$(GREEN)✓ Code formatted$(NC)"

# List the SQL migration files in db/sql/ (run automatically on a fresh DB).
migrations:
	@echo "$(BLUE)Listing migrations...$(NC)"
	@ls -lah db/sql/

## Docker Info

# Print Docker / Docker Compose versions and a table of running containers.
docker-info:
	@echo "$(BLUE)Docker Information:$(NC)"
	@echo "Docker Version: $$(docker --version)"
	@echo "Compose Version: $$(docker-compose --version)"
	@echo ""
	@echo "$(BLUE)Running Containers:$(NC)"
	@docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Remove unused Docker resources system-wide (dangling images, stopped containers, etc.).
prune:
	@echo "$(RED)Removing unused Docker resources...$(NC)"
	docker system prune -f
	@echo "$(GREEN)✓ Pruned$(NC)"

## Help for specific commands

# Print help for the log-related commands.
logs-help:
	@echo "$(BLUE)Log Commands:$(NC)"
	@echo "  make logs          - All service logs"
	@echo "  make logs-api      - API logs only"
	@echo "  make logs-db       - Database logs only"
	@echo "  make logs-ui       - Frontend logs only"
	@echo "  make logs-pgadmin  - PgAdmin logs only"

# Print help for the shell-access commands.
exec-help:
	@echo "$(BLUE)Shell Access:$(NC)"
	@echo "  make shell         - Database shell (psql)"
	@echo "  make exec-api      - API container bash"
	@echo "  make exec-db       - Database container bash"
	@echo "  make exec-ui       - Frontend container bash"

# Print help for the backup/restore commands.
backup-help:
	@echo "$(BLUE)Backup Commands:$(NC)"
	@echo "  make backup-db     - Backup database to ./backups/"
	@echo "  make restore-db    - Restore from latest backup"
	@echo "  make migrations    - List database migrations"

## Quick Start

# Full fresh start: wipe everything (clean), start (up), then show access info (dev).
# NOTE: chains through `up`, so it also depends on the missing ./setup-database.sh.
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
