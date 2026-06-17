# AI Coding Memory — SynapxIA

Running context for AI coding agents. Updated on significant merges to `develop`/`main`/`prod`.
For binding rules see [`../AGENTS.md`](../AGENTS.md) and [`.specify/memory/constitution.md`](../.specify/memory/constitution.md).

---

## What this project is

SynapxIA is a **team collaboration and performance-measurement platform** — a modular
monolith with three surfaces (API, UI, DB) orchestrated by Docker Compose.

Key domain concepts: **Teams → Assignments → Projects / Dimensions → Metrics**.
Users are assigned to teams with roles; teams own projects; dimensions define measurement
axes; metrics record measurements for assignments against dimensions.

---

## Tech snapshot

| Surface | Stack | Port |
|---------|-------|------|
| API | Python ≥3.12, FastAPI + SQLModel, `uv` | 8000 |
| UI | Astro 4 + Tailwind + Flowbite, Bun | 4321 |
| DB | PostgreSQL 18, ordered SQL migrations in `db/sql/` | 5432 |

Run everything: `make dev`. Verify: `make test`.

---

## Established patterns (don't reinvent)

### API (backend)
- Domain modules: `api/app/{admin,auth,collab,taxo,genai,inits,insights,workflows}/`
- Shared plumbing (DB session, auth deps) lives in `api/app/internal/` — never duplicated per module.
- List endpoints always take `skip`/`limit`. Logical delete via `is_active=False`.
- Status codes: 409 unique conflict · 400 validation · 403 auth · 404 not found.

### UI (frontend)
- **Types:** 3 interfaces per entity in `ui/src/types/api.ts` → `Entity`, `EntityCreate`, `EntityUpdate`.
- **Services:** CRUD wrappers in `ui/src/lib/{entity}.ts` around `lib/api.ts`.
- **Pages:** `ui/src/pages/{module}/{entity}.astro`. Mirror closest existing page (e.g. `admin/options.astro`).
- **Components:** reuse `DataTable`, `CrudModal`, `Toast` — don't create new alternatives.
- **i18n:** every user-facing string in both `ui/src/i18n/en.json` and `es.json`, keyed per entity/module.
- **Layouts:** `BaseLayout.astro` for sidebar pages; `Layout.astro` for standalone full-screen pages (e.g. `/dashboard`, `/login`).
- **`@` alias** resolves to `ui/src/` (via `fileURLToPath` in `astro.config.mjs`).

### DB
- Migrations: ordered SQL files `db/sql/{NN}-{module}-{ddl|insert}.sql`. Additive only.
- Changes only take effect on a fresh volume (`make rebuild`).

---

## Decisions log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-06-17 | LIB **curated catalogs** (Prompt Gallery first) are final-user **card galleries**, not admin `DataTable` pages. Reusable foundation: `components/lib/gallery/{CardGallery,GalleryCard,CatalogFormModal}.astro` + `lib/{catalogGallery,catalogModal}.ts`. The page uses a **bundled `@/` `<script>`**, never inline `type="module"` + `/src/...` imports (those 404 in the Vercel build). | Catalogs are discovery/reuse surfaces for devs/tech users; one card framework, per-catalog custom card+modal rendering. **Extension recipe** for HU-LI13–19 (MCP/Agent/Flow/Skill/Assistant/RAG/Model): add `{X}Card.astro` (wrap `GalleryCard` + custom chips), `{X}FormModal.astro` (wrap `CatalogFormModal` + that category's feature inputs + `mountCatalogModal({category, features})`), a `lib/{x}.astro` page, and i18n keys. No backend work — all categories+specs are seeded. |
| 2026-06-15 | `DataTable.astro` split into an orchestrator shell + `components/table/partials/` (Toolbar, Filters, SearchExport, Head, Body, Cell, Actions, Pagination, Empty) + pure helpers in `lib/datatable.ts` + types in `types/datatable.ts` | The 567-line monolith was a "god component". Split is **DOM-identical** (verified by before/after dev-render diff), so `advancedTable.ts` (which binds by `${tableId}-*` ids + DOM structure) and the card-view CSS are untouched. Sub-parts take `tableId`/props and rebuild the same ids. The 3 filter selects are now one loop. |
| 2026-06-15 | `DataTable` column config gained parametrized field types via `as` (`title`/`status`/`tags`/`date`/`badge`/`boolean`/`text`) + per-page `subtitleKey`/`subtitleFormat` | One reusable config drives both the desktop table and the mobile card; pages only annotate their `columns`. `title` renders bold name + muted subtitle (`.dt-title`/`.dt-subtitle`); the subtitle's source column is set `visible:false` so it isn't shown twice (still in `data` for export/filter). Card view keys off `td[data-col="title"]`, not column order. `advancedTable.ts` untouched. |
| 2026-06-07 | Added `ui/src/layouts/Layout.astro` (minimal shell) | `dashboard.astro` used a standalone full-screen design, not the sidebar BaseLayout; the file was simply missing. |
| 2026-06-07 | Hardened `@` alias to `fileURLToPath(new URL('./src', import.meta.url))` | Literal `/src` is filesystem-absolute and breaks Vercel builds. |
| 2026-06-07 | Created `AGENTS.md` per project + root, thin `CLAUDE.md` pointers | AI tools need a curated single entry point; Constitution and patterns were undiscoverable. |
| 2026-05-XX | `catalog` module renamed to `taxo` | Better reflects digital asset taxonomy purpose. |
| 2026-04-XX | `roles` renamed to `profiles` in admin | Profiles better represents the concept; roles concept retained for collab assignments. |
| 2026-04-XX | Master-detail pattern for dimensions → metrics | Mirrors admin roles → privileges pattern for consistency. |

---

## Feature status

### Shipped
| Feature | Domain | Status |
|---------|--------|--------|
| Admin CRUD (users, profiles, modules, options, privileges, lists, list_items, item_translations) | admin | ✅ done |
| Taxonomy (categories hierarchical, features) | taxo | ✅ done |
| Team collaboration (teams, roles, assignments, projects, dimensions, metrics) | collab | ✅ done |
| Asset library (assets, characterizations, favorites, actions, asset_relations) | lib | ✅ done |
| Prompt Gallery (HU-LI12) — final-user card gallery on the reusable gallery framework | lib | ✅ done |
| Curated catalogs HU-LI13–19 (MCP/Agent/Flow/Skill/Assistant/RAG/Model) — framework ready, pages pending | lib | ⬜ pending (use the gallery extension recipe) |
| Auth (JWT HS256 + bcrypt, /me, register, change-password) | auth | ✅ done |
| Vercel deployment (API serverless via Mangum + UI static + Neon DB) | infra | ✅ done |
| Per-service CLAUDE.md (api/ui/db ~800 lines each) | docs | ✅ done |
| Changelog HH:MM timestamps + hook automation | tooling | ✅ done |

### In progress / stubs
| Domain | Status | Notes |
|--------|--------|-------|
| genai | ⚠️ stub | No models or routes yet — needs SpecKit spec first |
| inits | ⚠️ stub | No models or routes yet |
| insights | ⚠️ stub | No models or routes yet |
| workflows | ⚠️ stub | No models or routes yet |

### Next (P1.1 in progress)
| Item | Status |
|------|--------|
| API linting: ruff + black + isort + mypy | ✅ config added to pyproject.toml |
| UI linting: ESLint (Astro + TS) | ✅ .eslintrc.json + package.json updated |
| pytest skeleton (api/tests/) | ✅ conftest + health/auth/users test files |
| Makefile: make lint/fmt/fmt-check/pytest/lint-ui | ✅ updated |
| memory.md expansion | ✅ this update |

---

## Known blockers

| Severity | Issue | Notes |
|----------|-------|-------|
| P0 | Vercel build-time API fetch | Static pages call `localhost:8000` during `astro build`; fails on Vercel (`ECONNREFUSED`). Fix: set `PUBLIC_API_BASE_URL` env in Vercel project settings pointing to deployed API. `api.ts` returns `[]` on failure so pages pre-render empty and hydrate client-side. |
| P1 | API linting not CI-gated | `make lint`/`make fmt-check` now exist but not wired into GitHub Actions. Violations won't block PRs until CI workflow is added. |
| P1 | No UI tests | Manual verification per quickstart guides only. ESLint now wired; UI test framework (Playwright) is post-launch scope. |
| P1 | caniuse-lite stale | Run `npx update-browserslist-db@latest` in `ui/` before next UI release. |
| P2 | Stub domains not implemented | `genai`, `inits`, `insights`, `workflows` are empty placeholders — each needs a SpecKit spec before implementation. |
| P2 | No Alembic migrations | Append-only SQL files work for greenfield; first breaking schema change in production will require `api/alembic/` setup. |

---

## Docs routing table

| Task | Primary doc | Supporting |
|------|-------------|------------|
| Onboarding / what is this | `README.md` | `memory/memory.md` (this file) |
| User stories (by module) | `docs/user-stories/README.md` | `docs/diagrams/`, source `Control H de U.xlsx` |
| API changes | `api/CLAUDE.md` | `AGENTS.md` |
| UI changes | `ui/CLAUDE.md` | `AGENTS.md` |
| DB / schema changes | `db/CLAUDE.md` | `AGENTS.md` |
| Auth deep-dive | `api/AUTH.md` | `api/CLAUDE.md` § Auth |
| Adding a resource (full stack) | `api/CLAUDE.md` § "Adding a new resource" | `ui/CLAUDE.md` § "Adding a CRUD page", `db/CLAUDE.md` § "Adding a new table" |
| Adding a whole new domain | `api/CLAUDE.md` § "Adding a new domain" | `db/CLAUDE.md` § "Module bands" |
| Deployment to Vercel + Neon | `docs/DEPLOYMENT.md` | `api/CLAUDE.md` § Deployment |
| Constitution rules | `.specify/memory/constitution.md` | `AGENTS.md` |
| SpecKit workflow (spec → plan → implement) | `AGENTS.md` § SpecKit | `specs/` + `.specify/templates/` |
| Changelog discipline | `AGENTS.md` § Changelog | `.claude/hooks/update-changelog.sh` |
| Linting + tests | `api/CLAUDE.md` § "Linting & testing" | `api/pyproject.toml` `[tool.*]` sections |
| Troubleshooting | `api/CLAUDE.md` § Debugging | `ui/CLAUDE.md` § Debugging, `db/CLAUDE.md` § Debugging |

---

## Session history (AI-assisted work)

### 2026-06-07 — Session (claude-opus-4-8)
- Explored and documented repo: created `AGENTS.md` (root + api, ui, db) and `CLAUDE.md` pointers.
- Fixed Vercel build failure: added missing `ui/src/layouts/Layout.astro` and fixed `@` alias.
- Created `memory/changelog.md`, `memory/memory.md`, and changelog automation hook.
- Expanded per-service CLAUDE.md (api/ui/db → 800+ lines each): modules, routes, patterns, key surfaces, debugging.
- Added HH:MM timestamps to `.claude/hooks/update-changelog.sh` for same-day changelog ordering.
- Added linting config to `api/pyproject.toml` ([tool.ruff], [tool.black], [tool.isort], [tool.mypy]) + dev deps (ruff, black, isort, mypy, pytest, httpx, pytest-asyncio).
- Added ESLint to `ui/package.json` + `ui/.eslintrc.json` (Astro + TypeScript).
- Created `api/tests/` pytest skeleton: conftest.py (SQLite in-memory + DI override) + test_health.py, test_auth.py, test_users.py (9 tests covering auth contracts + CRUD).
- Updated `Makefile`: `make lint` (ruff+mypy), `make fmt` (black+isort), `make fmt-check` (exit 1 on drift), `make pytest`, `make lint-ui`.
