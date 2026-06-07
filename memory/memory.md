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
| 2026-06-07 | Added `ui/src/layouts/Layout.astro` (minimal shell) | `dashboard.astro` used a standalone full-screen design, not the sidebar BaseLayout; the file was simply missing. |
| 2026-06-07 | Hardened `@` alias to `fileURLToPath(new URL('./src', import.meta.url))` | Literal `/src` is filesystem-absolute and breaks Vercel builds. |
| 2026-06-07 | Created `AGENTS.md` per project + root, thin `CLAUDE.md` pointers | AI tools need a curated single entry point; Constitution and patterns were undiscoverable. |
| 2026-05-XX | `catalog` module renamed to `taxo` | Better reflects digital asset taxonomy purpose. |
| 2026-04-XX | `roles` renamed to `profiles` in admin | Profiles better represents the concept; roles concept retained for collab assignments. |
| 2026-04-XX | Master-detail pattern for dimensions → metrics | Mirrors admin roles → privileges pattern for consistency. |

---

## Known issues / next up

- **Vercel build: API fetch at build time** — static pages in `ui/` call `localhost:8000` during `astro build`. On Vercel this errors (`ECONNREFUSED`). Needs one of: (a) `PUBLIC_API_BASE_URL` env var pointed at deployed API, (b) client-side fetch instead of build-time, or (c) SSR output mode.
- `genai`, `inits`, `insights` modules are domain stubs — not yet implemented.
- No automated UI tests; manual verification per quickstart guides only.
- caniuse-lite is stale — run `npx update-browserslist-db@latest` in `ui/`.

---

## Session history (AI-assisted work)

### 2026-06-07 — Session (claude-opus-4-8)
- Explored and documented repo: created `AGENTS.md` (root + api, ui, db) and `CLAUDE.md` pointers.
- Fixed Vercel build failure: added missing `ui/src/layouts/Layout.astro` and fixed `@` alias.
- Created `memory/changelog.md`, `memory/memory.md`, and changelog automation hook.
