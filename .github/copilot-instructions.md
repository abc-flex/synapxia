# synapxia Development Guidelines

Auto-generated from feature plans under `specs/`. Last updated: 2026-09-15.

> **Note:** this file was relocated from `.github/agents/copilot-instructions.md` (a path
> GitHub Copilot never actually reads) to `.github/copilot-instructions.md` (the real
> convention). It is **not** currently wired into the `agent-context` SpecKit extension —
> only `CLAUDE.md` is (see `.specify/extensions/agent-context/agent-context-config.yml`).
> If this team starts using Copilot for spec-driven work, either regenerate this file by
> hand from `specs/*/plan.md` after each new plan, or point the extension's `context_file`
> at this path instead (single-file config — see the extension's `README.md`).

## Active Technologies
- Python ≥3.12 (backend, `uv`-managed), FastAPI + SQLModel + SQLAlchemy · TypeScript /
  Astro 5 (SSR) + Svelte 5 islands + Tailwind (frontend, Bun) — see `specs/001-collab-projects`,
  `specs/002-collab-dimensions-metrics`.
- PostgreSQL 18, ordered SQL migrations in `db/sql/`.

## Project Structure

```text
api/     # FastAPI + SQLModel backend (modular monolith, domains under api/app/)
ui/      # Astro + Svelte frontend (Bun)
db/      # SQL migrations + seed data
specs/   # SpecKit feature specs (spec/plan/data-model/quickstart/tasks per feature)
```

## Commands

```bash
make dev    # start everything + print URLs and login
make test   # health checks (API, DB, admin user)
```

## Code Style

Python ≥3.12 (backend), TypeScript/Astro (frontend): follow standard conventions — see
root `AGENTS.md` for the binding Constitution rules and per-surface conventions.

## Recent Changes
- 002-collab-dimensions-metrics: `collab/dimensions` + `collab/metrics` CRUD (API + UI).
- 001-collab-projects: `collab/projects` CRUD (API + UI).

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
