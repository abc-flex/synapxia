# Getting Started — Running Synapxia for the First Time

This guide walks you through launching the full Synapxia stack from a clean checkout.

---

## 1. Prerequisites

### Install `make`

`make` is required to run the project commands.

**macOS**
```bash
# Comes with Xcode Command Line Tools:
xcode-select --install
# Or via Homebrew:
brew install make
```

**Linux (Debian / Ubuntu)**
```bash
sudo apt-get update && sudo apt-get install -y make
```

**Windows (native — no WSL required)**

Option A — Chocolatey (recommended):
```powershell
# 1. Install Chocolatey (run PowerShell as Administrator):
Set-ExecutionPolicy Bypass -Scope Process -Force; `
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; `
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# 2. Install make:
choco install make
```

Option B — Winget (built into Windows 11 / 10):
```powershell
winget install GnuWin32.Make
# Then add to PATH: C:\Program Files (x86)\GnuWin32\bin
```

Option C — Scoop:
```powershell
# Install Scoop first (if not already installed):
irm get.scoop.sh | iex

# Then install make:
scoop install make
```

Verify:
```bash
make --version
```

---

### Install Docker & Docker Compose

- **macOS / Windows:** Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Compose).
- **Linux:** Install [Docker Engine](https://docs.docker.com/engine/install/) + the [Compose plugin](https://docs.docker.com/compose/install/).

Verify:
```bash
make docker-info
```

---

## 2. Architecture / Services

The stack runs four services defined in [`docker-compose.yml`](../docker-compose.yml):

| Service | Tech | Port | Description |
|---------|------|------|-------------|
| `db` | PostgreSQL 18 | 5433 | Database (host port; container listens on 5432). Auto-runs SQL scripts in `db/sql/` on first startup. Override the host port with `DB_HOST_PORT`. |
| `pgadmin` | pgAdmin 4 | 8081 | Web admin UI for the database (host port; container listens on 80). Override the host port with `PGADMIN_HOST_PORT`. |
| `api` | FastAPI (Python, `uv`) | 8001 | Backend REST API with live reload. |
| `ui` | Astro (Bun) | 4321 | Frontend with live reload. |

**Startup order:** `db` → `api` (waits for DB healthy) → `ui` (waits for API).

---

## 3. Configure Environment Variables

Copy the template and verify the values:

```bash
cp .env.template .env
```

Default values (already set in the project):

```ini
DB_HOST=db
DB_SCHEMA=synapxia
DB_USER=synapxia
DB_PASSWORD=synapxia
DB_PORT=5432        # in-network port (container); API + PgAdmin use db:5432
DB_HOST_PORT=5433   # host-published port (localhost:5433) to avoid clashing with a local 5432
PGADMIN_EMAIL=admin@synapxia.com
PGADMIN_PASSWORD=synapxia
API_PATH=http://synapxia-api
```

The frontend also reads `ui/.env.development` — no changes needed there for local dev.

---

## 4. First Launch

For a clean first run (builds images and initializes the database):

```bash
make rebuild
```

The database **initializes itself** automatically by running every file in `db/sql/` via the Postgres Docker entrypoint.

> ⚠️ **Known issue:** `make rebuild` and `make up` call `./setup-database.sh` at the health-check step, which is not yet present in the repo. If the command errors at that step, the containers are still running. Use these instead to verify:
>
> ```bash
> make ps     # all containers should show "Up" / "healthy"
> make logs   # check for errors
> ```

---

## 5. Verify It's Running

```bash
make ps      # container status
make test    # API health, DB readiness, admin user check
```

Open in your browser:

| Service | URL |
|---------|-----|
| Frontend | http://localhost:4321 |
| API Docs (Swagger) | http://localhost:8001/docs |
| PgAdmin | http://localhost:8081 |

---

## 6. Login Credentials

| Context | User | Password |
|---------|------|----------|
| App login | `admin` | `Admin123!` |
| PgAdmin | `admin@synapxia.com` | `synapxia` |
| Database | `synapxia` | `synapxia` |

---

## 7. Day-to-Day Commands

```bash
make dev          # start stack + print URLs and credentials
make logs-api     # follow API logs
make logs-ui      # follow frontend logs
make shell        # open a psql shell in the DB
make down         # stop the stack (data is preserved)
make backup-db    # back up the DB to ./backups/
```

See [`MAKEFILE.md`](MAKEFILE.md) for the full command reference.

---

## 8. Troubleshooting

| Problem | Solution |
|---------|----------|
| A container won't start | `make logs` or `make logs-<service>` to see the error. |
| Database has stale/broken data | `make clean` then `make rebuild` to wipe the volume and re-run migrations. |
| Port already in use (4321 / 8001 / 8081 / 5433) | Stop the conflicting process, or change the host-side port mapping in `docker-compose.yml` (for the DB set `DB_HOST_PORT`, for PgAdmin set `PGADMIN_HOST_PORT`, in `.env` — the containers still listen on 5432 / 80). |
| Migrations didn't run | They only run on a **fresh** volume. Run `make clean` + `make rebuild` to force re-init. |
| `setup-database.sh: No such file` | Expected for now — see the note in step 4. |
