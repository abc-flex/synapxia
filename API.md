# Installing and Running the API

Focused install guide for the **API service only** (`api/`). For the full stack
(DB + API + UI via Docker Compose) see [`docs/GETTING_STARTED.md`](docs/GETTING_STARTED.md) —
start there unless you specifically need to run the API outside Docker.

For what the API *does* (routes, modules, patterns), see [`api/CLAUDE.md`](api/CLAUDE.md).
For auth details, see [`api/AUTH.md`](api/AUTH.md).

---

## Option 1 — Via Docker Compose (recommended)

From the repo root:

```bash
make up      # or `make dev` to also print URLs + login credentials
```

This builds and starts `db`, `api`, `ui`, and `pgadmin` together. The API is published at
`http://localhost:8001` (Swagger at `/docs`, health at `/api/health`). See
[`docs/GETTING_STARTED.md`](docs/GETTING_STARTED.md) for prerequisites, environment
variables, and troubleshooting.

## Option 2 — API standalone (no Docker, for backend-only development)

Requires **Python ≥ 3.12** and [`uv`](https://docs.astral.sh/uv/) installed, plus a
reachable PostgreSQL instance (either the Compose `db` service or your own).

```bash
cd api
uv sync                 # installs/locks dependencies from pyproject.toml
uv run fastapi dev      # runs the app with live reload
```

Set connection env vars before running (see `api/.env.template` /
[`api/CLAUDE.md` § "Configuration & environment"](api/CLAUDE.md) for the full table):

```ini
DATABASE_URL=postgresql://synapxia:synapxia@localhost:5433/synapxia   # or DB_HOST/DB_USER/DB_PASSWORD/DB_SCHEMA/DB_PORT
SECRET_KEY=<32+ char random string>
APP_ENV=development
CORS_ORIGINS=http://localhost:4321
```

The database schema/seed data must already exist (run migrations via the `db` Compose
service at least once, or point `DATABASE_URL` at a DB where `db/sql/*.sql` has run).

## Verifying it's running

```bash
curl http://localhost:8001/api/health
```

Open `http://localhost:8001/docs` (Swagger UI) or `/redoc` to explore the live API.

## Deploying

Production/Vercel deployment is a separate process — see
[`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).
