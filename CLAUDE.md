# CLAUDE.md

**Read [`AGENTS.md`](AGENTS.md) first** — it is the canonical guidance for AI agents in
this repo (architecture, Constitution rules, conventions, workflow). This file is a thin
pointer.

## Repo at a glance

SynapxIA is a modular monolith with three surfaces, run together via Docker Compose:

- **API** — FastAPI + SQLModel (`uv`), port 8000 → see [`api/CLAUDE.md`](api/CLAUDE.md)
- **UI** — Astro + Tailwind (Bun), port 4321 → see [`ui/CLAUDE.md`](ui/CLAUDE.md)
- **DB** — PostgreSQL 18, SQL migrations, port 5432 → see [`db/CLAUDE.md`](db/CLAUDE.md)

## Everyday commands

```bash
make dev    # start everything + print URLs and login (admin / Admin123!)
make test   # health checks (API, DB, admin user)
make logs   # tail logs (logs-api / logs-db / logs-ui for one service)
make down   # stop
```

## Before you commit

Governance is binding — see [`.specify/memory/constitution.md`](.specify/memory/constitution.md)
and the pre-PR checklist in [`AGENTS.md`](AGENTS.md). Features are spec-driven; specs live
in [`specs/`](specs/).
