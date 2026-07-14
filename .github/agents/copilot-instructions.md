# synapxia Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-04-03

## Active Technologies
- Python ≥ 3.12 (backend) · TypeScript / Astro (frontend) + FastAPI 0.11x, SQLModel, SQLAlchemy, Astro 4, Bun (002-collab-teams-fix)
- PostgreSQL (existing `teams` and `users` tables — no migration required) (002-collab-teams-fix)
- Python >= 3.12 (backend), TypeScript/Astro (frontend) + FastAPI, SQLModel, SQLAlchemy, Astro, Bun (002-collab-teams-fix)
- PostgreSQL (existing `teams` and `users` tables) (002-collab-teams-fix)
- Python 3.12 (backend, `uv`-managed) · TypeScript / Astro 4 (frontend, Bun) + FastAPI + SQLModel (backend) · Astro + Tailwind CSS + Bun (frontend) (002-collab-dimensions-metrics)
- PostgreSQL — `dimensions` and `metrics` tables exist; no migration needed (002-collab-dimensions-metrics)

- Python ≥3.12 (backend), TypeScript / Astro 4 (frontend) + FastAPI + SQLModel (backend), Astro + Bun + TailwindCSS (frontend) (001-collab-projects)

## Project Structure

```text
backend/
frontend/
tests/
```

## Commands

cd src; pytest; ruff check .

## Code Style

Python ≥3.12 (backend), TypeScript / Astro 4 (frontend): Follow standard conventions

## Recent Changes
- 002-collab-dimensions-metrics: Added Python 3.12 (backend, `uv`-managed) · TypeScript / Astro 4 (frontend, Bun) + FastAPI + SQLModel (backend) · Astro + Tailwind CSS + Bun (frontend)
- 002-collab-teams-fix: Added Python >= 3.12 (backend), TypeScript/Astro (frontend) + FastAPI, SQLModel, SQLAlchemy, Astro, Bun
- 002-collab-teams-fix: Added Python ≥ 3.12 (backend) · TypeScript / Astro (frontend) + FastAPI 0.11x, SQLModel, SQLAlchemy, Astro 4, Bun


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
