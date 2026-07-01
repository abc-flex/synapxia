# AGENTS.md — SynapxIA

Canonical guidance for AI coding agents (Claude Code, Copilot, etc.) working in this
repo. Every `CLAUDE.md` in this project links back here. Read this first, then the
project-specific `CLAUDE.md` for the surface you are editing.

> **Source of truth for rules:** [`.specify/memory/constitution.md`](.specify/memory/constitution.md) (v1.0.0).
> This file summarizes it for day-to-day work; the Constitution wins on any conflict.

## What this is

SynapxIA is a team-collaboration and performance-measurement platform built as a
**modular monolith** with three deployable surfaces, orchestrated by Docker Compose:

| Surface | Path | Stack | Port |
|---------|------|-------|------|
| API | [`api/`](api/CLAUDE.md) | Python ≥3.12, FastAPI + SQLModel, `uv` | 8000 (→80) |
| UI | [`ui/`](ui/CLAUDE.md) | Astro 4 + Tailwind + Flowbite, Bun | 4321 |
| DB | [`db/`](db/CLAUDE.md) | PostgreSQL 18, ordered SQL migrations | 5432 (host 5442) |

API domains live under `api/app/`: `admin, auth, collab, taxo, genai, inits,
insights, workflows`, with shared plumbing in `api/app/internal/`.

## AI coding memory

Running history and decisions are tracked in [`memory/`](memory/):
- [`memory/CHANGELOG.md`](memory/CHANGELOG.md) — what changed, per PR / merge / direct push to `develop` / `main` / `production`.
- [`memory/MEMORY.md`](memory/MEMORY.md) — patterns, decisions, known issues for AI agents.

### Mandatory update rules

| Event | Required action |
|-------|-----------------|
| PR opened / branch ready to merge | Append **one** entry to `memory/CHANGELOG.md` covering the whole PR (newest at top, never edit other PRs' entries) |
| Direct push to `develop` / `main` / `production` | Same rule — append **one** entry covering the pushed change set, **before or with** the push |
| Architectural decision | The PR's (or push's) `CHANGELOG.md` entry calls it out **and** updates the relevant section of `MEMORY.md` |
| Feature completed | Update the feature status in `MEMORY.md` + add the `CHANGELOG.md` entry |
| New blocker found | Add it to the "Known blockers" section of `MEMORY.md` |

**Every important group of changes must have a CHANGELOG entry.** That means every PR, every merge commit, and every direct push to a principal branch. The only thing that does NOT get its own entry is an individual commit on a branch that already has its rollup entry — in that case, **update the existing entry** instead.

Entry format (the **time** is required so same-day entries stay ordered):

```
## YYYY-MM-DD HH:MM — Short descriptive title
- 1–3 bullets on what changed and why.
- Files affected: `path/to/file.ts`, `path/to/other.py`
```

Use 24-hour local time (Colombia/America for this team). If you're an agent and don't have the current time loaded, run `date '+%Y-%m-%d %H:%M'` and use that.

**One PR / merge / direct-push = one entry.** Do not append a new entry per individual commit — squash the work into a single rollup entry covering everything that ships. If you commit again on the same branch (e.g. fixing a review comment), update the entry you already added on that branch instead of appending another one. A PR open for a week is still one entry, just with a richer summary.

> Historical note: entries dated before 2026-06-10 use a `### Added / Changed / Fixed` auto-generated format produced by a now-removed `.githooks/post-commit` + `post-merge` flow. If your local clone previously ran `make hooks`, run `git config --unset core.hooksPath` once to stop pointing at the deleted directory.

## Key commands (from repo root)

```bash
make up        # start all containers (waits ~30s for DB init), then health check
make dev       # up + print URLs and login credentials
make down      # stop containers
make rebuild   # clean rebuild including volumes
make test      # health checks: API /api/health, DB pg_isready, admin user
make logs      # all logs  (also logs-api / logs-db / logs-ui)
make shell     # psql into the DB
```

URLs after `make up`: UI http://localhost:4321 · API docs http://localhost:8000/docs ·
PgAdmin http://localhost:8080. Seed login: `admin` / `Admin123!`.

## The five Constitution principles (all MUST)

1. **Modular monolith boundaries** — new features go inside the owning `api/app/{domain}`
   (routes in `routes/`, data access in `internal/`). Shared cross-domain code only in
   `api/app/internal`. Do not duplicate connection/auth plumbing per module.
2. **API-first contract stability** — do not remove or rename existing endpoints,
   request keys, or response keys in place; incompatible changes need a versioned route
   + UI adaptation plan. List endpoints keep bounded `skip`/`limit` pagination.
3. **Risk-based testing** — tests proportional to risk. Backend contract/auth/migration/
   permission changes REQUIRE automated tests; UI-only copy/layout changes may use
   documented manual verification. Always run `make test`.
4. **Security & secret hygiene** — auth stays JWT Bearer + bcrypt; no plaintext
   passwords; secrets only via env vars, never committed, masked in logs. Preserve
   `is_active` / `is_superuser` semantics.
5. **Performance & operability** — use managed sessions/engines from `api/app/internal`,
   avoid unbounded/N+1 queries; keep every surface runnable via Compose + Make with a
   health/boot path; keep logging structured.

## Conventions

- **API:** pagination via `skip`/`limit`; logical delete via `is_active=False` (records
  retained); status codes 409 (unique conflict), 400 (validation), 403 (auth), 404
  (missing). Auth details in [`api/AUTH.md`](api/AUTH.md).
- **API response envelope:** every JSON response under `/api/` (except `/api/auth/*`,
  `/health`, `/`) is wrapped as `{ data, error, meta }` (success) / `{ data:null,
  error:{code,message,details}, meta }` (error) by a global middleware + exception
  handlers in `api/app/main.py` (helpers in `api/app/internal/responses.py`). Routes
  still return bare models / raise `HTTPException`; the UI unwraps `.data` centrally in
  `ui/src/lib/api.ts`. See [`api/CLAUDE.md`](api/CLAUDE.md) § "Response envelope".
- **UI types:** three interfaces per entity in `ui/src/types/api.ts` —
  `Entity`, `EntityCreate`, `EntityUpdate`.
- **UI services:** CRUD wrappers in `ui/src/lib/{entity}.ts` around `lib/api.ts`.
- **UI pages:** Astro CRUD pages in `ui/src/pages/{module}/{entity}.astro`, mirroring an
  existing page (e.g. `admin/options.astro`); reuse shared `DataTable`, `CrudModal`,
  `Toast` components.
- **i18n:** every user-facing string in both `ui/src/i18n/en.json` and `es.json`, keyed
  per entity/module.
- **DB:** migrations are ordered SQL files in `db/sql/` (auto-run on init); changes are
  additive/migration-driven, destructive changes need rollback instructions.

## Spec-driven workflow

Features are spec-driven (SpecKit). Each feature gets a folder under [`specs/`](specs/)
with `spec.md`, `plan.md`, `data-model.md`, `quickstart.md`, `tasks.md`. Plans MUST
include a **Constitution Check** mapping the design to the five principles before
implementation. Templates live in [`.specify/templates/`](.specify/templates/).

## Pre-PR checklist

- [ ] Code lives in the owning domain; shared logic only in `api/app/internal`.
- [ ] No removed/renamed existing API request/response keys; pagination preserved.
- [ ] Tests added for any auth/contract/migration/permission change; `make test` passes.
- [ ] No committed secrets; auth stays JWT + bcrypt.
- [ ] New UI entities have `api.ts` types, a `lib/` service, and `en.json` + `es.json` keys.
- [ ] Services still start via `make up`.
