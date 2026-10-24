# Research: Process Management

**Feature**: `009-process-management` · **Date**: 2026-10-23 · **Spec**: [spec.md](spec.md)

The spec has no open clarifications. The decisions below settle the design questions the spec leaves to planning.

---

## R1 — Owning API domain: promote the `workflows` stub

- **Decision**: processes live in `api/app/workflows/` (routes in `routes/`, models and services in `internal/`). The public URLs are `/api/processes/...`.
- **Rationale**: the Constitution (Principle I) lists `workflows` as the stub domain for this area, and `api/app/workflows/internal/models.py` already reads *"Models for Processes module"*. Promoting it adds no new domain, so no Constitution amendment is needed.
- **Alternatives considered**: a new `api/app/proc` domain, as `docs/user-stories/07-proc.md` says. Rejected: it would add an eleventh domain next to an empty one meant for the same thing and require an amendment. The user-story doc gets its `api/app/proc` reference corrected to `api/app/workflows` in this feature.

## R2 — Schema changes in place, no migration

- **Decision**: edit `db/sql/71-proc-ddl.sql` and `db/sql/72-proc-insert.sql` directly:
  - `process_assets` and `process_inits` gain `type VARCHAR(100) NOT NULL` (→ `RELATION_TYPE`), and it joins their primary keys: `(process, asset, type)` and `(process, init, type)`.
  - A new list, `PROCESS_RELATION_TYPE` (seven values, `en` + `es`), is defined in `71-proc-ddl.sql`. The comment on `related_processes.type` points to it.
  - The seed rewrites the related processes (R13) and gives every process–asset and process–initiative link a type.
- **Rationale**: the user's explicit decision. The product has not reached production, and this matches the precedent of SpecKit 003, which was seed-only with no migration.
- **Consequence**: an existing local database must be recreated with `make rebuild`. No `provisioned-db.sql` is produced. Rollback means reverting the two files and running `make rebuild`. This is recorded in Complexity Tracking, because the Constitution asks for additive, migration-driven changes.

## R3 — Link writes: one atomic "replace the set" call per tab

- **Decision**: each Related tab saves through one call that sends the tab's full desired set: `PUT /api/processes/{code}/relations`, `.../assets` and `.../inits`. The server diffs that set against the stored links in **one transaction**:
  - A stored active link missing from the set is deactivated (`is_active = false`).
  - An identical inactive row is reactivated.
  - A new link is inserted.
  - A link whose rationale changed is updated.
  - Any validation failure rolls back the whole tab.
- **Rationale**: the spec saves per tab, so the tab is the natural transaction unit (FR-011, SC-006). It avoids the per-link create / 409 / reactivate sequence Asset Management runs from the browser, where a failure halfway leaves the tab partly saved.
- **Alternatives considered**: per-link CRUD routes mirroring `asset_relations`/`asset_inits`. Rejected: more endpoints and not atomic. The **UI** behaviour is still identical to Asset Management (staging, dot, inline messages); only the wire format differs.

## R4 — Create is all-or-nothing

- **Decision**: `POST /api/processes/` accepts the core fields plus optional `relations`, `assets` and `inits` arrays. The process and all its links are written in one transaction.
- **Rationale**: FR-010 and US5 scenario 2 require that no link is created if the process is not. There is a precedent: Propose Initiative writes the initiative and its links in one transaction (SpecKit 005, FR-021).

## R5 — Status lifecycle in a dedicated service

- **Decision**: a new module, `workflows/internal/status_service.py`, mirrors `insights/internal/status_service.py`:
  - `TRANSITIONS = {DRAFT: {REVIEW}, REVIEW: {PUBLISHED, DRAFT}, PUBLISHED: {DEPRECATED}, DEPRECATED: set()}`.
  - It provides `validate_create_status` (only DRAFT or omitted), `validate_transition` and `allowed_statuses_for`.
  - `GET /api/processes/{code}` returns `allowed_statuses` (the current status first), so the form never re-derives the rule (FR-008).
  - A process that keeps its current status is not a transition.
- **Rationale**: one owner for the rule. This is the same shape as Dashboard and Initiative Management.

## R6 — Relation rules in one module, published to the UI

- **Decision**: `workflows/internal/relation_rules.py` owns every rule about process links:
  - **Self-relation**: refused.
  - **Uniqueness**: per `(source, target, type)`. For `INTERACTS_WITH` the pair is unordered, so `(A, B)` and `(B, A)` collide.
  - **Compatibility (FR-013b)**: `SUPPORTS` is accepted only from a Support process to a Primary one; `PRECEDES` only between two processes of the same type.
  - **Type-change guard**: changing a process's type is refused while active `SUPPORTS` or `PRECEDES` links would become incompatible. The message lists those links.
- The same rules are exposed as data in `GET /api/processes/form-options` → `relation_rules`, for example `{"SUPPORTS": {"source": ["SUPPORT"], "target": ["PRIMARY"]}, "PRECEDES": {"same_type": true}}`. The target picker filters with that data rather than hard-coding the rule.
- **Rationale**: the server is the authority (FR-013b). Publishing the rule as data keeps a single definition and avoids drift between picker and server.

## R7 — Parent hierarchy check

- **Decision**: on create or update with a parent, load `(code, parent)` for all processes in **one query** and walk up from the proposed parent. If the walk reaches the process itself, the change is refused with a 400. The parent must be an active process. A step cap equal to the row count stops the walk on corrupt data.
- **Rationale**: process counts are in the tens to hundreds, so one projected query plus an in-memory walk avoids recursive SQL. That keeps the suites on SQLite and has no N+1 queries (Principle V).

## R8 — Form data from one PROC-gated endpoint

- **Decision**: `GET /api/processes/form-options` (gated by `PROC/PROCESSES`, read) returns everything the dialog needs in one call:
  - `processes`: active processes as code, name and type, for the parent picker and Related processes.
  - `units`: active business units.
  - `owners`: active users.
  - `assets`: active assets as id, name and category.
  - `initiatives`: active initiatives as id and name.
  - `relation_rules` (R6).
  - `can_edit`: whether the caller holds the edit right.
- List values (PROCESS_TYPE, PROCESS_STATUS, PROCESS_RELATION_TYPE, RELATION_TYPE) come from the existing `/api/list_items/list/{code}`, which is open to any authenticated user.
- **Rationale**: `GET /api/business_units/select` needs `ADMIN/BUSINESS_UNITS`, and the asset and initiative selects need LIB and INITS privileges. Process Management must not depend on another module's privileges. There is a precedent: `GET /api/dashboards/parameter-lists` (SpecKit 006) was added for the same reason. The payload holds names only, never content.

## R9 — Access by module privilege only

- **Decision**: every route uses `require_privilege("PROC", "PROCESSES", can_edit=…)`: read for GETs, edit for writes. There is no per-process grant table, and `owner` is informational.
- **Rationale**: this is the spec's assumption. The Constitution's per-resource permission pattern applies only when per-record access control is needed, and it is not needed here. Administrator and Administrative already hold the privilege with edit rights. Superusers bypass the check as everywhere else.
- A read-only holder gets `can_edit = false` from form-options. The page then hides *New Process*, the save buttons, the remove action and the add rows, and the dialog opens read-only.

## R10 — UI: a shared `RelatedLinksTab.svelte`

- **Decision**: build one generic Svelte component, `RelatedLinksTab.svelte`. Its markup, classes, staging, inline messages and pending-changes behaviour are taken from `AssetDetailTabs.svelte`'s Related Assets tab.
  - Its props: target options, relation-type options, an optional target filter (driven by `relation_rules`), an i18n prefix and `readonly`.
  - It exposes `hydrate`, `staged` (the desired set), `dirty` and `reset`.
  - `ProcessDetailTabs.svelte` mounts it three times: Related processes, Related assets, Related inits.
- **Rationale**: SC-003 requires identical controls, and one component guarantees the three process tabs match each other. The precedent is `PermissionsTab.svelte`, extracted in SpecKit 006.
- **Not done now**: switching `AssetDetailTabs.svelte`'s own two Related tabs to the new component. That file's save path is shared with versioning and create mode, and the repo has no browser tests, so the refactor is left as a follow-up rather than risked here.

## R11 — List page and the 100-row default

- **Decision**: `/proc/processes` uses the shared `DataTable`, filtering and searching on the client.
  - It loads with `limit=500`; the server caps `limit` at 500.
  - Columns (revised by the user after implementation): code, name (`as: "title"`, no subtitle), type, owner, status, tags and actions.
  - Filters: type and status (header funnels) and unit (toolbar, over a hidden column).
- **Rationale**: this avoids the known 100-row truncation (MEMORY "Known blockers") with a bound that is ample for a process inventory (about 45 seeded processes) and keeps pagination explicit (Principle II).

## R12 — Code identity

- **Decision**: the code is trimmed and uppercased, and must match `^[A-Z0-9][A-Z0-9_-]{0,49}$` (seed codes such as `INFR-GOVERNA` comply). It is immutable after creation: `ProcessUpdate` has no `code` key. A duplicate code is a 409, even when the existing process is logically removed, because codes are primary keys and are never reused.
- **Rationale**: the code is the foreign key target of four tables and the URL key.

## R13 — Seed rewrite

- **Decision**:
  - **Primary chain**: `DEPENDS_ON` rows become `PRECEDES` with the direction reversed, as INBL → OPER, OPER → OUTL, OUTL → MKTS and MKTS → SERV. All are Primary–Primary, so compatible.
  - **Support rows**: `USED_BY` rows become `SUPPORTS`, as TECH → OPER, PROC → INBL, HRMG → OPER and INFR → SERV. All are Support → Primary, so compatible.
  - **Asset and initiative links**: every `process_assets` and `process_inits` row gets `RELATED_TO`. No rationale points to a more specific type.
- Seeded processes stay Published.

## R14 — Labels and i18n

- **Decision**:
  - `menu_options.processes` changes from "Process Catalog" / "Catálogo de Procesos" to "Process Management" / "Gestión de Procesos", matching the seeded option name (as SpecKit 006 did for dashboards).
  - New key namespaces in `en.json` and `es.json`: `process_table.*`, `process_modal.*`, `process_detail_modal.*` and `related_links.*`, the last shared by the new component.
  - The PROCESS_RELATION_TYPE labels come from `list_items` (`en` and `es`), shown through `lib/listLang.ts`.

## R15 — Tests

- **Decision**: backend suites on the existing SQLite fixtures, with helpers in `api/tests/proc_helpers.py` modelled on `ana_helpers.py`. Suites:
  - `test_proc_processes.py`: CRUD, code rules, parent cycle, removal with children, pagination and filters.
  - `test_proc_status.py`: create status and every allowed and refused move.
  - `test_proc_relations.py`: replace semantics, self, duplicate, unordered INTERACTS_WITH, compatibility, type-change guard, reactivation, the PROCESS_RELATION_TYPE list enforced, atomic rollback.
  - `test_proc_links.py`: assets and initiatives replace, typed uniqueness, inactive targets refused.
  - `test_proc_access.py`: 401, 403 for read-only on writes, 403 for profiles without the privilege, form-options gating.
- **Rationale**: Principle III. These are new contract and permission surfaces, so automated tests are required. The UI is verified manually through `quickstart.md`.
