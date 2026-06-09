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

## Security Implementation (PR #25)

As of PR #25, **all API endpoints are secured with JWT authentication + role-based access control (RBAC)**:

- ✅ All endpoints require valid JWT token (401 Unauthorized if missing)
- ✅ Privilege matrix enforced per user profile (403 Forbidden if insufficient)
- ✅ Frontend routes protected with Astro middleware
- ✅ Rate limiting on login (5 attempts = 15-min lockout)

**For deployment to Vercel**, see [`SECURITY_DEPLOYMENT.md`](SECURITY_DEPLOYMENT.md) — requires:
- `SECRET_KEY` environment variable (generate: `openssl rand -hex 32`)
- `CORS_ORIGINS` pointing to deployed UI URL
- `APP_ENV=production`

Local development uses defaults (see `.env.template`), but production Vercel deployment is **security-critical**.

## Before you commit

Governance is binding — see [`.specify/memory/constitution.md`](.specify/memory/constitution.md)
and the pre-PR checklist in [`AGENTS.md`](AGENTS.md). Features are spec-driven; specs live
in [`specs/`](specs/).

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
<!-- SPECKIT END -->
