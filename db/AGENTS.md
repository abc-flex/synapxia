# AGENTS.md — Database

**Read the root [`AGENTS.md`](../AGENTS.md) first** for the full conventions and the
binding Constitution rules. This file covers what is specific to the database.

## Stack

PostgreSQL 18 (Docker image `postgres:18`), port 5432. Schema is defined as **ordered
SQL files** in `db/sql/`, mounted to `/docker-entrypoint-initdb.d` and auto-run on a
fresh DB. There is no ORM-based migration tool — SQL files are the migrations.

## Naming / ordering convention

Files run in lexical order. The numbering groups DDL then INSERT per domain:

```
11-admin-ddl.sql   12-admin-insert.sql
21-taxo-ddl.sql    22-taxo-insert.sql
31-collab-ddl.sql  32-collab-insert.sql
41-lib-ddl.sql     42-lib-insert.sql
51-inits-ddl.sql   52-inits-insert.sql
61-ana-ddl.sql
manual/drop.sql / manual/delete.sql   # teardown / cleanup helpers (subdir; not auto-run on init)
```

Add new schema as a new numbered file in the right domain band; keep DDL before its
INSERTs.

## Commands

```bash
make shell        # psql -U synapxia -d synapxia  (inside the db container)
make migrations   # list db/sql/ files
make logs-db      # tail DB logs
make backup-db    # pg_dump to ./backups/
make rebuild      # drop volumes and re-init from db/sql/ (DESTROYS data)
```

Default local credentials: user `synapxia`, password `synapxia`, db `synapxia`.

## Rules that bite here

- **Additive & migration-driven:** schema changes are additive; destructive changes
  require rollback instructions (per the Constitution).
- Changes only take effect on a fresh volume (`make rebuild`) unless applied manually via
  `make shell`.
- Reflect schema changes in the API SQLModel models and, if they affect API contracts,
  follow the contract-stability rules in [`AGENTS.md`](../AGENTS.md).
- ERD reference: [`../docs/models.drawio`](../docs/models.drawio).
