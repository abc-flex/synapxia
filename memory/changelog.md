# Changelog

All notable changes to SynapxIA are recorded here.
Entries are written automatically when AI-assisted changes are merged to `develop`, `main`, or `prod`.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased] — claude/upbeat-galileo-fiupL

### Fixed
- `ui/src/layouts/Layout.astro` created — `dashboard.astro` imported a missing layout, breaking Vercel build.
- `ui/astro.config.mjs` — hardened `@` alias from literal `/src` to `fileURLToPath(new URL('./src', import.meta.url))` for reliable resolution at build time.

### Docs
- Added root `AGENTS.md` — canonical AI coding guide covering the 5 Constitution principles, architecture, conventions, patterns, and pre-PR checklist.
- Added root `CLAUDE.md` — thin pointer to `AGENTS.md` with everyday commands.
- Added `api/AGENTS.md`, `ui/AGENTS.md`, `db/AGENTS.md` — project-specific agent guidance (stack, structure, commands, rules).
- Added `api/CLAUDE.md`, `ui/CLAUDE.md`, `db/CLAUDE.md` — slim pointers to their sibling AGENTS.md.

---

## [0.3.0] — 2026-06-06 · develop (c0e05e9)

### Changed
- `taxo` module: refactored `categories` fields and `order_by` (UI + API); catalog module renamed to `taxo`.
- `admin` module: refactored `users` and table fields across UI and API; `roles` renamed to `profiles`.

### Database
- Added `ana` module DDL; renamed `roles → profiles` in admin; permissions inclusion; options review up to `lib` module.

---

## [0.2.0] — 2026-05-XX · Merge PR #13 (002-collab-dimensions-metrics)

### Added
- `collab/dimensions` — full CRUD UI + API (code, name, description, scale, unit).
- `collab/metrics` — full CRUD UI + API, master-detail from dimensions (dimension + assignment + value + measured_at).
- `collab/assignments`, `collab/projects`, `collab/teams` — CRUD operations reviewed and tested.

### Fixed
- Filter management with hidden columns; pagination previous/next buttons alignment.
- Initial blank-space bug in CrudModal text input fields.
- Sidebar: module open state and active option emphasis.

---

## [0.1.0] — 2026-04-XX · Merge PR #12 (001-collab-projects)

### Added
- `collab/projects` — CRUD UI, API, and spec (`001-collab-projects`); team filter via `?team=<code>`.
- `collab/dimensions` and metrics spec (`002-collab-dimensions-metrics`).
- `item_translations` CRUD (admin module).
- `catalog/features` CRUD (UI + API).
- `collab/teams` CRUD (UI + API).
- Sidebar: one module open at a time; active option highlighted.
- `admin/{lists,list_items,business_units,privileges,users}` CRUD reviewed and tested.

### Changed
- API routes refactored: active-record filtering only, function naming convention standardised across `admin`, `catalog`, `collab`.
- SQL files renamed with ordered numbering convention.
- CrudModal dialog size updated; `types/` directory cleaned.

### Infrastructure
- Data models updated (ERD `docs/models.drawio`).
- Initial `ana` module schema added.

---

## [0.0.1] — Initial setup

### Added
- Monorepo scaffold: `api/` (FastAPI + SQLModel + `uv`), `ui/` (Astro 4 + Bun + Tailwind), `db/` (PostgreSQL 18 + SQL migrations).
- Docker Compose orchestration with health checks; Makefile dev targets.
- JWT + bcrypt authentication (`fastapi-users`); admin seed user `admin/Admin123!`.
- Base SQL schema for `admin`, `taxo`, `collab`, `lib`, `inits`, `ana` modules.
- SpecKit governance: Constitution v1.0.0, spec templates, agent prompts under `.github/agents/`.
