.PHONY: help up down ps logs shell dev clean rebuild restart reset reset-db health test lint lint-ui fmt fmt-check pytest purge nuke migrate-create migrate-upgrade migrate-downgrade

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
	@echo "  make reset-db    - Reset DB only (wipe + re-run DDL/seeds)"
	@echo "  make reset       - Full reset: reset-db + rebuild"
	@echo ""
	@echo "$(GREEN)Information:$(NC)"
	@echo "  make ps          - Show running containers"
	@echo "  make logs        - View logs (all services)"
	@echo "  make health      - Run health check script"
	@echo ""
	@echo "$(GREEN)Development:$(NC)"
	@echo "  make shell       - Open database shell (psql)"
	@echo "  make dev         - Start all services in development"
	@echo "  make test        - Smoke tests (health + DB + admin user)"
	@echo ""
	@echo "$(GREEN)Code Quality:$(NC)"
	@echo "  make lint        - Lint API: ruff + mypy"
	@echo "  make lint-ui     - Lint UI: eslint"
	@echo "  make fmt         - Format API: black + isort (auto-fix)"
	@echo "  make fmt-check   - Format check (exit 1 if drift)"
	@echo "  make pytest      - Run API unit tests"
	@echo ""
	@echo "$(GREEN)Database Migrations (Phase 2 - Alembic):$(NC)"
	@echo "  make migrate-create MSG='...' - Create new migration"
	@echo "  make migrate-upgrade          - Apply pending migrations"
	@echo "  make migrate-downgrade TARGET=xxx - Rollback to revision"
	@echo ""
	@echo "$(GREEN)Cleanup:$(NC)"
	@echo "  make clean       - Remove all containers & volumes"
	@echo "  make purge       - Remove all containers, volumes & images"
	@echo "  make nuke        - Purge everything then rebuild from scratch"
	@echo ""
	@echo "$(BLUE)=======================================$(NC)"
	@echo ""

## Basic Commands

# Start all containers in the background, wait ~30s for the DB to initialize,
# print the service URLs and run a health check.
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

# Reset the DB only — wipes the postgres volume + container and re-runs every
# DDL/insert file in db/sql/. Other services (api, ui, pgadmin) stay untouched.
# Use when seeds change and you don't want a full rebuild.
reset-db:
	@echo "$(RED)Resetting database...$(NC)"
	@echo "Stopping database container..."
	docker-compose -f $(COMPOSE_FILE) stop db
	@echo "Removing database container and volumes..."
	docker-compose -f $(COMPOSE_FILE) rm -f -v db
	docker volume rm synapxia_synapxia-db-pg18 2>/dev/null || true
	@echo "Recreating database container..."
	docker-compose -f $(COMPOSE_FILE) up -d db
	@echo "Waiting for database initialization (DDL + seeds)..."
	@sleep 15
	@echo "$(GREEN)✓ Database reset complete — DDL + seeds reinitialized$(NC)"

# Full reset: nuke the DB, then rebuild every container from scratch.
reset: reset-db rebuild
	@echo "$(GREEN)✓ Full reset complete$(NC)"

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

# Inline health checks: API /health endpoint, DB pg_isready, admin user existence.
# Replaces the legacy ./setup-database.sh shell script (no longer required).
health:
	@echo "$(GREEN)Running health checks...$(NC)"
	@echo ""
	@echo "$(BLUE)API Health Check:$(NC)"
	@curl -s http://localhost:8000/api/health || echo "$(RED)✗ API not responding$(NC)"
	@echo ""
	@echo "$(BLUE)Database Connection:$(NC)"
	@docker-compose -f $(COMPOSE_FILE) exec -T db pg_isready -U synapxia && echo "$(GREEN)✓ Database healthy$(NC)" || echo "$(RED)✗ Database unavailable$(NC)"
	@echo ""
	@echo "$(BLUE)Admin User Check:$(NC)"
	@docker-compose -f $(COMPOSE_FILE) exec -T db psql -U synapxia -d synapxia -c "SELECT username, email FROM users WHERE is_superuser = true LIMIT 1;" 2>/dev/null || echo "$(RED)✗ Admin user not found$(NC)"
	@echo ""
	@echo "$(GREEN)✓ Health checks complete$(NC)"

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

# Quick smoke tests: delegates to `make health` (same checks).
test: health
	@echo "$(GREEN)✓ Tests complete$(NC)"

## Cleanup Commands

# Remove all containers AND volumes. Destroys all database data.
clean:
	@echo "$(RED)Removing all containers and volumes...$(NC)"
	docker-compose -f $(COMPOSE_FILE) down -v
	@echo "$(GREEN)✓ Cleanup complete$(NC)"
	@echo ""
	@echo "To start fresh, run: $(BLUE)make rebuild$(NC)"

# Remove all containers, volumes, AND built images.
# Use when Dockerfile or dependencies changed and you want a guaranteed clean slate.
purge:
	@echo "$(RED)Removing all containers, volumes and images...$(NC)"
	docker-compose -f $(COMPOSE_FILE) down -v --rmi all
	@echo "$(GREEN)✓ Purge complete$(NC)"
	@echo ""
	@echo "To rebuild from scratch, run: $(BLUE)make nuke$(NC)"

# Full nuclear reset: purge everything (containers + volumes + images) then rebuild
# and restart. Guarantees no stale layers survive — use after Dockerfile changes.
nuke: purge
	@echo "$(GREEN)Building images from scratch...$(NC)"
	docker-compose -f $(COMPOSE_FILE) up -d --build
	@echo "$(GREEN)Waiting for database initialization...$(NC)"
	@sleep 30
	@make health
	@echo "$(GREEN)✓ Nuke complete — clean environment running$(NC)"

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

# Run every db/sql/*.sql migration against a remote Postgres (Neon/Vercel).
# Uses the local synapxia-db container's psql (v18) so no host install needed.
#
# Usage:
#   NEON_URL='postgres://USER:PASS@HOST/DB?sslmode=require' make neon-migrate
#
# Prefer the *NON_POOLING* URL from Vercel → Storage → Neon (DDL doesn't
# play nicely with PgBouncer's transaction-mode pooler).
#
# Idempotency: the script aborts on the first error. If you've already
# applied DDL but want to re-run seeds, run individual files with:
#   docker exec -i synapxia-db psql "$$NEON_URL" -f - < db/sql/12-admin-insert.sql
neon-migrate:
	@if [ -z "$$NEON_URL" ]; then \
		echo "$(RED)NEON_URL must be set. Example:$(NC)"; \
		echo "  NEON_URL='postgresql://user:pass@host/db?sslmode=require' make neon-migrate"; \
		exit 1; \
	fi
	@if ! docker ps --format '{{.Names}}' | grep -q '^synapxia-db$$'; then \
		echo "$(RED)synapxia-db container is not running. Start it with: make up$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)🚀 Running migrations against:$(NC) $${NEON_URL%%@*}@…"
	@for f in 11-admin-ddl.sql 12-admin-insert.sql 21-taxo-ddl.sql 22-taxo-insert.sql 31-collab-ddl.sql 32-collab-insert.sql 41-lib-ddl.sql 42-lib-insert.sql 51-inits-ddl.sql 52-inits-insert.sql 61-ana-ddl.sql; do \
		echo "  ▶ $$f"; \
		docker exec -i synapxia-db psql "$$NEON_URL" -v ON_ERROR_STOP=1 -q -f - < db/sql/$$f || exit 1; \
	done
	@echo "$(GREEN)✓ Neon migrations complete$(NC)"

# Restore the database from the most recent .sql backup in ./backups/.
restore-db:
	@echo "$(RED)Restoring database from latest backup...$(NC)"
	@LATEST=$$(ls -t ./backups/*.sql | head -1); \
	docker-compose -f $(COMPOSE_FILE) exec -T db psql -U synapxia synapxia < $$LATEST
	@echo "$(GREEN)✓ Restore complete$(NC)"

## Advanced Commands

# Lint API: ruff (style/errors) + mypy (types). Exits 1 on violations.
lint:
	@echo "$(BLUE)Linting API (ruff + mypy)...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) exec api ruff check app/
	@docker-compose -f $(COMPOSE_FILE) exec api mypy app/ --ignore-missing-imports
	@echo "$(GREEN)✓ API lint OK$(NC)"

# Lint UI: eslint for Astro + TypeScript files.
lint-ui:
	@echo "$(BLUE)Linting UI (eslint)...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) exec ui bun run lint
	@echo "$(GREEN)✓ UI lint OK$(NC)"

# Format API code with black + isort (auto-fix in place).
fmt:
	@echo "$(BLUE)Formatting API (black + isort)...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) exec api black app/
	@docker-compose -f $(COMPOSE_FILE) exec api isort app/
	@echo "$(GREEN)✓ Formatted$(NC)"

# Check API format without modifying files. Exits 1 if drift detected.
fmt-check:
	@echo "$(BLUE)Checking API format (black + isort)...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) exec api black --check app/
	@docker-compose -f $(COMPOSE_FILE) exec api isort --check app/
	@echo "$(GREEN)✓ Format OK$(NC)"

# Run API unit tests via pytest. Targets api/tests/ with SQLite in-memory fixtures.
pytest:
	@echo "$(BLUE)Running API unit tests...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) exec api pytest tests/ -v
	@echo "$(GREEN)✓ Tests passed$(NC)"

# Create a new Alembic migration (Phase 2).
migrate-create:
	@if [ -z "$(MSG)" ]; then \
		echo "$(RED)Error: MSG not set. Usage: make migrate-create MSG='Your migration message'$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Creating Alembic migration: $(MSG)...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) exec api alembic revision --autogenerate -m "$(MSG)"
	@echo "$(GREEN)✓ Migration created in api/migrations/versions/$(NC)"

# Apply pending Alembic migrations to the database.
migrate-upgrade:
	@echo "$(BLUE)Applying migrations...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) exec api alembic upgrade head
	@echo "$(GREEN)✓ Migrations applied$(NC)"

# Rollback to a specific migration revision (e.g., make migrate-downgrade TARGET=0001).
migrate-downgrade:
	@if [ -z "$(TARGET)" ]; then \
		echo "$(RED)Error: TARGET not set. Usage: make migrate-downgrade TARGET=revision_id$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Rolling back to $(TARGET)...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) exec api alembic downgrade $(TARGET)
	@echo "$(GREEN)✓ Rolled back to $(TARGET)$(NC)"

# Legacy alias — kept for compatibility.
format: fmt

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
