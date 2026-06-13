# Changelog

Append-only project log. Newest entries at the top.

**Every important group of changes gets an entry** — every PR, every merge commit, and every direct push to `develop` / `main` / `production`. A direct push is not exempt just because there is no PR; it is still a change set that needs to be logged, before or alongside the push.

**One PR / merge / direct-push = one entry.** Don't append per individual commit. If you commit again on the same branch (review fixups, follow-ups), **update the entry you already added on that branch** instead of appending a new one. Never edit entries from *other* PRs.

Format (note the **time** — needed so same-day entries stay ordered and traceable):

```
## YYYY-MM-DD HH:MM — Short descriptive title
- What changed and why (1–3 bullets).
- Files affected: `path/to/file.ts`
```

Use 24-hour local time (Colombia/America for this team). Agents: if you don't have the current time loaded, run `date '+%Y-%m-%d %H:%M'`.

Historical entries below (before the switchover) use a Keep-a-Changelog–style auto-generated format from the old git-hook flow. They are kept as-is for traceability; new entries follow the format above.

---

## 2026-06-13 18:07 — Tabbed asset modal (Details + Related Assets) + relation/favorite API fixes

- Restructured the asset create/edit modal into two tabs — **Details** (existing core fields + dynamic characterizations) and **Related Assets** (compose/list/remove relations where the asset is the source: target asset + RELATION_TYPE + optional rationale) — plus a **favorite star** in the header (per-user; immediate optimistic toggle on edit, staged on create). One form + one Save: panels hide via CSS so all inputs stay in form submission, and a capture-phase `invalid` handler flips to the owning tab so native validation can focus a hidden-tab field. Create mode stages relations + favorite in memory and persists them after the asset id exists; edit mode diffs staged-vs-initial (delete-first, then create with 409→PUT reactivation fallback, then update changed type/rationale).
- **API model bug fixes (were unusable):** `AssetRelation` now maps to the real `related_assets` table with `source`/`target` as `BigInteger` FKs to `assets.id` (previously `str` FKs to a non-existent `assets.code`) and includes the `rationale` column the DB already had; `Favorite` now maps to `favorite_assets` with `asset` as a BigInteger FK to `assets.id`. Mirrors the earlier Characterization `asset: str→int` fix.
- **New endpoints (additive):** `GET /api/asset_relations/source/{asset_id}` (relations by source, registered before the composite route) and `GET /api/assets/select` (`{value,label}` for the target-asset dropdown). Relation/favorite routes switched to int path params and their privilege gate moved from the never-seeded `ASSET_RELATIONS`/`FAVORITES` options to the seeded `(LIB, ASSETS)` — non-superusers were getting 403 before.
- New UI services `lib/asset_relations.ts` + `lib/favorites.ts` (with `setFavorite`/`isFavorite` helpers handling the 404/400/409 soft-delete edge cases), `getAssetsSelect()` in `lib/assets.ts`, six new types in `types/api.ts`, and 17 new `asset_detail_modal.*` i18n keys in en + es.
- Files affected: `api/app/lib/internal/models.py`, `api/app/lib/routes/asset_relations.py`, `api/app/lib/routes/favorites.py`, `api/app/lib/routes/assets.py`, `ui/src/components/lib/AssetDetailModal.astro`, `ui/src/lib/asset_relations.ts`, `ui/src/lib/favorites.ts`, `ui/src/lib/assets.ts`, `ui/src/types/api.ts`, `ui/src/i18n/en.json`, `ui/src/i18n/es.json`

---

## 2026-06-10 01:58 — Adopt human-written CHANGELOG flow (mirror safe-transfers)

- Dropped the `.githooks/post-commit` + `.githooks/post-merge` + `.claude/hooks/update-changelog.sh` automation. From now on, Claude (and humans) write **one entry per PR / merge / direct push** here by hand, before or alongside the change — the rule is documented in `AGENTS.md` "Mandatory update rules" and reminded in `CLAUDE.md` (which `@`-imports both `AGENTS.md` and `memory/MEMORY.md` so every session loads them).
- Format change: switched from Keep-a-Changelog `### Added / Changed / Fixed` blocks driven by commit subjects to a hand-written `## YYYY-MM-DD HH:MM — Title` block with 1–3 narrative bullets and an explicit `Files affected:` list. Historical entries below this one are preserved unchanged.
- Each clone that previously ran `make hooks` needs `git config --unset core.hooksPath` once to stop pointing at the (now-deleted) `.githooks/` dir; the `hooks` Make target is removed.
- Files affected: `memory/CHANGELOG.md`, `AGENTS.md`, `CLAUDE.md`, `Makefile`, `.githooks/post-commit` (deleted), `.githooks/post-merge` (deleted), `.claude/hooks/update-changelog.sh` (deleted).

---

## [develop] — 2026-06-10 01:27 · 7016f33

### Added
- `e06680d` unify database URL resolution and update environment variable d… (#42)
- `58e00a7` **(ui)** filter items from lists by the current language, or lang='en' in CrudModal form
- `3d00d54` update LanguageSwitcher component to include forceDropdown prop

### Changed
- `e2eba13` **(ui)** add filterLang: true to lists that are loaded with getListItemsbyList()
- `e7cbeae` **(ui)** default selected value for filters applied on page load
- `49a0869` refactor admin/list_items by add lang field
- `6733ca0` update dependencies and remove bun.lockb (#40)

### Other
- `7016f33` Ci/unify db url env var (#43)
- `e78a869` Style: lading page (#41)

---


## [develop] — 2026-06-10 00:54 · d4e20a6

### Added
- `58e00a7` **(ui)** filter items from lists by the current language, or lang='en' in CrudModal form
- `3d00d54` update LanguageSwitcher component to include forceDropdown prop

### Changed
- `e2eba13` **(ui)** add filterLang: true to lists that are loaded with getListItemsbyList()
- `e7cbeae` **(ui)** default selected value for filters applied on page load
- `49a0869` refactor admin/list_items by add lang field
- `6733ca0` update dependencies and remove bun.lockb (#40)

### Other
- `e78a869` Style: lading page (#41)

---


## [develop] — 2026-06-09 23:11 · e2eba13

### Added
- `3d00d54` update LanguageSwitcher component to include forceDropdown prop

### Changed
- `e2eba13` **(ui)** add filterLang: true to lists that are loaded with getListItemsbyList()

---


## [develop] — 2026-06-09 21:48 · 3d00d54

### Added
- `3d00d54` update LanguageSwitcher component to include forceDropdown prop

---


## [develop] — 2026-06-09 18:30 · e78a869

### Changed
- `e7cbeae` **(ui)** default selected value for filters applied on page load
- `49a0869` refactor admin/list_items by add lang field
- `6733ca0` update dependencies and remove bun.lockb (#40)
- `1d48800` Spec Kit updated

### Other
- `e78a869` Style: lading page (#41)

---


## [develop] — 2026-06-09 15:30 · 3f363eb

### Added
- `3f363eb` enhance UI components with new icons and update dashboard links

---


## [develop] — 2026-06-09 14:53 · 6733ca0

### Changed
- `6733ca0` update dependencies and remove bun.lockb (#40)
- `1d48800` Spec Kit updated

---


## [develop] — 2026-06-09 10:05 · bc1fd8d

### Changed
- `1d48800` Spec Kit updated

---


## [develop] — 2026-06-09 03:22 · f208526

### Added
- `f208526` update API endpoints to include trailing slashes for consistency

---


## [develop] — 2026-06-09 03:13 · 80a0612

### Added
- `80a0612` implement cookie-based authentication and role-based access con… (#38)
- `105cf3d` **(security)** implement role-based access control (RBAC) (#25)
- `94b3d98` enhance CORS configuration for improved security and local development
- `74224ea` update authentication flow to use bcrypt for password hashing and improve error handling

### Changed
- `3abefa3` **(ui)** add lib/assets crudel page

### Other
- `284b32a` Feat(lib): assets repository demo (#37)
- `3dcca27` Style: add icons for suboptions (#36)
- `7e2e1ce` Fix: translations (#35)
- `2f25f01` Chore!: secure apages (#34)
- `20ea1c9` Secure 16 unprotected endpoints with JWT auth and RBAC (#33)
- `5afd09a` Fix NameError on import and harden POSTGRES_URL handling (#32)
- `04da648` Fix Vercel build command: use uv pip install (#30)
- `c68e779` Sync requirements.txt with pyproject.toml (#29)
- `e513b5b` Fix Vercel Python runtime import error: use uv pip sync instead of uv sync (#28)
- `9ad746e` Fix Vercel build configuration for uv package manager (#27)
- `f43a486` changelog automation support for production branch (#26)
- `9da629d` Fix database connection error in docker-compose (#23)

---


## [develop] — 2026-06-09 02:17 · 284b32a

### Added
- `105cf3d` **(security)** implement role-based access control (RBAC) (#25)
- `94b3d98` enhance CORS configuration for improved security and local development
- `74224ea` update authentication flow to use bcrypt for password hashing and improve error handling

### Changed
- `3abefa3` **(ui)** add lib/assets crudel page

### Other
- `284b32a` Feat(lib): assets repository demo (#37)
- `3dcca27` Style: add icons for suboptions (#36)
- `7e2e1ce` Fix: translations (#35)
- `2f25f01` Chore!: secure apages (#34)
- `20ea1c9` Secure 16 unprotected endpoints with JWT auth and RBAC (#33)
- `5afd09a` Fix NameError on import and harden POSTGRES_URL handling (#32)
- `04da648` Fix Vercel build command: use uv pip install (#30)
- `c68e779` Sync requirements.txt with pyproject.toml (#29)
- `e513b5b` Fix Vercel Python runtime import error: use uv pip sync instead of uv sync (#28)
- `9ad746e` Fix Vercel build configuration for uv package manager (#27)
- `f43a486` changelog automation support for production branch (#26)
- `9da629d` Fix database connection error in docker-compose (#23)

---


## [develop] — 2026-06-09 01:15 · 3dcca27

### Added
- `105cf3d` **(security)** implement role-based access control (RBAC) (#25)
- `94b3d98` enhance CORS configuration for improved security and local development
- `74224ea` update authentication flow to use bcrypt for password hashing and improve error handling

### Changed
- `3abefa3` **(ui)** add lib/assets crudel page

### Other
- `3dcca27` Style: add icons for suboptions (#36)
- `7e2e1ce` Fix: translations (#35)
- `2f25f01` Chore!: secure apages (#34)
- `20ea1c9` Secure 16 unprotected endpoints with JWT auth and RBAC (#33)
- `5afd09a` Fix NameError on import and harden POSTGRES_URL handling (#32)
- `04da648` Fix Vercel build command: use uv pip install (#30)
- `c68e779` Sync requirements.txt with pyproject.toml (#29)
- `e513b5b` Fix Vercel Python runtime import error: use uv pip sync instead of uv sync (#28)
- `9ad746e` Fix Vercel build configuration for uv package manager (#27)
- `f43a486` changelog automation support for production branch (#26)
- `9da629d` Fix database connection error in docker-compose (#23)

---


## [develop] — 2026-06-08 22:03 · 20ea1c9

### Other
- `20ea1c9` Secure 16 unprotected endpoints with JWT auth and RBAC (#33)

---


## 2026-06-08 14:30 — Fix changelog automation for renamed production branch
- Updated git hooks to recognize `production` as a principal branch after branch rename from `prod`
- Post-merge hook now triggers changelog updates on develop, main, and production branches
- Changelog header updated to reflect correct branch name
- Files affected: `.githooks/post-merge`, `.claude/hooks/update-changelog.sh`, `memory/changelog.md`

---

## [Unreleased] — claude/security-implementation-auth-rbac

### Security
- **PR #25**: Comprehensive security implementation with JWT authentication + role-based access control (RBAC).
  - Secured 81 unprotected API endpoints across all modules (ADMIN, TAXO, LIB, COLLAB).
  - Added privilege matrix enforcement: all endpoints check user profile against `privileges` table.
  - Superuser bypass: `is_superuser=True` skips privilege checks.
  - All GET operations require read privilege (`can_edit=False`); POST/PUT/DELETE require write privilege (`can_edit=True`).
  - Returns 401 Unauthorized (missing token) or 403 Forbidden (insufficient privileges).

### Backend (API)
- `api/app/internal/permissions.py` — New permission service with `check_privilege()` dependency.
- Updated 22 route files to add auth + RBAC:
  - Admin: `profiles`, `modules`, `options`, `privileges`, `business_units`, `lists`, `list_items`, `item_translations`
  - Taxo: `categories`, `features`, `specifications`
  - Lib: `assets`, `characterizations`, `favorites`, `actions`, `asset_relations`
  - Collab: `teams`, `roles`, `assignments`, `projects`, `dimensions`, `metrics`
- Fixed `docker-compose.yml` line 70: `DATABASE_URL` hostname corrected from `postgres` to `db`.

### Frontend (UI)
- `ui/src/middleware.ts` — New Astro middleware protecting all routes except `/login`, `/signup`, `/`.
  - Unauthenticated users redirected to `/login`.
  - Static assets and API routes exempt from guard.
- `ui/src/lib/api.ts` — Enhanced error handling:
  - 401/403 errors trigger auto-logout (clear token).
  - Redirect to `/login` on auth failures.
  - Applied to `apiGet`, `apiPost`, `apiPut`, `apiDelete`.
- `ui/src/pages/login.astro` — Refactored login page with security + UX improvements:
  - Rate limiting: 5 failed attempts = 15-minute lockout.
  - Specific error messages for auth failures, network errors, disabled accounts.
  - Field focus on validation errors.
  - Error auto-clears on input.
  - Attempt counter after 3 failures.
  - Screen reader support.

### Fixed
- `ui/src/layouts/Layout.astro` created — `dashboard.astro` imported a missing layout, breaking Vercel build.
- `ui/astro.config.mjs` — hardened `@` alias from literal `/src` to `fileURLToPath(new URL('./src', import.meta.url))` for reliable resolution at build time.

### Docs
- Added root `AGENTS.md` — canonical AI coding guide covering the 5 Constitution principles, architecture, conventions, patterns, and pre-PR checklist.
- Added root `CLAUDE.md` — thin pointer to `AGENTS.md` with everyday commands; updated with security implementation note.
- Added `api/AGENTS.md`, `ui/AGENTS.md`, `db/AGENTS.md` — project-specific agent guidance (stack, structure, commands, rules).
- Added `api/CLAUDE.md`, `ui/CLAUDE.md`, `db/CLAUDE.md` — slim pointers to their sibling AGENTS.md.
- Updated `vercel.env.example` with security warnings and critical variable documentation.

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
