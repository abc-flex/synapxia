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
| 2026-06-26 | **Shared `FavoritesPill`; DataTable filter slots accept an `aria-pressed` `<button>`; curated galleries are published-only with a Propose CTA.** The "★ favorites" filter is now **one** component — `components/lib/FavoritesPill.astro`, an `aria-pressed` toggle whose active styling comes from Tailwind's built-in **`aria-pressed:` variant** (no JS class-juggling) — reused by both `CardGallery` and the assets `DataTableFilters` (`asToggle` branch, replacing the switch). This extends the 2026-06-25 "element-type-aware slots": `advancedTable.ts` `slotValue`/`setSlotValue` now also read/clear a button's `aria-pressed`, and a new `bindFilterControl(el, param)` binds **`click`** for toggle buttons / **`change`** for selects+checkboxes, and on a header-funnel `<select>` change closes its `<details>` (plus a document outside-click closer). Galleries `/lib/{prompts,mcps,agents}` are **published-only** (filter rows to `PUBLISHED`, pass `statuses={[]}` so `CardGallery` hides the status `<select>`) and carry a primary **Propose** CTA → `/lib/propose?category=<CODE>` (propose page preselects from `?category=`). The toolbar **Reset** button moved to the left group + went discreet (borderless/muted). | One favorites control everywhere (user: "reuse the favorites button … in all pages"); galleries are browse-only published surfaces but still need a contribution entry point. **Gotcha (recorded):** `DataTable.astro` must run `initAdvancedTable` **once** — via the bundled JSON-config `<script>`. A leftover literal-`/src/...` `type="module"` import double-bound every handler in dev (Export toggle fired twice → menu never opened) and 404'd in the Vercel build; it was deleted. UI-only, no backend/DDL. |
| 2026-06-26 | **LIB curated catalogs (Prompt/MCP/Agent) are view-only; their detail modal is tabbed.** The shared read-only `CatalogDetailModal` body is split into **Details / Discussion / Activity** tabs (`data-detail-tab`/`data-detail-panel`, wired in `catalogDetail.ts`; Related sits under Details). The cards (`PromptCard`/`McpCard`; `AgentCard` already had none) and the modal footer drop **Edit/Delete**, and the gallery pages drop the **New** button + create/edit `FormModal` + delete `CrudModal`. Editing/removing assets is now **only** on `/lib/assets` (DataTable + `AssetDetailModal`) and creation via the Propose flow. The foro discussion is minimalist: composer at the bottom, per-question **Answer** is a link that reveals an inline box. On `/lib/assets` the row **detail** button now opens `AssetDetailModal` with `data-asset-section="detail"` (its Chars/Related/Permissions tabs) instead of an inline expanded `<tr>`. | User wanted the specific-catalog pages to be browse-only reference surfaces with a cleaner, tabbed detail view, and the assets-repo detail to open as a modal (consistent with the catalog detail) rather than collapsing on the row. Reuses the existing `assetDetailTabs` modal mode + all `data-foro-*` hooks — UI-only, no backend/DDL. |
| 2026-06-25 | **DataTable column filters can render inline in a column header (funnel) or as a toggle** — opt-in `filterNHeaderColumn` / `filterNAsToggle` props on `DataTable.astro`; slots are built once via `buildFilterConfigs` (`lib/datatable.ts`) and shared by `DataTableHead` (funnel `<details>` hosting the same `<select>` id/`data-column-key`) and `DataTableFilters` (toolbar). `advancedTable.ts` binds by id so placement is free, and is now element-type-aware (reads a `<select>` value OR a checkbox's `data-on-value`). Also surfaced **per-user asset permission scopes**: `permissions_service.assets_user_scopes` + a `permission_scopes` field on `/api/assets/with-access` feed the assets "Privileges/Permisos" membership filter (USER/ROLE/TEAM/UNIT/PROJECT/PUBLIC, matched against the user's unit + active collab assignments/projects). First adopter: `/lib/assets` (Category/Status → header funnels, Favorites → toggle, Privileges → toolbar). | Declutter the asset toolbar and put per-column filters on their columns, reusably (DataTable is shared by ~18 pages — all unchanged when the new props are unset). The permissions filter answers "what can I access?" by scope, not access-level. Note: `/with-access` uses Postgres-only `array_agg`/`bool_or`, so its query is Postgres-verified while the scope logic is unit-tested on SQLite. |
| 2026-06-24 | **Don't share the API virtualenv between host and container.** `docker-compose.yml` bind-mounts `./api:/app`; an anonymous `- /app/.venv` volume now keeps the image-built venv (correct arch) from being shadowed by the host's `./api/.venv`. Also fixed `make pytest` to run `uv run pytest` (the venv bin isn't on the container `PATH`). Python stays pinned at **3.14** per team direction. | The API was crashing on boot with `ModuleNotFoundError: No module named 'pydantic_core._pydantic_core'`. Root cause was **not** a missing wheel — it was a stale **x86_64** host `./api/.venv` (built earlier under emulation) bind-mounted over the container's correct **aarch64** venv (`SOABI cpython-314-aarch64-linux-gnu`), so the arch-tagged `.so` didn't match. cp314 arm64 wheels exist and the image builds a working venv. |
| 2026-06-24 | **Asset interactions ride the generic `actions` table — never a new table.** Votes = `actions` `type=VOTE`, `content` POSITIVE/NEGATIVE, one active row per (user, asset); comments/questions/answers (future) = `type` COMMENT/QUESTION/ANSWER threaded via `parent`; history = read over `actions`; notifications = `actions` where `workflow_status` ASSIGNED/NOTIFIED. Backend logic centralizes in **`api/app/lib/internal/actions_service.py`** (Asset Action Service); frontend in `ui/src/lib/actions.ts` + a vote bar on the shared `GalleryCard`/`CatalogDetailModal`. Also mapped the existing `workflow_status` DDL column onto the `Action` model (additive, was missing). | All `ACTION_TYPE` values are already seeded; the `actions` table has every needed column (`type`/`workflow_status`/`content`/`parent`). One substrate + one service avoids per-feature tables/duplication and is the foundation for the lib roadmap (foro/history/notifications). Per the project user-story spreadsheet this is HU-LI05 "Vote"; `docs/user-stories/04-lib.md` numbers it HU-LI07 (different numbering, left uncorrected). |
| 2026-06-18 | Characterization **`value` vs `detail`**: short fields (PLATFORM/MODE/MODEL/TEMP/OVERVIEW) keep their payload in `value`; **rich** fields (PROMPT_TEMPLATE/EXAMPLE_OUTPUT/TOOLS/CONTENT/SERVER_CONFIG/INSTRUCTIONS) keep it in `detail` (with `value` as a short summary), matching the seed. `mountCatalogModal` `features` accept `{ name, column }`; cards/detail-view read the right column. | Reading `value` everywhere showed summaries instead of the real content (e.g. MCP tool chips rendered the sentence "List of tools…"). |
| 2026-06-18 | Reusable **read-only "big card" detail view**: `gallery/CatalogDetailModal.astro` + `lib/catalogDetail.ts` `mountCatalogDetail({ modalId, editModalId, sections })`. Card click opens it via the card's **`data-detail-modal`** (GalleryCard `detailModalId`); `catalogGallery.ts` prefers it over the edit modal. Sections are `inline`/`block`/`code`(+Copy)/`tools`. Also: `GalleryCard` opt-in **`hero`** gradient header (`heroClass`), `CatalogFormModal` `hideDetailsHeading` (grouped forms), `CardGallery` grid widened to `auto-fill minmax(360px,1fr)`. | User wanted to click a card and read full descriptions/instructions "like a big picture"; built once, used by Prompt/MCP/Agent. **HU-LI15–19 recipe addition:** add `{X}DetailModal.astro` (wrap `CatalogDetailModal` + `mountCatalogDetail` with that category's sections) and set the card's `detailModalId`. |
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
| Asset voting (HU-LI05) — `actions` `type=VOTE` (POSITIVE/NEGATIVE toggle) + **Asset Action Service** | lib | ✅ done |
| Asset foro (HU-LI06) — comments/questions/answers as `actions` (COMMENT/QUESTION/ANSWER, answers threaded via `parent`); discussion section on the gallery detail modal | lib | ✅ done |
| Related assets (HU-LI07) — read-only "Related" section on the gallery detail modal (both directions, de-duped) over the existing `related_assets` table; reverse + resolved routes (`/target/{id}`, `/related/{id}`) | lib | ✅ done |
| Asset history (HU-LI10) — read-only activity timeline on the gallery detail modal (creation marker + votes/comments/Q&A/workflow actions, newest first) over `actions`; `get_asset_history` + `GET /api/actions/history/asset/{id}` | lib | ✅ done |
| Workflow notifications (HU-LI11) — header bell lists the user's open assignments (REVIEW/MODIFICATION/PUBLICATION/REJECTION) as latest-status `actions` threads (ASSIGNED bold → NOTIFIED dismissible → FINISHED gone); `list_notifications`/`mark_notified`/`dismiss_notification` + `/api/actions/notifications*`. **Display/transition only** — the review workflow that *generates* assignments is not built yet. | lib | ✅ done |
| Propose an asset (HU-Propose) — review-workflow entry point: transactional `propose_asset` inserts asset (PROPOSED) + characterizations (from category specs) + PROPOSAL/FINISHED + REVIEW/ASSIGNED (reviewer) + MANAGE permissions; `POST /api/assets/propose` + `GET /api/assets/reviewers` + `/lib/propose` page. **This generates the REVIEW assignment that HU-LI11 notifications surface.** Downstream HU-Review/HU-Modify still pending. | lib | ✅ done |
| Prompt Gallery (HU-LI12) — final-user card gallery on the reusable gallery framework | lib | ✅ done |
| MCP Directory (HU-LI13) — second card catalog (Mode chip, tool chips, Copy-config) | lib | ✅ done |
| Agent Index (HU-LI14) — third catalog; first **hero card** + uses the reusable big detail view | lib | ✅ done |
| Curated catalogs HU-LI15–19 (Flow/Skill/Assistant/RAG/Model) — framework ready, pages pending | lib | ⬜ pending (use the gallery extension recipe) |
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
| P1 | DataTable list pages truncate at 100 rows | ~18 admin/collab/taxo pages fetch their main list with the default `limit=100` (`getX()` with no args), then `DataTable`/`advancedTable` do **all** filter/paginate/search/export **client-side** over only those 100 rows. Tables >100 rows silently lose data and "Showing X of Y" lies. First hit: `list_items` (203 rows) showed 2 of 5 `GENAI_DEV_ADOPTION/en` values — patched ad-hoc with `getListItems(0,1000)` in `ui/src/pages/admin/list_items.astro`. `/select` endpoints are unbounded, so dropdowns are safe. **Proposed transversal fix (not yet done):** _Nivel 1_ — add `apiGetAll<T>(route, pageSize=200)` to `ui/src/lib/api.ts` that auto-paginates `skip/limit` until exhausted (cap ~10k), expose `getAllX()` per `lib/{entity}.ts`, migrate the list pages; keeps client UX + bounded per-request pagination. _Nivel 2_ (only for tables that grow: metrics/assets/actions) — server-side filter via query param (`/api/metrics?dimension=X`; `list_items` already has `/list/{code}`). _Nivel 3_ — server-driven `DataTable` (fetch on filter/page change); big refactor, defer until volume warrants. |
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
