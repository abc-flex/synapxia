# Research: Initiative Management

**Branch**: `004-initiative-management` | **Phase**: 0 | **Date**: 2026-09-23

The Technical Context had no open unknowns about the stack — the stack is fixed by the
Constitution. Every decision below is about **how to mirror Asset Management inside the `inits`
domain without duplicating plumbing** (Principle I), given what exists today. The baseline was
mapped before deciding:

- `inits` is read-only: `Initiative` model + `GET /api/initiatives/{select,/,{id}}`; no
  Create/Update model. `Criteria` has full CRUD.
- `diagnostics`, `collaborations`, `init_permissions`, `favorite_inits` exist in DDL + seed but
  have **no model and no route**.
- `asset_inits` is modelled and routed in `lib` (`AssetInit`, `/api/asset_inits`), asset-side
  only; model PK is `(asset, init)` while the DDL PK is `(asset, init, type)`.
- The per-resource permission engine (`lib/internal/permissions_service.py`) is ~90 % generic
  but hard-wired to `AssetPermission` and its `.asset` column.
- The status policy (`lib/internal/status_service.py`) is hard-wired to `Action` + asset
  constants.
- UI: `/inits/initiatives` 404s (no page); `AssetDetailTabs.svelte` (1522 lines) is heavily
  asset-specific; `lib/foro.ts` and `lib/history.ts` hard-code asset endpoints and the
  `data-asset-id` opener attribute.
- Seed: initiative `status` values (`1-ACTIVATED`, `2-ASSESSMENT`, `3-ENGAGING`,
  `4-DELIVERED`) are not in `INITIATIVE_STATUS`; `INITIATIVE_STATUS`, `COLLAB_TYPE`,
  `EXPECTED_IMPACT`, `PRIORITY_LEVEL`, `INITIATIVE_TYPE` have `en` rows only.

---

## R1 — Activity substrate: `collaborations`, not `actions`

- **Decision**: Record every initiative activity (Kickoff, Delivery, Archiving) and read every
  history/discussion entry from `collaborations`, through a new `Collaboration` SQLModel and a new
  `inits/internal/collaborations_service.py`. Extend the existing `COLLAB_TYPE` list with
  `KICKOFF` rather than adding any table.
- **Rationale**: User requirement (spec FR-029). Structurally forced as well: `actions.asset` is
  a `NOT NULL` FK to `assets`, so an initiative row cannot live there. `collaborations` already
  exists with the same shape (`type` + `workflow_status` + `content` + `parent`) and seed rows;
  it is the `inits` twin of the substrate, not a bespoke per-workflow table.
- **Constitution**: the "Contribution / approval workflows" pattern names `actions`; this is a
  documented deviation (see plan § Complexity Tracking). It keeps the pattern's *rules* — one
  substrate per domain, enum extended first, one service owning each transition in a single
  transaction.
- **Alternatives considered**: (a) make `actions.asset` nullable and add `actions.init` —
  rejected: widens every `lib` query and the user explicitly chose `collaborations`;
  (b) a generic "activity" table shared by both domains — rejected: a migration of shipped `lib`
  data for no user benefit.

## R2 — Status policy: a sibling `inits` status service, sharing the normalizer

- **Decision**: New `api/app/inits/internal/status_service.py` with
  `ALLOWED_TRANSITIONS: dict[(from, to), collab_type]`:
  `ACCEPTED→IN_PROGRESS: KICKOFF`, `ACCEPTED→DELIVERED: DELIVERY`,
  `ACCEPTED→ARCHIVED: ARCHIVING`, `IN_PROGRESS→DELIVERED: DELIVERY`,
  `IN_PROGRESS→ARCHIVED: ARCHIVING`, `DELIVERED→ARCHIVED: ARCHIVING`.
  Public API mirrors `lib`'s: `normalize`, `validate_transition(current, new) -> Optional[str]`
  (None = unchanged), `log_status_collaboration(session, init_id, user_id, type)` (adds a
  `HANDLED` row, never commits), `allowed_targets(current) -> list[str]` (feeds the UI).
  `StatusTransitionForbidden(ValueError)` so a route's existing 400 mapping applies. There is no
  `validate_create_status` — initiatives have no create path here.
- **Rationale**: The two maps, the two log models and the two domains differ; one parameterised
  engine for a six-entry dict would be more code than the thing it replaces. The only genuinely
  shared logic — stripping the legacy `N-` sort prefix — is small; `normalize` is lifted to
  `api/app/internal/status.py` and both services import it (keeps Principle I honest without a
  framework).
- **Concurrency** (spec edge case "two owners change the status concurrently"): the PUT loads the
  row with `with_for_update()` before validating, so the second request validates against the
  committed status. SQLite ignores the clause; the rule is still unit-tested sequentially.
- **Alternatives considered**: extending `lib/internal/status_service.py` with an entity switch —
  rejected: a `lib` module would import `inits` models, inverting the domain dependency.

## R3 — Per-resource permissions: extract the generic engine to `api/app/internal`

- **Decision**: Move the resource-agnostic parts of `lib/internal/permissions_service.py` into a
  new shared module `api/app/internal/resource_permissions.py`:
  `_as_naive_utc`, `is_valid_now`, `resolve_user_scopes`, and parameterised
  `not_revoked_clause(model)`, `is_revoked(grant)`, `matching_grants(session, user, model,
  fk_col, ids=None)`, `effective_levels(grants, fk_attr)`. The `lib` module keeps its **exact
  public API** as thin wrappers (`accessible_assets`, `require_asset_manage`, …) so no `lib`
  caller or test changes. A new `inits/internal/permissions_service.py` wraps the same engine
  over a new `InitPermission` model: `accessible_inits`, `inits_user_access`,
  `user_init_access`, `require_init_manage`, `require_init_view`, `InitAccessForbidden`.
- **Rationale**: Constitution Principle I explicitly prohibits duplicating permission plumbing,
  and the "Per-resource permissions" pattern requires `init_permissions` to behave identically
  (MANAGE/VIEW, validity window, revoke-not-delete, superuser bypass, RBAC as outer gate).
  `init_permissions` has the same columns as `asset_permissions` except the FK name, so the
  extraction is a parameter, not a redesign. `resolve_user_scopes` importing `collab` models from
  `app/internal` is acceptable: it is exactly the cross-domain dependency the shared layer exists
  for.
- **Safety net**: the existing `lib` suites (`test_lib_permissions.py`,
  `test_lib_access_enforcement.py`, `test_assets_access.py`,
  `test_assets_category_with_access.py`) must pass unchanged after the extraction — that is the
  refactor's acceptance test.
- **Alternatives considered**: (a) copy the service into `inits` — rejected (Principle I);
  (b) import `lib.internal.permissions_service` from `inits` — rejected: couples `inits` to
  asset internals and leaves the engine asset-bound.

## R4 — Initiative listing: `GET /api/initiatives/with-access`

- **Decision**: Mirror `GET /api/assets/with-access`: filter to accessible initiatives **before**
  `skip`/`limit`; return each `Initiative` plus `my_access` (`MANAGE`/`VIEW`, superuser =
  `MANAGE`) and `is_favorite`. Gate: `require_privilege("INITS","INITIATIVES")`. Favorites are
  joined server-side (one `IN` query over `favorite_inits` for the caller) rather than via a
  second client call as assets do, because no favorites route exists for initiatives and adding
  one only to join it client-side is more surface for no benefit.
- **Truncation** (known P1 blocker: DataTable pages truncate at 100): the page requests
  `limit=500`. Portfolio size is tens of initiatives; the value is bounded (Principle II) and
  documented. The generic `apiGetAll` fix stays out of scope.
- **Alternatives considered**: `permission_scopes` (assets' USER/ROLE/TEAM… filter) — dropped:
  the spec asks for an access-level filter, not a scope-membership filter.

## R5 — Editing core fields: `PUT /api/initiatives/{id}` + `DELETE /api/initiatives/{id}`

- **Decision**: New `InitiativeUpdate` (all optional: `name`, `description`, `type`,
  `expected_impact`, `priority_level`, `reference`, `tags`, `detail`, `status`). `score` is not
  editable (it is the diagnosis result). Order inside the handler, mirroring `assets.put`:
  404 → `require_init_manage` (403) → list-value validation for `type`/`expected_impact`/
  `priority_level` against `list_items` (400) → `validate_transition` (400) → apply, stamp
  `updated_at`, stage the collaboration, **one commit**. `DELETE` is a logical delete
  (`is_active=False`, 400 if already inactive), MANAGE-only, and records nothing (same as assets).
  Gate for both: `require_privilege("INITS","INITIATIVES", can_edit=True)`.
- **Rationale**: FR-012, FR-017 – FR-022, FR-007. Server-side list validation is new relative to
  assets but cheap and required because the UI is not a permission (Constitution III/IV).

## R6 — Diagnosis Questions: one read endpoint that returns labels

- **Decision**: `GET /api/initiatives/{id}/diagnostics?lang=es|en` returns **one row per
  criterion** — every active criterion plus any inactive criterion the initiative has an answer
  for — with `criteria`, `name`, `description`, `creator_score`, `reviewer_score`, `rationale`,
  and the resolved `creator_label` / `reviewer_label` from that criterion's own list in the
  requested language (falling back to `en`). Also returns the initiative `score`. Three queries
  total (criterias, diagnostics for the init, list_items for the involved lists) — no N+1. Gate:
  `check_any_privilege(INITS, [INITIATIVES, EXPLORE])` + `require_init_view`. Read-only; no write
  endpoint in this feature.
- **Rationale**: FR-014 – FR-016. Resolving labels server-side avoids the UI fetching six lists
  (and the `/api/list_items/` 100-row truncation). `diagnostics` has a single `rationale` column
  shared by proposer and reviewer — the UI shows it once per criterion.
- **Alternatives considered**: UI joins `criterias` + `list_items` + raw diagnostics —
  rejected (N list requests, truncation risk, label logic duplicated in the UI).

## R7 — Related Assets from the initiative side

- **Decision**: New routes under the `inits` domain, `api/app/inits/routes/initiative_assets.py`,
  reusing `lib`'s `AssetInit` model:
  `GET /api/initiatives/{id}/assets` (resolved: asset name, category, status, type, rationale),
  `POST /api/initiatives/{id}/assets` (`{asset, type, rationale}`),
  `DELETE /api/initiatives/{id}/assets/{asset_id}/{type}` (logical).
  Writes require **init MANAGE** (the page's owner), plus the target asset being active and
  visible to the caller (`lib` `user_asset_access` not `None`, superuser bypass) — so an owner
  cannot link an asset they cannot see. POST on an existing **inactive** (asset, type) link
  reactivates it with the new rationale (spec: "a removed identical link is restored"); on an
  active one → 409.
- **Uniqueness — amended 2026-09-23 (user decision)**: a link is identified by **(asset, init,
  type)**, matching the DDL primary key; the same pair may be linked once per relation type.
  The first version of this plan kept `(asset, init)` as the model key to avoid touching `lib`'s
  pair-addressed routes; the user rejected that reading, since the `type` in both PKs
  (`asset_inits`, `related_assets`) is there precisely to allow several links per pair. See R13.
- **Rationale**: the tab lives on the initiative, so its authority is the initiative's MANAGE;
  the asset-side routes stay governed by asset MANAGE, untouched.
- **Alternatives considered**: adding `GET /api/asset_inits/init/{id}` to `lib` and reusing its
  POST/DELETE — rejected: those writes require *asset* MANAGE, which an initiative owner
  typically lacks, and `lib`'s POST 409s on inactive rows (no restore).

## R8 — Initiative permissions routes

- **Decision**: `api/app/inits/routes/init_permissions.py`, prefix `/api/init_permissions`,
  mirroring `asset_permissions.py`: `GET /init/{init_id}` (non-revoked, incl. future-dated),
  `POST /` (409 on a live duplicate; a revoked grant does not block), `PUT /{id}`,
  `DELETE /{id}` = revoke (`valid_to = now()`, 400 if already revoked). Writes:
  `require_privilege(INITS, INITIATIVES, can_edit=True)` + `require_init_manage` (blocks VIEW
  self-escalation). Reads: `require_privilege(INITS, INITIATIVES)` + `require_init_view`
  (stricter than assets, whose permission reads have no per-asset check — no reason to repeat
  that gap).
- **Rationale**: FR-025/026, Constitution "Per-resource permissions" pattern verbatim.

## R9 — History and Discussion reads

- **Decision**: In `collaborations_service.py`: `get_initiative_history(session, init_id)`
  (all active collaborations, newest first, batched actor lookup, `summary` from a
  `(type, workflow_status)` → text map with a type fallback, `content` kept only for discussion
  types, synthetic `CREATED` entry from `initiatives.created_at` — the same `HistoryEntry` shape
  `lib` returns) and `list_discussion(session, init_id)` (COMMENT/QUESTION/ANSWER, oldest first,
  with author — the same `DiscussionItem` shape). Routes in `inits/routes/collaborations.py`:
  `GET /api/collaborations/history/init/{id}`, `GET /api/collaborations/discussion/init/{id}`,
  bounded `skip`/`limit`. Gate: `check_any_privilege(INITS,[INITIATIVES,EXPLORE])` +
  `require_init_view`. No write routes (Discussion is read-only here; posting belongs to Explore
  Initiatives).
- **Rationale**: reusing the response shapes lets the UI reuse `Foro.svelte` and `history.ts`
  unchanged except for the data source (R11).
- **Seed-shape caveat**: seed `collaborations` includes PENDING workflow rows (`DIAGNOSIS`,
  `ACCEPTANCE`, `DELIVERY`). History shows them like `lib` shows pending actions, labelled via
  `history.action.{TYPE}_{STATUS}`.

## R10 — Seed data (no migration)

- **Decision**: Edit seeds in place (product unreleased, `make rebuild`):
  - `51-inits-ddl.sql`: add `('COLLAB_TYPE','en','KICKOFF','Kickoff',55)` between REJECTION (50)
    and DELIVERY (60); add `es` rows for `INITIATIVE_STATUS`, `COLLAB_TYPE` (incl.
    `KICKOFF`→"Arranque"), `EXPECTED_IMPACT`, `PRIORITY_LEVEL`, `INITIATIVE_TYPE`, following the
    criteria lists' `es` block pattern.
  - `52-inits-insert.sql`: realign initiative statuses to cover every Core-Fields state —
    1 `IN_PROGRESS`, 2 `DELIVERED`, 3 `ACCEPTED`, 4 `ACTIVATED` (proposer answers only),
    5 `ACTIVATED` (no answers); set `type` on each; add `init_permissions` so the seeded
    ADMINISTRATIVE user and a COLLABORATOR hold MANAGE/VIEW on some but not all initiatives
    (enables the "only what I can access" test with real data).
- **Consequence**: adding `es` rows means every consumer of these lists must filter by language
  (`langItems()` pattern already used in `AssetDetailTabs.svelte`); the new page and modal do.
  No other consumer of these five lists exists today (the domain had no UI).
- **Provisioned DBs (Neon/local)**: one-off `INSERT`s for `KICKOFF` + `es` rows and `UPDATE`s
  for statuses, listed in quickstart.md.

## R11 — Frontend: copy the asset modal, parameterise the two shared readers

- **Decision**:
  - New page `ui/src/pages/inits/initiatives.astro` — derived from `lib/assets.astro`:
    `showAddButton={false}`, no create bridge, header funnels for status/type/priority/impact,
    favorites toggle, access-level filter, `manageKey="can_manage"`, no favorite action.
  - New `ui/src/components/inits/InitiativeDetailModal.astro` — derived from
    `AssetDetailModal.astro`: no create mode (the no-id branch is a no-op), no version/usage
    UI, core fields for initiatives, `applyStatusPolicy` driven by a transition map, tab-scoped
    saves (each tab saves only itself, stricter than assets where related/inits/permissions
    flush together).
  - New `ui/src/components/svelte/InitiativeDetailTabs.svelte` — tabs Core Fields, Diagnosis
    Questions, Related Assets, Permissions, Discussion, History; keeps the tab strip, dirty
    dots, diff-`flush` and `langItems` patterns; drops characteristics/versions.
  - **Parameterise, don't fork**, the two genuinely generic readers: `Foro.svelte` gains an
    optional `api` prop (default = current asset functions) and `idAttr` (default
    `"assetId"`); `history.ts` `mountHistory` gains optional `fetcher` and `idAttr`. The
    initiative modal passes collaboration fetchers and `idAttr: "initId"`, and `readonly` to
    Foro. Asset callers are unchanged.
  - Services: extend `lib/initiatives.ts`; new `lib/init_permissions.ts`,
    `lib/collaborations.ts`. Types in `types/api.ts`. i18n namespaces `initiative_modal.*`
    (DataTable convention from `i18Item="initiative"`), `initiative_table.*`,
    `initiative_detail_modal.*`, plus `history.action.{ACTIVATION,DIAGNOSIS,…,KICKOFF,…}`.
- **Rationale**: the explorer's verdict on `AssetDetailTabs.svelte` — ~40 % characteristics
  machinery, every service and payload key asset-specific — makes generalising it costlier and
  riskier (to a shipped surface) than a focused copy. The Constitution's anti-duplication rule
  targets backend plumbing; the UI modal is presentation. Foro/history, by contrast, are already
  generic in shape, so a data-source parameter removes duplication at almost no risk.
- **Alternatives considered**: a generic `EntityDetailTabs` with injected services — rejected
  for this feature; worth revisiting once Explore Initiatives adds a third consumer.

## R12 — Testing approach

- **Decision**: New pytest modules on the existing SQLite `session`/`client` fixtures, using the
  per-file helper pattern of `test_lib_access_enforcement.py` (`_user`, `_override`,
  `_seed_privileges`, `_mk_perm` with `NOW/PAST/FUTURE`):
  `test_inits_status.py` (pure transition map + PUT paths + collaboration written or not),
  `test_inits_access.py` (with-access scoping, pagination after filtering, MANAGE-only writes,
  delete), `test_inits_permissions.py` (grant/revoke/re-grant, self-escalation),
  `test_inits_initiative_assets.py` (link/unlink/restore/409, invisible asset refused),
  `test_inits_diagnostics.py` (all criteria listed, labels by lang with fallback, inactive
  criterion with answer kept), `test_inits_collaborations.py` (history order/shape, discussion
  threading, KICKOFF summary). Existing `lib` permission suites must stay green (R3).
- **Env**: tests run in the API container (`docker compose exec -T api uv run pytest -q`); the
  old "use a 3.12 venv" advice no longer applies (`requires-python = ">=3.14"`). Baseline:
  8 pre-existing failures in `test_auth.py`/`test_health.py`/`test_users.py`.

## R13 — Several links per pair, in `asset_inits` AND `related_assets` (amendment)

- **Decision**: Both `AssetInit` and `AssetRelation` models put `type` in their primary key,
  as the DDL already does (`pk_asset_inits (asset, init, type)`, `pk_related_assets (source,
  target, type)`). Every write/lookup identifies a link by the full triple:
  - **New, additive `lib` routes**: `GET`/`PUT`/`DELETE /api/asset_relations/{source}/{target}/{type}`
    and `/api/asset_inits/{asset}/{init}/{type}`. `PUT` on them cannot change `type` (it is part
    of the key — remove + add instead; 400).
  - **Existing pair routes kept** (Principle II): `…/{a}/{b}` still work whenever the pair has a
    single link (the active one if any, else the only row), so existing callers are unaffected.
    When the pair holds several links they answer **409** pointing to the typed route instead of
    silently picking one. A legacy `PUT` that changes `type` still works but 409s if the target
    triple already exists.
  - **`POST` duplicate check** moves from the pair to the triple. An active identical link → 409;
    an inactive identical link is **reactivated** (201) — the UI no longer needs its old
    "409 → PUT is_active:true" fallback, though that fallback keeps working.
  - **Init side** (unreleased, this branch): `DELETE /api/initiatives/{id}/assets/{asset_id}/{type}`
    replaces the pair form; POST keys by (asset, type).
  - **Read-only "Related" section** (`GET /api/asset_relations/related/{id}`): keeps "outgoing wins"
    per other asset, but no longer collapses several relation types — every outgoing link is
    listed; incoming links appear only for assets with no outgoing link.
  - **UI**: `AssetDetailTabs` (Related Assets + Related Inits), `InitiativeDetailTabs` and the
    Propose wizard stage and diff links keyed by (target, type); the duplicate check becomes
    "same target AND same type".
- **Rationale**: user requirement; the DDL keys were designed for it. Keeping the pair routes
  (with an explicit 409 on ambiguity) honours Principle II without letting them act on an
  arbitrary row.
- **Alternatives considered**: replacing the pair routes — rejected (breaking change for a
  shipped contract); making pair routes act on all links of the pair — rejected (a PUT/DELETE
  that silently fans out is surprising and hard to undo).

## R14 — Review amendments: list columns, favorites, diagnosis table, interactive discussion

- **List**: columns name, type, priority, status, tags, actions. Expected impact and access level
  stay as filters in the toolbar (their header funnels needed a visible column). The row star
  uses the shared DataTable `favoriteAction`, backed by new `PUT`/`DELETE
  /api/initiatives/{id}/favorite` (caller from session; VIEW is enough — favoriting is
  personal, not an edit).
- **Diagnosis Questions**: a real table — criterion | proposer answer | reviewer answer — with
  the two answer columns tinted differently (indigo for the proposer, emerald for the reviewer)
  and a two-card score header, one per party. The server adds totals/answered counts so the UI
  never re-sums. Rationale sits behind the same Show / Hide switch as Asset Management's
  characteristic details (icon + label + track, right-aligned, collapsed by default).
- **Discussion**: interactive, reusing `Foro.svelte` with a full `api` object (fetch + three
  posts + delete) instead of only `fetchDiscussion`. New write routes in
  `inits/routes/collaborations.py` backed by `collaborations_service.add_*`. Unlike the asset
  side (which takes `user_id` from the body), the author comes from the session, and delete is
  author-or-superuser only.
- **Alternatives considered**: reusing `/api/actions/*` for initiative posts — impossible
  (`actions.asset` NOT NULL); keeping a single `score` — rejected, the user wants one per party.
