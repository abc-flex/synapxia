# CLAUDE.md — Database

Companion to [`AGENTS.md`](AGENTS.md) (rules) and the root [`../AGENTS.md`](../AGENTS.md)
(Constitution + repo-wide conventions). This file is the **actionable map** of the
database layer: every SQL file, every module band, every seed dataset an AI agent
needs to extend or debug the schema.

> **Rule of thumb:** rules live in [`AGENTS.md`](AGENTS.md). Concrete file inventories,
> table shapes, and seed data live here.

---

## Stack

| Item | Value |
|------|-------|
| Engine | PostgreSQL 18 |
| Container port | 5432 (published on host `5433` by default — override via `DB_HOST_PORT`) |
| Migration tool | Ordered raw SQL files (no Alembic/Flyway/Liquibase) |
| Initialization | Docker entrypoint auto-runs files in `/docker-entrypoint-initdb.d/` lexically |
| Persistence | `synapxia-db-volume` (named Docker volume) |
| Admin UI | pgAdmin on host port `8081` (container 80; override via `PGADMIN_HOST_PORT`) |
| Production target | Neon (serverless Postgres on AWS) via `neon-migrate.sh` |

Default credentials (dev): `synapxia` / `synapxia` (user / password / database name).
Seed admin user: `admin` / `Admin123!`.

---

## Directory map (`db/`)

```
db/
├── sql/
│   ├── 11-admin-ddl.sql        # Admin schema:    modules, units, lists, list_items, profiles, users, options, privileges
│   ├── 12-admin-insert.sql     # Admin seeds:     admin user, 3 profiles, 7 modules, 32 options, ~70 privileges, business units
│   ├── 21-taxo-ddl.sql         # Taxonomy:        categories (hierarchical), features, specifications
│   ├── 22-taxo-insert.sql      # Taxonomy seeds:  14-node category tree, 18 features, default specifications
│   ├── 31-collab-ddl.sql       # Collab schema:   teams, roles, assignments, projects, dimensions, metrics
│   ├── 32-collab-insert.sql    # Collab seeds:    5 teams, 5 roles, 60 test users, 60 assignments, dimension scales
│   ├── 41-lib-ddl.sql          # Library:         assets, characterizations, favorites, actions, asset_relations, permissions
│   ├── 42-lib-insert.sql       # Library seeds:   3 example assets, characterizations, action types, relation types
│   ├── 51-inits-ddl.sql        # Initiatives:     initiatives, criterias, diagnostics, collaborations, permissions
│   ├── 52-inits-insert.sql     # Inits seeds:     6 evaluation criteria with 1-3 scales (en/es)
│   ├── 61-ana-ddl.sql          # Analytics:       dashboards, parameters, executions, permissions
│   └── manual/                 # NOT auto-run on init — Postgres entrypoint doesn't recurse
│       ├── delete.sql          # Manual cleanup:  DELETE all rows, schema preserved
│       └── drop.sql            # Manual teardown: DROP every table
├── neon-migrate.sh             # psql-driven migration script for Neon (prod deploys)
├── AGENTS.md                   # Rules (see root AGENTS.md too)
└── CLAUDE.md                   # this file
```

---

## File numbering convention

```
{NN}-{module}-{ddl|insert}.sql
```

- `NN` — two-digit ordinal. **DDL goes at `NN`; the matching seed at `NN+1`.** The
  Postgres entrypoint runs files in lexical (alphanumeric) order, so this guarantees
  schema-before-data within a module and module-before-module across the stack.
- `module` — short kebab name matching the API domain (`admin`, `taxo`, `collab`,
  `lib`, `inits`, `ana`).
- `ddl|insert` — `ddl` for `CREATE TABLE` / constraints / indexes; `insert` for
  seed rows.

### Module bands (current)
| Band | Module | API domain | Purpose |
|------|--------|------------|---------|
| 10s | `admin` | `app/admin/` | Governance: users, profiles, modules, options, privileges, units, lists |
| 20s | `taxo` | `app/taxo/` | Asset taxonomy: categories, features, specifications |
| 30s | `collab` | `app/collab/` | Teams, roles, assignments, projects, dimensions, metrics |
| 40s | `lib` | `app/lib/` | Asset library: assets, characterizations, favorites, actions, relations |
| 50s | `inits` | `app/inits/` (stub) | GenAI initiatives: criterias, diagnostics, collaborations |
| 60s | `ana` | `app/insights/` (stub) | Analytics: dashboards, parameters, executions |

When adding a new module, allocate the next free band (70s, 80s, …). Don't squeeze
new modules between existing bands.

---

## Tables by module

### Admin — `db/sql/11-admin-ddl.sql`
| Table | PK | Key columns | Notes |
|-------|------|-------------|-------|
| `modules` | `code` | `name`, `icon`, `sort_order`, `is_active` | Drives sidebar primaryNav |
| `business_units` | `code` | `name`, `type`, `parent` (self-FK) | Org hierarchy |
| `lists` | `code` | `module`, `type`, `name` | Configurable enum catalog |
| `list_items` | `(list, lang, value)` | `label`, `sort_order` | Bilingual (en/es), one row per lang |
| `profiles` | `code` | `name`, `description`, `is_active` | Role profiles |
| `users` | `id` (bigserial) | `username`, `email`, `profile` (FK), `unit` (FK), `is_superuser`, `is_active`, `hashed_password` | SCRAM-SHA-256 hash format |
| `options` | `(module, code)` | `name`, `path`, `type`, `icon`, `sort_order` | Drives sidebar itemsNav |
| `privileges` | `(profile, module, option)` | `can_edit` | Access matrix |

### Taxonomy — `db/sql/21-taxo-ddl.sql`
| Table | PK | Key columns | Notes |
|-------|------|-------------|-------|
| `categories` | `code` | `name`, `parent` (self-FK), `description` | Hierarchical (14-node tree in seed) |
| `features` | `code` | `name`, `type`, `list` (optional FK→lists.code) | Asset metadata attributes |
| `specifications` | `(category, feature)` | `default_value`, `is_required` | Category-level feature defaults |

### Collab — `db/sql/31-collab-ddl.sql`
| Table | PK | Key columns | Notes |
|-------|------|-------------|-------|
| `teams` | `code` | `name`, `lead` (FK→users.id), `chat_channel_url`, `kanban_board_url` | Optional lead |
| `roles` | `code` | `name`, `description` | BACK, FRONT, QA, PO, TL |
| `assignments` | `id` (bigserial) | `user_id`, `team`, `role`, `valid_from`, `valid_to` | Temporal validity |
| `projects` | `code` | `team`, `status`, `repo_url`, `start_date`, `end_date` | Status from PROJECT_STATUS list |
| `dimensions` | `code` | `name`, `unit`, `scale` | Measurement axes |
| `metrics` | `id` (bigserial) | `dimension`, `assignment`, `value`, `measured_at` | Master-detail under dimensions |

### Lib — `db/sql/41-lib-ddl.sql`
| Table | PK | Key columns | Notes |
|-------|------|-------------|-------|
| `assets` | `id` (bigserial) | `code`, `name`, `category` (FK), `status`, `tags` (JSONB), `details` (JSONB), `current_version` | Flexible metadata via JSON; semver label bumped by the versioning flow (HU-LI09) |
| `characterizations` | `(asset, version_label, feature)` | `value` | Asset × feature → free-text value, one row set per asset version |
| `favorite_assets` | `(user_id, asset)` | — | User bookmarks |
| `actions` | `id` (bigserial) | `type`, `asset`, `user_id`, `description`, `created_at` | Audit log (PROPOSAL, USAGE, COMMENT, VOTE, …) |
| `related_assets` | `(source, target)` | `relation_type`, `description` | DEPENDS_ON, EXTENDS, SIMILAR_TO, … |
| `asset_permissions` | `id` (bigserial) | `asset`, `target_type`, `target_value`, `access_level` | Fine-grained (USER/ROLE/TEAM × VIEW/MANAGE) |

### Inits — `db/sql/51-inits-ddl.sql` (schema only; module is a stub on the API side)
| Table | PK | Key columns |
|-------|------|-------------|
| `initiatives` | `id` (bigserial) | `name`, `status`, `priority_level`, `expected_impact`, `score` |
| `criterias` | `code` | `name`, `description`, `list` (FK→lists.code) |
| `diagnostics` | `(init, criteria)` | `creator_score`, `reviewer_score` |
| `favorite_inits` | `(user_id, init)` | — |
| `collaborations` | `id` (bigserial) | `init`, `user_id`, `type`, `content`, `created_at` |
| `related_inits` | `(source, target)` | `relation_type` |
| `init_permissions` | `id` (bigserial) | `target_type`, `target_value`, `access_level` |

### Ana — `db/sql/61-ana-ddl.sql` (schema only; module is a stub on the API side)
| Table | PK | Key columns |
|-------|------|-------------|
| `dashboards` | `id` (bigserial) | `name`, `type`, `sources_types`, `status` |
| `parameters` | `(dashboard, name)` | `data_type`, `is_required`, `default_value` |
| `favorite_dashboards` | `(user_id, dashboard)` | — |
| `executions` | `id` (bigserial) | `dashboard`, `user_id`, `duration_ms`, `status` |
| `dashboard_permissions` | `id` (bigserial) | `target_type`, `target_value`, `access_level` |

---

## Naming conventions

### Tables
- **Plural nouns**: `users`, `modules`, `teams`, `assets`, `initiatives`.
- **Junction tables**: name describes the relationship if it carries data
  (`assignments`, `characterizations`, `privileges`); otherwise `favorite_*`,
  `related_*`, `*_permissions`.

### Columns
| Column | Type | Meaning |
|--------|------|---------|
| `id` | `BIGINT GENERATED BY DEFAULT AS IDENTITY` | Surrogate PK |
| `code` | `VARCHAR(50)` (often), `PRIMARY KEY` | Human-readable PK |
| `is_active` | `BOOLEAN DEFAULT TRUE` | Soft-delete flag — set false instead of `DELETE` |
| `created_at` | `TIMESTAMPTZ NOT NULL DEFAULT NOW()` | Insertion timestamp |
| `updated_at` | `TIMESTAMPTZ` | Last mutation (set by API on PUT) |
| `*_id` | `BIGINT` | Surrogate-key FK (e.g. `user_id`) |
| `{table}` | `VARCHAR(50)` | Natural-key FK (e.g. `profile` → `profiles.code`) |

**Conventions to honor:**
- Natural keys when stable (modules, profiles, teams) — they double as i18n keys
  in the UI and stay human-debuggable in pgAdmin.
- Surrogate keys when the natural key is volatile or composite would be awkward
  (users, assignments, metrics, actions).
- Document FK targets inline as SQL comments:
  ```sql
  list VARCHAR(50) NOT NULL  -- references lists.code
  ```

### List / enum pattern
1. Add the catalog entry to `lists` (with `module`, `type`, `name`).
2. Add values to `list_items` (one row per `(list, lang, value)`).
3. Reference from a column with a SQL comment, e.g.
   `status VARCHAR(50)  -- references list_items.value where list='ASSET_STATUS'`.

`type` values on `lists`: `LIST_OF_VALUES`, `SCALE`, `FEATURE`, `CRITERIA`.

---

## Docker integration

`docker-compose.yml` mounts `./db/sql:/docker-entrypoint-initdb.d`. Postgres' standard
init protocol runs every `*.sql` file in that directory **in lexical order on first
boot of a fresh volume.**

```yaml
db:
  image: postgres:18
  ports: ["${DB_HOST_PORT:-5433}:5432"]   # host 5433 → container 5432 (avoid host 5432 clashes)
  volumes:
    - ./db/sql:/docker-entrypoint-initdb.d   # auto-run on fresh init
    - synapxia-db-volume:/var/lib/postgresql/data
  environment:
    POSTGRES_USER: ${DB_USER}
    POSTGRES_PASSWORD: ${DB_PASSWORD}
    POSTGRES_DB: ${DB_SCHEMA}
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
    interval: 30s
    timeout: 5s
    retries: 5
```

The API container waits via `depends_on: db: condition: service_healthy`.

### When changes take effect
- **Fresh volume** — `make rebuild` (drops the volume, re-runs all SQL in order).
- **Existing volume** — files in `/docker-entrypoint-initdb.d/` are **ignored**;
  Postgres only runs them on first init. Apply changes manually via `make shell`:
  ```bash
  make shell
  \i /docker-entrypoint-initdb.d/11-admin-ddl.sql  -- or copy/paste your DDL
  ```

This is the heart of the Constitution's additive-only DB rule: rather than risk
divergence between fresh-init and in-place-applied schemas, **every change must be
additive and re-runnable safely**, so `make rebuild` and manual apply produce the
same end-state.

---

## pgAdmin

```yaml
pgadmin:
  image: dpage/pgadmin4:9.11
  ports: ["${PGADMIN_HOST_PORT:-8081}:80"]   # host 8081 → container 80 (avoid host 8080 clashes)
  environment:
    PGADMIN_DEFAULT_EMAIL: ${PGADMIN_EMAIL}
    PGADMIN_DEFAULT_PASSWORD: ${PGADMIN_PASSWORD}
```

- URL: `http://localhost:8081` (host port; `PGADMIN_HOST_PORT`)
- Default credentials (dev): `admin@synapxia.com` / `synapxia` (per `make dev` banner).
- **Server auto-registration** — currently manual. The compose file references
  `/pgadmin-servers.json.template` + `/pgadmin-entrypoint.sh` but those files are
  not yet committed; first-run requires manually adding the `db` host through the UI.
  Connection: host `synapxia-db`, port `5432`, user/pw `synapxia` / `synapxia`,
  database `synapxia`.

---

## Seed data deep dive

### Admin user (`12-admin-insert.sql`)
```
username:     admin
email:        admin@synapxia.org
profile:      ADMINISTRATOR    (full access)
unit:         GEN_AI
is_superuser: TRUE
password:     Admin123!
hash:         SCRAM-SHA-256$4096:erZkGksCVwc49r8o18VeSg==$2c7…=:yw24DEvmi0xGcE7…=
id:           0    (reserved; everyone else starts at 1)
```

Use `api/hash_password.py` to mint new SCRAM hashes if you need to seed extra users.

### Profiles (3)
- `ADMINISTRATOR` — full read/edit access across all 7 modules.
- `ADMINISTRATIVE` — TAXO / COLLAB / LIB / INITS / ANA / PROC (read+edit); no ADMIN.
- `COLLABORATOR` — read-only on most modules; edit on INITS (propose initiatives).

### Modules (7)
`ADMIN`, `TAXO`, `COLLAB`, `LIB`, `INITS`, `ANA`, `PROC` — drive sidebar primaryNav.

### Options (32 navigation items across the 7 modules)
Drive sidebar itemsNav. See `12-admin-insert.sql` lines for the full inventory; the
per-module breakdown is in the comparison plan summary.

### Privileges
~70 rows. Each row says: "Profile X may access (Module Y, Option Z), edit flag = boolean".
Adding a new option for a profile? Insert a `privileges` row in `12-admin-insert.sql`.

### Test users (60, in `32-collab-insert.sql`)
- 12 users × 5 teams (`CORE`, `SUPPORT`, `OPS`, `ANALYTICS`, `LAB`).
- All use the same SCRAM hash as `admin` → login is `Admin123!`.
- Profile: `COLLABORATOR`, unit: `ENG`.
- Each is paired with an `assignments` row tying them to a team and a role
  (`BACK`, `FRONT`, `QA`, `PO`, `TL`).

### Taxonomy seeds (`22-taxo-insert.sql`)
14-node category tree:
```
AI_ASSETS
├── CLASSIC_AI
│   ├── ML_MODELS, FORECASTING, ANOMALY_DETECTION, NLP_CLASSIC
└── GEN_AI
    ├── PROMPTS, MCPS, AGENTS, FLOWS, RAG_APPS, MODELS, SKILLS, ASSISTANTS
```
18 features (`LANGUAGE`, `MODE`, `PLATFORM`, `REPOSITORY`, `FRAMEWORK`, `COMPLEXITY`,
`SUGGESTED_MODEL`, `PROMPT_TEMPLATE`, `TOOLS`, `INSTRUCTIONS`, …).

### Library sample (`42-lib-insert.sql`)
Three demo assets you can poke at in `/lib/assets`:
1. **Python Web Development Prompt** (PROMPTS) — VSCode + GPT-5 example with full
   prompt template.
2. **GitHub MCP Server** (MCPS) — remote MCP with TOOLS + SERVER_CONFIG JSON.
3. **Python Web Developer Agent** (AGENTS) — VSCode + GPT-5 agent with TOOLS + INSTRUCTIONS.

Plus a populated action log (publication, votes, comments) and a couple of
favorite/permission rows.

---

## Migration philosophy

> **Constitution V (Performance & Operability):** every surface runnable via
> Compose + Make with a health/boot path. The DB layer enforces this by being
> declaratively re-runnable from a fresh volume.

### The rules
1. **Additive only.** Add new tables, columns, indexes, FKs. Never `DROP COLUMN`,
   `RENAME TABLE`, or `ALTER` an existing column type without a documented
   migration + rollback path. The UI / API both rely on schema stability.
2. **Idempotent where possible.** New DDL files should be safe to re-run. Use
   `CREATE TABLE IF NOT EXISTS`, `INSERT … ON CONFLICT DO NOTHING`, etc., when
   reasonable.
3. **Module + band locality.** A change that touches `admin` lives in `11-admin-ddl.sql`
   (append to it) or in a new file with a fractional ordinal:
   `13-admin-{feature}-ddl.sql` if the change must come after `12-admin-insert.sql`.
4. **Match the API.** A new SQLModel table in `api/app/{domain}/internal/models.py`
   must have a corresponding DDL entry. Use `make rebuild` to verify.
5. **Rollback notes.** Destructive changes (none should exist yet) require explicit
   rollback SQL in the commit body and an entry in the AGENTS.md gotchas list.
6. **No one-off remediation files.** Do **not** create dated/standalone "remediation"
   SQL (e.g. a `db/remediation/` folder) to patch an already-initialized DB. Put every
   schema/seed change in the canonical `db/sql/*` files (append to the module DDL/insert
   or add a fractional-ordinal file per rule 3). Apply changes to an existing DB by
   re-running the relevant `db/sql` statements / `make rebuild` — not via bespoke
   dated scripts.

### What `delete.sql` and `drop.sql` are for
- **`delete.sql`** — `DELETE FROM …` for every table in reverse-FK order. Wipes data
  but keeps schema. Useful for re-seeding in tests once we have them.
- **`drop.sql`** — `DROP TABLE … CASCADE` for every table. Total teardown without
  killing the Postgres volume / role / database. Useful in CI when you want to
  re-apply DDL against an existing cluster.

Neither is auto-run — they live in `db/sql/manual/`, a subdirectory the Postgres
entrypoint doesn't recurse into. Run them manually with `make shell` then
`\i /docker-entrypoint-initdb.d/manual/delete.sql`.

---

## Production: Neon via `neon-migrate.sh`

`db/neon-migrate.sh` is the production migration runner. It:
1. Reads `NEON_DATABASE_URL` from env (Vercel/Neon-injected).
2. Runs each `db/sql/*.sql` file in lexical order against the remote DB via `psql`.
3. Is **idempotent only by accident** — re-running `12-admin-insert.sql` against a
   non-empty DB will throw uniqueness errors. Use `--first-init` or hand-edit before
   re-running.

Trigger manually (not from CI yet):
```bash
NEON_DATABASE_URL='postgres://…' bash db/neon-migrate.sh
```

Future direction (post-Launch): adopt Alembic for prod schema diffs to enable
proper rollback semantics. See the comparison plan's P1 backlog.

---

## Common operations

```bash
# Open psql in the running container
make shell

# Tail DB logs
make logs-db

# Bash into the DB container (advanced)
make exec-db

# Clean rebuild (drops volume, re-runs all SQL)
make rebuild

# Backup the current state
make backup-db            # writes ./backups/synapxia-YYYYMMDD-HHMMSS.sql

# Restore from the latest backup
make restore-db

# List SQL migration files
make migrations
```

### Useful psql snippets
```sql
-- List all tables
\dt

-- Describe a table
\d users
\d+ assets         -- includes column comments and indexes

-- Verify the seed
SELECT username, email, profile FROM users WHERE is_superuser = TRUE;
SELECT code, name FROM modules ORDER BY sort_order;
SELECT list, value, lang, label FROM list_items
 WHERE list='ASSET_STATUS' ORDER BY lang, sort_order;

-- Check FK coverage
SELECT conname, conrelid::regclass AS table, confrelid::regclass AS references
  FROM pg_constraint WHERE contype = 'f' ORDER BY conrelid::regclass::text;

-- Inspect JSON columns
SELECT id, code, tags, details FROM assets LIMIT 5;
```

---

## Debugging

**Common errors:**
- **`schema "synapxia" does not exist`** — volume not initialized. `make rebuild` to
  force re-init.
- **`relation "users" does not exist`** — DDL file failed silently. Check
  `make logs-db` from the moment of init; look for an `ERROR` line.
- **`duplicate key value violates unique constraint "users_pkey"`** — running an
  insert seed against an existing DB. The init only runs on fresh volumes; for
  re-runs use `delete.sql` or `make rebuild`.
- **`could not connect to server: Connection refused`** (from API) — DB not healthy
  yet. The compose healthcheck takes 5–30s on cold start.
- **API can't find tables but `\dt` shows them** — `DB_SCHEMA` mismatch between API
  config and DB. They must match (both `synapxia` by default).

---

## Adding a new table (step-by-step)

1. Pick the module band (`admin` = 10s, `taxo` = 20s, …).
2. Append the `CREATE TABLE …` to `{NN}-{module}-ddl.sql` (preserve existing comments
   for FK references).
3. Add seed rows to `{NN+1}-{module}-insert.sql` if needed.
4. Mirror the table in `api/app/{module}/internal/models.py` (`SQLModel(table=True)` +
   `Create` / `Update` schemas).
5. Add a router in `api/app/{module}/routes/{entity}.py` following the canonical CRUD
   pattern (`api/CLAUDE.md` has the template).
6. Add UI service + types + page (`ui/CLAUDE.md` has the template).
7. `make rebuild` and verify with `make test`.
8. Add a CHANGELOG entry with `YYYY-MM-DD HH:MM` timestamp listing every affected file.

---

## Rules that bite here (recap from AGENTS.md)

- **Additive-only changes.** No `DROP`, `RENAME`, or breaking `ALTER` without a
  documented rollback in the PR body.
- **Migrations only take effect on fresh volume** (`make rebuild`) or via manual
  apply through `make shell`.
- **Numbered file order matters.** Don't reuse a number; pick the next free in the
  module's band.
- **Match the API model.** Every SQLModel table needs a corresponding DDL row;
  every new column needs a matching `*Create` / `*Update` field.
- **Composite keys are explicit.** Use `PRIMARY KEY (col_a, col_b)` not surrogate
  serial when the natural key is meaningful (`privileges`, `characterizations`,
  `list_items`, `options`).
- **Logical delete in code, not DB.** The DB allows soft-delete via `is_active`;
  hard `DELETE` is reserved for cleanup scripts (`delete.sql`).

---

## Resources

- [PostgreSQL 18 docs](https://www.postgresql.org/docs/18/)
- [SQL conventions guide](https://www.sqlstyle.guide/) — close to what we follow
- [pgAdmin 4 docs](https://www.pgadmin.org/docs/pgadmin4/latest/)
- Repo-wide: [`../AGENTS.md`](../AGENTS.md), [`../api/CLAUDE.md`](../api/CLAUDE.md),
  [`../memory/memory.md`](../memory/memory.md)
