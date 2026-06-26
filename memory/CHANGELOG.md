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

## 2026-06-25 22:09 — lib/ui: asset filters — inline column-header funnels + favorites toggle + privileges filter
- Reworked the Asset Repository (`/lib/assets`) filter UX and made the column-filter capability reusable in the DataTable. **Category** and **Status** filters now render as a **funnel icon inside their column headers** (not toolbar dropdowns); the toolbar keeps a **Favorites toggle** and a single **Privileges/Permisos** filter. The permissions filter was re-meant: instead of access-level (VIEW/MANAGE/PUBLIC) it surfaces assets the **current user** can access via their permission scope (USER/ROLE/TEAM/UNIT/PROJECT/PUBLIC).
- **Backend (additive, no DDL):** new `api/app/lib/internal/permissions_service.py` — `resolve_user_scopes` (USER/UNIT from the user; ROLE/TEAM from active collab `assignments`; PROJECT from those teams' projects; all `is_active` + temporally valid) and `assets_user_scopes` (per-asset scope-types granting the user access, incl. PUBLIC, via one batched query — no N+1). `GET /api/assets/with-access` now captures the current user and returns a new `permission_scopes` field on `AssetWithAccessLevels` (existing `access_levels`/`is_public` unchanged).
- **DataTable (reusable, backward-compatible):** new opt-in props `filterNHeaderColumn` (render a filter slot as a funnel `<details>` in that display column's `<th>`, hosting the same `<select>` id/`data-column-key`) and `filterNAsToggle` (render a slot as a switch). Factored slot building into `buildFilterConfigs` (`lib/datatable.ts`); `DataTableHead` renders header funnels, `DataTableFilters` skips header slots + renders toggles, `advancedTable.ts` made element-type-aware (reads `<select>` value OR checkbox `data-on-value`; highlights an active funnel). Also fixed a latent bug: `DataTable.astro` never forwarded filter-4 props to the toolbar. CSS `.dt-head-filter*` in `globals.css`. Unset props → identical prior behavior, so the ~18 other DataTable pages are unaffected.
- **Assets page:** Category→`category_name` header funnel, Status→`status_name` header funnel, Favorites→toolbar toggle, Privileges/Permisos→toolbar membership filter over a new `permissions` row field (from `permission_scopes`). New `asset_table.perm_filter_*` i18n in en/es; `AssetWithAccessLevels` type gains `permission_scopes`.
- **Tests:** new `api/tests/test_lib_permissions.py` — scope resolution (role/team/project via assignments; inactive/expired excluded) + per-asset scope matching (PUBLIC/USER/UNIT/ROLE/TEAM/PROJECT; inactive/expired permissions excluded; per-user isolation) + route auth/OpenAPI (the `/with-access` query uses Postgres-only `array_agg`/`bool_or`, so its behavior is Postgres-verified). Lib suites **81 passed** on the 3.12 venv. UI `bun run build` clean; `tsc` shows no new errors (8 pre-existing in `advancedTable.ts`).
- Files affected: `api/app/lib/internal/permissions_service.py` (new), `api/app/lib/internal/models.py`, `api/app/lib/routes/assets.py`, `api/tests/test_lib_permissions.py` (new), `ui/src/components/table/DataTable.astro`, `ui/src/components/table/partials/{DataTableToolbar,DataTableFilters,DataTableHead}.astro`, `ui/src/components/table/advancedTable.ts`, `ui/src/lib/datatable.ts`, `ui/src/types/datatable.ts`, `ui/src/styles/globals.css`, `ui/src/pages/lib/assets.astro`, `ui/src/lib/assets.ts` (type), `ui/src/types/api.ts`, `ui/src/i18n/{en,es}.json`
## 2026-06-25 17:15 — lib: discussion/vote/related/status UX + split-edit
- Six review-driven polish items on the lib asset surfaces (votes/foro/related/history + the edit modals). Branch `feat/lib-discussion-votes-status` off `develop`. Mostly frontend; the only backend change is the workflow-aware history + a new read endpoint (additive, contract-safe).
- **Separate like/dislike counts.** The vote bar showed a single net `score`; now it shows the like count beside 👍 and the dislike count beside 👎. `VoteTally`/`summarizeVotes` already carried `positive`/`negative` — pure display: `GalleryCard.astro` + `CatalogDetailModal.astro` (two `data-vote-{up,down}-count` spans), `paintVote` in `catalogGallery.ts`/`catalogDetail.ts`, and `votePositive`/`voteNegative` threaded through the 3 card wrappers + 3 gallery pages (replaced the `voteScore` prop).
- **Merged "Discussion" feed.** `Foro.astro`/`foro.ts` previously rendered two separate boxes (Comments / Questions). Now one composer with a **Comment | Question** type toggle + one chronological (newest-first) feed where each top-level entry carries a **Question**/**Comment** tag pill and questions keep their threaded answers + inline answer composer. Backend unchanged (the combined `/api/actions/discussion/asset/{id}` already returns all three). English label is "Discussion". New i18n `foro.{tag_comment,tag_question,post,empty}`.
- **Clickable related assets.** `related.ts` cards are now buttons carrying the detail modal's open trigger (`data-modal-open` + `data-asset-id`), so clicking re-hydrates the whole modal in place for that asset (`open()` already fetches everything by id). Guarded `catalogDetail` `open()` with `if (!dialog.open)` so re-opening in place doesn't throw. Cross-category related assets show core + discussion/history (no foreign spec sections) — acceptable.
- **Review status (the "published" repeated bug).** `_history_summary` was type-only, so PUBLICATION ASSIGNED/NOTIFIED/FINISHED all read "published the asset". Now workflow-aware (`_WORKFLOW_SUMMARIES` keyed by `(type, workflow_status)`): "was assigned to publish" / "was notified to publish" / "published the asset", etc. Added `get_workflow_stage` + **`GET /api/actions/workflow/asset/{id}`** (additive, returns the latest workflow action or null; new `WorkflowStage` DTO) and a **review-stage badge** in the detail header (distinct from the asset.status pill). UI: `history.ts` `actionLabel` prefers `history.action.{TYPE}_{STATUS}`; `getWorkflowStage` service + `WorkflowStage` type; i18n `history.action.*_*` + `workflow_stage.*`. Verified live: history verbs now read distinctly and `GET /api/actions/workflow/asset/1` → `{PUBLICATION, FINISHED, mateo.restrepo}`.
- **Split edit (core vs detail tabs).** Added an opt-in `data-asset-section` (`core` | `detail`, absent = full) on the edit-open trigger. `/lib/assets` (`AssetDetailModal`): the pencil now opens **core-only** (saves only `PUT /api/assets`); the row's master-detail/list expand already edited **tabs-only** (Characterizations/Related/Permissions). Gallery (`CatalogFormModal`/`catalogModal.ts`): the card **Edit** opens core-only; a new list-icon button opens the **characterizations-only** editor (gallery modals have no Related/Permissions). Each section save persists only its slice (hidden required core inputs relaxed in detail mode). AgentCard has no card-level edit (only the detail-modal "Editar", left as full). New i18n `asset_detail_modal.title_edit_{core,detail}` + `common.edit_details`.
- **Tests/checks:** updated `test_lib_history.py` (workflow-aware summary expectations) + added workflow-verb-distinctness, `get_workflow_stage`, and `/workflow` route auth/OpenAPI tests. Host-venv pytest: **103 passed**, 8 pre-existing unrelated failures (test_auth DNS-for-`db`, test_health path, test_users RBAC). `bun run build` clean. Live-verified votes/discussion/workflow against the running container.
- **Review hardening** (adversarial diff review):
  - `catalogDetail.ts` `open()` now carries an `openSeq` generation guard — the reopen-in-place (related-asset click) made the async stage/vote/favorite/asset loads race, so a slow response for the previous asset could paint over the one now shown. Late responses are now discarded. Also fixed the reopen scroll-to-top to target the inner scroll container (not the `<dialog>`).
  - `catalogModal.ts` disables **Save** while an edit's asset + characterizations load (and leaves it disabled if the load errors) — otherwise saving in "detail" mode against still-empty inputs would `deleteCharacterization` every feature, wiping the asset's characterizations.
  - Deterministic ordering for tied timestamps: `foro.ts` merged-feed comparator now returns 0 + breaks ties by id; `get_asset_history` sorts `(created_at, id)` (the seed inserts a whole workflow thread at one `NOW()`, so without the id tiebreak steps like "reviewed" could render before "assigned to review").
- Files affected: `api/app/lib/internal/{actions_service,models}.py`, `api/app/lib/routes/actions.py`, `api/tests/test_lib_history.py`, `ui/src/lib/{actions,catalogGallery,catalogDetail,catalogModal,foro,history,related}.ts`, `ui/src/types/api.ts`, `ui/src/components/lib/{GalleryCard,CatalogDetailModal,CatalogFormModal,Foro}.astro` (gallery/), `ui/src/components/lib/{McpCard,PromptCard,AgentCard,AssetDetailModal}.astro`, `ui/src/pages/lib/{mcps,prompts,agents,assets}.astro`, `ui/src/i18n/{en,es}.json`
## 2026-06-25 18:09 — lib: propose an asset for review (HU-Propose)
- Phase 6 of the lib roadmap: the **review-workflow entry point**. Proposing an asset is one atomic transaction that inserts the asset (`PROPOSED`) + one characterization per the category's `specifications` + a `PROPOSAL`/`FINISHED` action (proposer) + a `REVIEW`/`ASSIGNED` action (a reviewer) + `MANAGE` `asset_permissions` for both, per `docs/user-stories/lib-status.md`. The `REVIEW`/`ASSIGNED` row is exactly what Phase 5's notifications surface — **this is the generator that finally makes the bell light up**. No new table, no DDL.
- **Backend:** new `api/app/lib/internal/propose_service.py` — `propose_asset` (transactional, `session.flush()` for the asset id then a single `commit`; validates category + name; rolls back + re-raises `IntegrityError`), `list_reviewers` / `resolve_reviewer` (eligible = active **ADMINISTRATIVE**-profile users; explicit `reviewer_id` validated, else auto-assign the first). Routes in `routes/assets.py`, registered **before** `/{asset_id}`: `POST /api/assets/propose` (`ValueError`→400, `IntegrityError`→409) and `GET /api/assets/reviewers` (under LIB so a proposer needn't have ADMIN/USERS). New DTOs `ProposeRequest` / `ReviewerOption`. Additive only; gated by `require_privilege("LIB","ASSETS")`.
- **Frontend:** new `ui/src/pages/lib/propose.astro` (form: name/description/category/reviewer/tags/detail) + `ui/src/lib/propose.ts` (`getReviewers`, `proposeAsset`). Category + reviewer selects hydrate client-side (per-user data + the Vercel build-time empty-fetch gotcha). `ProposeRequest`/`ReviewerOption` types; `propose.*` i18n in en/es. Reachable at `/lib/propose`.
- **Tests:** `api/tests/test_lib_propose.py` — full transactional insert (asset/chars/actions/permissions), **integration with HU-LI11** (a proposal shows up as the reviewer's notification), value overrides, auto-reviewer, reviewer-must-be-ADMINISTRATIVE, no-reviewer/unknown-category/empty-name validation (+ writes-nothing), route auth-gating + OpenAPI + reviewers list + 400. Lib suites **84 passed** (propose + notifications + history + relations + foro + votes + lib) on in-memory SQLite (Python 3.12 venv — the sandbox's 3.14 host venv crashes fastapi/pydantic import; unrelated). UI `bun run build` clean; `tsc` no new errors (8 pre-existing in `advancedTable.ts`).
- **Scope note:** Propose generates the REVIEW assignment + sets up permissions; the downstream **HU-Review / HU-Modify** steps (reviewer approve/reject/feedback → status change + next assignment) and the propose page's sidebar/nav wiring are follow-ups. Characterizations are created from spec defaults (optionally overridden via `values`); a full per-feature propose form is a later enhancement.
- Files affected: `api/app/lib/internal/propose_service.py` (new), `api/app/lib/internal/models.py`, `api/app/lib/routes/assets.py`, `api/tests/test_lib_propose.py` (new), `ui/src/pages/lib/propose.astro` (new), `ui/src/lib/propose.ts` (new), `ui/src/types/api.ts`, `ui/src/i18n/{en,es}.json`, `docs/user-stories/lib-assets-roadmap.md`

## 2026-06-25 15:24 — lib: workflow notifications (HU-LI11)
- Phase 5 (final) of the lib roadmap: the header bell now lists the current user's open **workflow notifications** — assignments of type REVIEW/MODIFICATION/PUBLICATION/REJECTION, per `docs/user-stories/lib-status.md` (HU-Notifications). Built as the read/transition side of the Asset Action Service over the existing `actions` log — **no new table, no DDL**.
- **Model:** an assignment's lifecycle is tracked by **inserting** successive `actions` rows with `workflow_status` ASSIGNED → NOTIFIED → FINISHED (matching the seed — each transition is a new row, never an update). A notification is the latest row of a per-(asset, type) thread whose status is still ASSIGNED (bold/unread) or NOTIFIED (seen, dismissible); FINISHED drops it off.
- **Backend:** `actions_service.list_notifications` (group user's workflow actions by (asset, type), keep latest-status ASSIGNED/NOTIFIED, asset names via one batched `IN` — no N+1, newest first), `mark_notified` (ASSIGNED→insert NOTIFIED, idempotent), `dismiss_notification` (insert FINISHED). Routes registered **before** `/{id}`: `GET /api/actions/notifications` (current user from JWT), `POST /api/actions/notifications/{id}/notified`, `POST /api/actions/notifications/{id}/dismiss`. Per-user isolation: the transition routes 404 if the action isn't the caller's. New DTO `NotificationItem`. Additive only; gated by `require_privilege("LIB","ACTIONS")`.
- **Frontend:** rewired the static `NotificationMenu.astro` stub to a hydrated list + `ui/src/lib/notifications.ts` (service + `mountNotifications` controller): fetches the user's notifications, badge dot + count, **bold** for ASSIGNED, a Dismiss control for NOTIFIED, click a row → mark seen (ASSIGNED→NOTIFIED) in place. Asset names via `textContent` (XSS-safe). `NotificationItem` type in `types/api.ts`; `notifications.*` i18n (per-type labels) in en/es.
- **Scope note (flagged):** this is the **display/transition** side only. The propose/review workflow that *generates* assignments (HU-Review/Modify/Show-Action) and those destination views are **not built**, so clicking a notification marks it seen in place rather than navigating — the menu surfaces/dismisses whatever assignments exist. Documented as the known dependency in the roadmap.
- **Tests:** `api/tests/test_lib_notifications.py` — latest-status grouping (ASSIGNED unread / NOTIFIED seen / FINISHED excluded), type filtering, per-user isolation, distinct-type threads, mark_notified (+ idempotent), dismiss, route auth-gating + OpenAPI + cross-user 404. Lib suites **69 passed** (notifications + history + relations + foro + votes + lib) on in-memory SQLite (run on a Python 3.12 venv — the sandbox's 3.14 host venv crashes fastapi/pydantic import; unrelated). UI `bun run build` clean; `tsc` no new errors (8 remaining are pre-existing in `advancedTable.ts`).
- Files affected: `api/app/lib/internal/actions_service.py`, `api/app/lib/internal/models.py`, `api/app/lib/routes/actions.py`, `api/tests/test_lib_notifications.py` (new), `ui/src/components/core/header/NotificationMenu.astro`, `ui/src/lib/notifications.ts` (new), `ui/src/types/api.ts`, `ui/src/i18n/{en,es}.json`, `docs/user-stories/lib-assets-roadmap.md`

## 2026-06-25 14:30 — lib: asset history timeline (HU-LI10)
- Phase 4 of the lib roadmap: a read-only **activity timeline** on the shared gallery detail modal (prompts/agents/mcps) — every event on an asset (creation, votes, comments, questions, answers, and any review-workflow actions), newest first. Built as the **read-side of the Asset Action Service** over the existing `actions` log — **no new table, no DDL**. HU-LI10 (derived from `actions`; no direct story in `docs/user-stories/04-lib.md`).
- **Backend:** `actions_service.get_asset_history` aggregates every active action for an asset + a synthetic **CREATED** marker from the asset row, newest first; actor usernames resolved with one batched `IN` query (no N+1); a server-derived `summary` per entry (`_history_summary`, votes → upvoted/downvoted), `content` only for COMMENT/QUESTION/ANSWER. New route `GET /api/actions/history/asset/{asset_id}` registered **before** `/{id}` (bounded `skip`/`limit` over the timeline; unknown asset → 400). New read-projection DTO `HistoryEntry`. Additive only — no endpoint/key removed or renamed; gated by `require_privilege("LIB","ACTIONS")`.
- **Frontend:** new `ui/src/components/lib/gallery/HistoryTimeline.astro` (section shell, scoped by `modalId`) + `ui/src/lib/history.ts` (`getAssetHistory` service + `mountHistory` controller — hooks the same open trigger as the detail/foro controllers, renders a per-type dot + actor + localized action label + relative time, with a content snippet for discussion entries; actor/content via `textContent`, XSS-safe). Embedded in `CatalogDetailModal` (below the discussion) and hydrated from `mountCatalogDetail`, so all three catalogs get it. `HistoryEntry` type in `types/api.ts`; `history.*` i18n (incl. per-action-type labels) in en/es. Labels localize by `type`, falling back to the server summary.
- **Tests:** `api/tests/test_lib_history.py` — newest-first ordering with the CREATED marker, inclusion of vote/comment/question/answer rows, vote summary + content suppression, actor resolution, inactive excluded, empty-asset (CREATED-only) case, workflow_status carried, route auth-gating + OpenAPI + unknown-asset 400. Lib suites **44 passed** (history + foro + votes + lib) on in-memory SQLite (run on a Python 3.12 venv — the sandbox's 3.14 host venv crashes fastapi/pydantic import; unrelated to this change). UI `bun run build` clean; `tsc` shows no new errors (the 8 remaining are pre-existing in `advancedTable.ts`).
- Files affected: `api/app/lib/internal/actions_service.py`, `api/app/lib/internal/models.py`, `api/app/lib/routes/actions.py`, `api/tests/test_lib_history.py` (new), `ui/src/components/lib/gallery/HistoryTimeline.astro` (new), `ui/src/lib/history.ts` (new), `ui/src/components/lib/gallery/CatalogDetailModal.astro`, `ui/src/lib/catalogDetail.ts`, `ui/src/types/api.ts`, `ui/src/i18n/{en,es}.json`, `docs/user-stories/lib-assets-roadmap.md`
## 2026-06-25 05:40 — lib: related assets on gallery detail (HU-LI07)
- Phase 3 of the lib roadmap: a read-only **"Related" section** on the shared gallery detail modal (prompts/agents/mcps) showing the assets connected to the one being viewed, in **both directions**. Built on the existing `related_assets` table — **no new table, no DDL**. HU-LI07 in the project spreadsheet (maps to `docs/user-stories/04-lib.md` HU-LI09 "Related Assets"; numbering left uncorrected there). Creating/removing relations stays in the admin asset editor; the gallery is display-only.
- **Backend:** two additive routes in `routes/asset_relations.py`, registered **before** the composite `/{source_id}/{target_id}`: `GET /api/asset_relations/target/{asset_id}` (reverse lookup, counterpart to the existing `/source/{asset_id}`) and `GET /api/asset_relations/related/{asset_id}` (resolved related **assets** in both directions, de-duplicated by the other asset id with outgoing winning ties, inactive/missing assets excluded, resolved via one batched `IN` query — no N+1; each direction fetch bounded by `skip+limit`). New read-projection DTO `RelatedAsset` (asset display fields + `relation_type` + `direction` + `rationale`) in `internal/models.py`. Additive only — no endpoint/key removed or renamed; gated by `require_privilege("LIB","ASSETS")`.
- **Frontend:** new `ui/src/components/lib/gallery/Related.astro` (section shell, scoped by `modalId`, hidden when the asset has no relations) + `ui/src/lib/related.ts` (`mountRelated` controller — hooks the same open trigger as the detail/foro controllers, renders mini cards with a direction-arrow relation chip; asset text via `textContent`, XSS-safe). Embedded in `CatalogDetailModal` (above the discussion) and hydrated from `mountCatalogDetail`, so all three catalogs get it with zero per-page wiring. Service `getAssetRelationsByTarget` + `getRelatedAssets` in `asset_relations.ts`; `RelatedAsset` type in `types/api.ts`; `related.*` i18n (incl. RELATION_TYPE labels) in en/es.
- **Tests:** `api/tests/test_lib_relations.py` — reverse lookup (+ inactive-relation excluded), resolved both-directions shape, bidirectional de-dup (outgoing wins), inactive target asset excluded, empty case, self-relation rejected (existing create contract), route auth-gating + OpenAPI presence. Lib suites: **43 passed** (relations + foro + votes + lib) on in-memory SQLite (run on a Python 3.12 venv — the sandbox's 3.14 host venv crashes fastapi/pydantic import; unrelated to this change). UI `bun run build` clean; `tsc` shows no new errors (the 8 remaining are pre-existing in `advancedTable.ts`).
- Files affected: `api/app/lib/internal/models.py`, `api/app/lib/routes/asset_relations.py`, `api/tests/test_lib_relations.py` (new), `ui/src/components/lib/gallery/Related.astro` (new), `ui/src/lib/related.ts` (new), `ui/src/components/lib/gallery/CatalogDetailModal.astro`, `ui/src/lib/catalogDetail.ts`, `ui/src/lib/asset_relations.ts`, `ui/src/types/api.ts`, `ui/src/i18n/{en,es}.json`, `docs/user-stories/lib-assets-roadmap.md`

## 2026-06-25 00:57 — lib: asset foro — comments, questions & answers (HU-LI06)
- Phase 2 of the lib roadmap: a **discussion** on each asset — comments, questions, and threaded answers. All are `actions` rows (`type` COMMENT/QUESTION/ANSWER; an ANSWER threads to its QUESTION via `parent`) — **no new table**, built on the Asset Action Service from Phase 1. HU-LI06 in the project spreadsheet (maps to `docs/user-stories/04-lib.md` HU-LI06 "Participations" + HU-LI08 "Comment"; numbering left uncorrected there).
- **Backend:** extended `actions_service.py` with `add_comment`/`add_question`/`add_answer` (answer validates its parent is an active QUESTION on the *same* asset → `ValueError`; empty content → `ValueError`; writes roll back + re-raise `IntegrityError`) and `list_discussion` (active COMMENT/QUESTION/ANSWER for an asset, oldest first, author usernames resolved with one batched `IN` query — no N+1) + `discussion_item`. New routes in `routes/actions.py`, registered **before** `/{id}`: `GET /api/actions/discussion/asset/{asset_id}`, `POST /api/actions/{comments,questions,answers}` (asset-exists → 400, `ValueError` → 400, `IntegrityError` → 409). Logical delete reuses the existing `DELETE /api/actions/{id}`. New DTOs `ParticipationCreate`/`AnswerCreate`/`DiscussionItem`. Additive only — no endpoint/key removed or renamed.
- **Frontend:** new `ui/src/lib/foro.ts` (service + `mountForo` controller + `groupDiscussion`) and `ui/src/components/lib/gallery/Foro.astro` (comments + Q&A composers with empty/loading/error states), embedded in the shared `CatalogDetailModal` and hydrated from `mountCatalogDetail` — so prompts/agents/mcps all get the discussion section. User content is rendered via `textContent` only (XSS-safe). Reuses the top-layer `toast` for errors and `getUser` for the author guard. `DiscussionItem`/`ParticipationCreate`/`AnswerCreate` types in `types/api.ts`; `foro.*` i18n keys in en/es.
- **Card-level discuss button + count:** added a chat-bubble button to the `GalleryCard` interaction bar (beside the like/dislike), shown whenever the card has a `detailModalId`. Clicking it opens the detail view and (via a `data-foro-focus` flag on the synthetic opener) `mountForo` scrolls the discussion into view and focuses the comment composer. A discussion **count badge** (comments+questions+answers) is SSR-prefilled from the same bulk `getActions` fetch each gallery already runs (`summarizeDiscussionCounts`, no N+1) and kept live — `mountForo` repaints the originating card's badge whenever the discussion loads/changes. Plumbed `discussCount` through the card wrappers (`{Prompt,Mcp,Agent}Card`) and pages. i18n `gallery.discuss` in en/es.
- **Tests:** `api/tests/test_lib_foro.py` — service (comment/question/answer create, parent validation, empty-content, threadable list shape, inactive excluded) + route contract (auth-gating, OpenAPI presence, answer bad-parent → 400, IntegrityError → 409). Lib suites: **33 passed** (foro + votes + lib) on in-memory SQLite. Also verified live against a real Postgres 16 (seeded `db/sql`): post comment/question/answer → 201 with author resolved + correct threading, bad parent/empty → 400. UI `bun run build` clean.
- Files affected: `api/app/lib/internal/actions_service.py`, `api/app/lib/internal/models.py`, `api/app/lib/routes/actions.py`, `api/tests/test_lib_foro.py` (new), `ui/src/lib/foro.ts` (new), `ui/src/components/lib/gallery/Foro.astro` (new), `ui/src/components/lib/gallery/CatalogDetailModal.astro`, `ui/src/components/lib/gallery/GalleryCard.astro`, `ui/src/components/lib/{Prompt,Mcp,Agent}Card.astro`, `ui/src/pages/lib/{prompts,mcps,agents}.astro`, `ui/src/lib/catalogDetail.ts`, `ui/src/lib/catalogGallery.ts`, `ui/src/types/api.ts`, `ui/src/i18n/{en,es}.json`

## 2026-06-24 19:17 — admin/privileges: module-driven Option select
- In the Privilege modal, selecting a **Module** now rebuilds the **Option** `<select>` with only that module's options (option codes are only unique within a module). Server fetches the full options (`getOptions(undefined, 0, 1000)`) and builds an `optionsByModule` map (`{ moduleCode: [{value: code, label: name}] }`) passed to the client via `data-options-by-module` on `#privileges-data`. Table `option_name` now resolves by composite `(module, code)`.
- Client rebuilds options on the module select's `change` (create + edit modals), preserving the translated placeholder and previous value; the create modal is seeded for its default module on load. Works on edit prefill because `crudClient` sets `module` before `option` in `fieldKeys` order. Mirrors the dimension-driven Value pattern from `collab/metrics`.
- UI-only change; verified via IDE diagnostics (no TS errors). Files affected: `ui/src/pages/admin/privileges.astro`

## 2026-06-24 18:47 — DataTable: persist column filter selection in the URL
- `advancedTable.ts` now writes each column filter's value back to the URL (`history.replaceState`, no reload) on change, under the same query param it already reads on init (`columnFilter`…`columnFilter4`). A reload — e.g. the one after a create/edit/delete save — now restores the filter the user was viewing instead of snapping back to the original URL value. The Reset button also clears those params.
- Centralized here (a bundled script that runs in dev and prod) instead of per-page inline `type="module"` scripts, which 404 in the Vercel build; works automatically for every page with a `columnFilter` (users, metrics, list_items, …). Removed the now-redundant per-page sync snippets from `collab/metrics.astro` and `admin/users.astro`.
- Files affected: `ui/src/components/table/advancedTable.ts`, `ui/src/pages/collab/metrics.astro`, `ui/src/pages/admin/users.astro`

## 2026-06-24 17:13 — collab/metrics: dimension-driven Value scale
- Metric **Value** select is now driven by the selected **Dimension** instead of a hardcoded list. Server loads the items of every `SCALE`-type list (`getListsbyType("SCALE")` → per-list `getListItemsbyList`) into a `scalesByList` map, plus a `dimensionScale` map (dimension code → its `scale` FK, falling back to the code). Both are passed to the client via `data-*` on `#metrics-data`.
- Client rebuilds the Value `<option>`s on the dimension select's `change` (wired for both create and edit modals), filtered to the user's language; preserves the translated placeholder and the previously selected value. Works on edit prefill because `crudClient` sets `dimension` before `value` in `fieldKeys` order. The Value field no longer renders server-side options or uses `filterLang` (client handles scale + language).
- UI-only change; verified via IDE diagnostics (no TS errors). Manual check: toggle dimension in the New Metric modal → Value list swaps to the dimension's scale.
- Files affected: `ui/src/pages/collab/metrics.astro`

## 2026-06-24 14:25 — lib: asset voting (HU-LI05) + Asset Action Service foundation
- Implemented up/down voting on assets (HU-LI05 in the project user-story spreadsheet; note `docs/user-stories/04-lib.md` numbers this story HU-LI07 "Vote" — different numbering, not corrected here). Votes are `actions` rows of `type=VOTE` with `content` POSITIVE/NEGATIVE — **no new table**; one active vote per (user, asset), re-click toggles off, opposite click flips.
- **Reusable abstraction (backend):** new `api/app/lib/internal/actions_service.py` — generic helpers over the `actions` event log (`list_actions_for_asset`, `get_user_vote`, `count_votes`, `get_vote_tally`, `set_vote`). This is the foundation later phases (foro/history/notifications) build on.
- **Additive model fix:** mapped the existing `workflow_status` DDL column onto `Action`/`ActionCreate`/`ActionUpdate` (it was missing from the model; column already in `db/sql/41-lib-ddl.sql`, so no migration). Needed by the future notifications/review workflow.
- API: added vote convenience routes under `/api/actions/votes/*` (`GET /votes/asset/{id}` tally+my_vote, `GET /votes/{user_id}/{asset_id}`, `POST /votes` set/flip, `DELETE /votes/{user_id}/{asset_id}` clear), registered before `/{id}` so the literal segment isn't parsed as an id. Additive only — no endpoint/key removed or renamed.
- UI: new `ui/src/lib/actions.ts` service (+ `Action`/`VoteTally` types); up/down vote bar on the shared `GalleryCard` and `CatalogDetailModal` (so prompts/agents/mcps all get it), wired in `catalogGallery.ts`/`catalogDetail.ts` (repaint from the authoritative tally; card + detail stay in sync). SSR pre-fill of scores via one bounded `getActions(0,1000)` + client-side `summarizeVotes` (mirrors the bulk characterizations fetch). i18n `gallery.vote_*` in en/es.
- Tests: `api/tests/test_lib_votes.py` (service logic: toggle/flip/clear/reactivate/tally/invalid-value + route auth-gating + OpenAPI). Extended `test_lib.py` for `workflow_status`. Backend suite: 45 passed (the 8 failures are pre-existing env-only: no DB / gated `test_users`). UI `bun run build` clean; no new `tsc` errors.
- Docs: added `docs/user-stories/lib-assets-roadmap.md` — the 5-phase lib roadmap (Voting → Foro → Related Assets → History → Notifications), one review-sized PR per phase, all on existing tables (zero new tables), with the HU-LI spreadsheet↔`04-lib.md` numbering map. Phase 1 marked shipped.
- **Fix pass (PR #53 follow-up — same branch):** three voting defects.
  - *Vote returned 500.* Root cause = local DB drift: the live `actions` table predated the additive `workflow_status` column (it's in `db/sql/41-lib-ddl.sql` + the `Action` model, but `db/sql` only re-applies on a fresh volume), so the `SELECT … workflow_status` raised `UndefinedColumn`. Fixed locally via `make reset` (re-seed). Hardened the code so a DB-constraint error can never surface as a raw 500: `actions_service.set_vote` now wraps its writes in `try/except IntegrityError → rollback → re-raise`, and `POST /api/actions/votes` + `DELETE /api/actions/votes/{user}/{asset}` catch `IntegrityError → rollback → HTTPException(409)` (mirrors the favorites template). UI: on a failed vote, `catalogGallery.ts`/`catalogDetail.ts` now re-sync from `getVoteTally → paintVote` so the bar never shows stale state.
  - *Error toasts rendered behind the detail modal.* The detail view is a native `<dialog>.showModal()` (browser top layer, beats any z-index); a `document.body`-appended `z-50` toast loses. New `ui/src/lib/toast.ts` renders into a non-modal `<dialog>.show()` container (joins the top layer, re-promoted per toast) and `installGlobalToast()` registers `window.showToast`. Wired into `lib/{prompts,agents,mcps}.astro`, replacing their inline `showToast`. (~20 other pages share the latent bug — out of scope here.)
  - *Vote-icon UX.* Vote controls now use solid **thumbs-up / thumbs-down** icons (Heroicons; thumb-down is the thumb-up rotated 180°); state shows via **color only** — vivid emerald/rose when it's the user's vote, muted gray otherwise (no `fill` toggle, which made the glyph a messy blob). Title/aria-label still flips to "Remove vote" when active so the un-vote toggle is discoverable. Added `gallery.vote_remove` (en/es) + a `translate()` helper in `i18nClient.ts` to keep the swapped labels localized. In the detail view (`CatalogDetailModal`) the vote bar moved up into the header beside the favorite star (was below the description).
  - *Vote de-bounce.* Continuous clicking was firing one `POST /votes` per click (locally each request settles in a few ms, so an in-flight guard alone didn't coalesce them). Switched to a **trailing debounce**: each click resets a ~300ms timer and the vote only fires once clicking pauses, so a burst collapses to a single request (per-card `WeakMap` timer in `catalogGallery.ts`; single timer in `catalogDetail.ts`, cleared on modal close). A DOM-level `data-voting` in-flight guard still serializes any overlapping request.
  - *Vote de-bounce.* Added an in-flight "bouncer": while a vote request is pending, further clicks on that bar are ignored (a `data-voting` flag on the vote-bar element, in both `catalogGallery.ts` and `catalogDetail.ts`). Prevents rapid double-clicks from firing a burst of `POST /votes`. DOM-level flag (not a closure) so it holds even if a handler were ever bound twice.
  - Tests: added 2 regression tests to `test_lib_votes.py` (service rolls back + re-raises on `IntegrityError`; `POST /votes` maps it to 409) — `test_lib_votes.py` is 13/13 green in-container. Verified live through the Docker container (vote/toggle/flip/clear → HTTP 200, no 500). `bun run build` clean.
- **API container boot fix (arm64).** After the rebuild the API crashed with `ModuleNotFoundError: No module named 'pydantic_core._pydantic_core'`. Root cause was **not** a missing wheel and **not** the 3.14 pin (kept at 3.14 per team direction) — it was a stale **x86_64** host `api/.venv` (built earlier under emulation) bind-mounted over the container's correct **aarch64** venv via `./api:/app`, so the arch-tagged `.so` didn't match the container's `SOABI`. Fix: added an anonymous `- /app/.venv` volume to the api service in `docker-compose.yml` so the image-built (in-arch) venv isn't shadowed, removed the stale host `api/.venv`, and fixed the `make pytest` target to run `uv run pytest` (the venv bin isn't on the container `PATH`). API now boots clean on 3.14; `make pytest` runs in-container (47 passed; the 8 `test_auth`/`test_health`/`test_users` failures are pre-existing and unrelated to voting).
- Files affected: `api/app/lib/internal/models.py`, `api/app/lib/internal/actions_service.py` (new), `api/app/lib/routes/actions.py`, `api/tests/test_lib.py`, `api/tests/test_lib_votes.py` (new), `ui/src/types/api.ts`, `ui/src/lib/actions.ts` (new), `ui/src/lib/toast.ts` (new), `ui/src/lib/catalogGallery.ts`, `ui/src/lib/catalogDetail.ts`, `ui/src/utils/i18nClient.ts`, `ui/src/components/lib/gallery/GalleryCard.astro`, `ui/src/components/lib/gallery/CatalogDetailModal.astro`, `ui/src/components/lib/{PromptCard,AgentCard,McpCard}.astro`, `ui/src/pages/lib/{prompts,agents,mcps}.astro`, `ui/src/i18n/{en,es}.json`, `docker-compose.yml`, `Makefile`, `docs/user-stories/lib-assets-roadmap.md` (new)

## 2026-06-20 00:15 — admin: remove dead item_translations feature (no DDL backing)
- `item_translations` had a SQLModel model, route, UI page/service/types, and `manual/` SQL references, but **no `CREATE TABLE` in any `db/sql/` migration** — the table never existed, so its endpoints 500'd. Bilingual labels are already handled by `list_items.lang` (one row per language), so the concept was dead. Removed it wholesale.
- API: deleted `admin/routes/item_translations.py`; removed `ItemTranslation*` models from `admin/internal/models.py`; dropped the router import/registration/openapi-tag/path-map from `main.py`; removed the `ItemTranslation` import from `migrations/env.py`. Also removed the two now-broken `list_items` endpoints that queried it (`GET /api/list_items/list/{code}/with-translations` and `/{code}/{value}/with-translations`) plus the now-unused `Dict, Any` import — these already 500'd against the missing table (verified the path now 404s; `GET /api/list_items/` still 200s).
- UI: deleted `lib/item_translations.ts` and `pages/admin/item_translations.astro`; removed the `ItemTranslation*` interfaces from `types/api.ts`. No sidebar option/i18n keys existed for it, so nav is unaffected. `tsc --noEmit` clean.
- DB: removed the `item_translations` lines from `manual/delete.sql` and `manual/drop.sql`.
- Contract note: the removed `with-translations` endpoints were non-functional (queried a non-existent table), so this is a cleanup of dead surface, not a breaking change to a working contract. `app.main` imports OK; `tests/test_admin.py` still passes. Full-repo grep for `item_translation` is now empty.
- Files affected: `api/app/main.py`, `api/app/admin/internal/models.py`, `api/app/admin/routes/list_items.py`, `api/app/admin/routes/item_translations.py` (deleted), `api/migrations/env.py`, `ui/src/types/api.ts`, `ui/src/lib/item_translations.ts` (deleted), `ui/src/pages/admin/item_translations.astro` (deleted), `db/sql/manual/delete.sql`, `db/sql/manual/drop.sql`

## 2026-06-20 00:02 — admin: align models with DDL (profiles.icon + max_length widths)
- Validated all 8 admin entities against `11-admin-ddl.sql`. privileges was already complete; the rest had length caps tighter than the DDL and **`profiles.icon` (TEXT) was missing entirely** from the API, UI types, page, and i18n — yet the seed already stores icon values (e.g. `ADMINISTRATIVE` → `user-group`), so the API was silently dropping them. Added `icon: Optional[str]` to `ProfileBase`/`Profile`, `ProfileCreate`, `ProfileUpdate`; `icon?: string` to the UI `Profile*` interfaces; an `icon` form field + data mapping + create/update payloads in `profiles.astro`; and `profile_modal.icon` to `en.json`/`es.json`. Verified live: `GET /api/profiles/` now returns the icon.
- Aligned `max_length` with the DDL: `modules.description`/`lists.description`/`profiles.description` 255→500 (`VARCHAR(500)`); `business_units.type` 50→100 (`VARCHAR(100)`); `list_items.label` 150→200 (`VARCHAR(200)`); `users.email` 100→244 (`VARCHAR(244)` — a long-but-valid email would have failed); `options.path`/`options.icon` 500→unbounded (DDL `TEXT`). All across Base/Create/Update as applicable.
- No DDL change — columns already exist. Added `tests/test_admin.py` (6 contract tests: profiles.icon presence/round-trip, VARCHAR-length alignment, options TEXT-unbounded, all-DDL-fields regression guard across the 8 models, OpenAPI schema) — all pass.
- ⚠️ Flagged (NOT changed — needs a decision): the `item_translations` table has a SQLModel model + admin route + UI page + `manual/{delete,drop}.sql` references, but **no `CREATE TABLE` in any `db/sql/` migration** — the table is never created on a fresh volume, so its endpoints would fail at runtime. Likely superseded by `list_items.lang` (bilingual rows). Decide whether to add the DDL or remove the dead model/route/page.
- Files affected: `api/app/admin/internal/models.py`, `api/tests/test_admin.py`, `ui/src/types/api.ts`, `ui/src/pages/admin/profiles.astro`, `ui/src/i18n/en.json`, `ui/src/i18n/es.json`

## 2026-06-19 23:55 — lib: fix actions model desync with DDL (broken endpoint)
- Validated all 6 lib entities against `41-lib-ddl.sql` (+ `43-lib-perms-active-ddl.sql`). assets, characterizations, favorite_assets, related_assets, asset_permissions were field-complete across API/UI/types. **`actions` was badly desynced** and `GET /api/actions/` was 500ing because the model selected columns that don't exist:
  - `asset` was typed `str(50) → assets.code`, but the DDL/seed use `BIGINT → assets.id` (assets has no `code` column; seed inserts `asset=1,2`). Now `int` via `BigInteger`/`ForeignKey('assets.id')` (same pattern as characterizations/favorites/relations).
  - Mapped a phantom `details` JSON column and a `measured_at` column — neither exists in the DDL. Removed both; added the real `detail` (TEXT) column the DDL defines.
  - `content`/`reference` are `TEXT` in the DDL but were capped at 500 — now unbounded.
  - `routes/actions.py`: dropped the `json.dumps(details)` handling (create + update), fixed the asset-existence error message (`code`→`id`), removed the now-unused `import json`, updated docstrings. Verified live: `GET /api/actions/` now returns 200 with `detail`/int `asset` against the dev Postgres.
- No UI changes (actions has no page/service/type). No DDL change — the DDL was already correct; the model was wrong.
- Added `tests/test_lib.py` (5 contract tests: detail-not-details/measured_at, asset-is-int, TEXT-unbounded, all-DDL-fields regression guard across the 6 models, OpenAPI schema) — all pass.
- Files affected: `api/app/lib/internal/models.py`, `api/app/lib/routes/actions.py`, `api/tests/test_lib.py`

## 2026-06-19 23:30 — collab: align models with DDL (projects.detail)
- Validated all 6 collab entities against `31-collab-ddl.sql`. teams, roles, assignments, dimensions, metrics were already field-complete across API/UI/types/i18n. The only gap was **`projects.detail`** (TEXT) — present in the DB but missing from `ProjectBase`/`Project`, `ProjectCreate`, `ProjectUpdate`, the UI `Project*` interfaces, the page form, and i18n. Added `detail: Optional[str]` to the 3 API schemas, `detail?: string` to the 3 UI interfaces, a `detail` textarea field + data mapping + create/update payloads in `projects.astro`, and `project_modal.detail` to `en.json`/`es.json`. No DDL change (column already exists).
- Also added `as const` to the 3 pre-existing `type: "text"` project form fields to clear real TS errors flagged by the Astro language server (unrelated to the field gap).
- **Aligned all API `max_length` caps with the DDL** (were tighter, risking read/write failures on long values): TEXT columns are now unbounded — `roles.icon`, `teams.chat_channel_url`/`kanban_board_url`, `assignments.observation`, `projects.repo_url`/`detail`, `metrics.value`/`observation`; VARCHAR caps fixed — `roles.description` 255→500, `dimensions.scale` 50→100 (Create/Update). The most likely to have bitten: `roles.description` at 255 would fail SQLModel validation when reading a 256–500 char description the DDL (`VARCHAR(500)`) allows.
- Added `tests/test_collab.py` (7 contract tests: detail presence/round-trip/optionality, all-DDL-fields regression guard across the 6 models, OpenAPI schema, plus TEXT-unbounded and VARCHAR-length alignment guards) — all pass.
- Files affected: `api/app/collab/internal/models.py`, `api/tests/test_collab.py`, `ui/src/types/api.ts`, `ui/src/pages/collab/projects.astro`, `ui/src/i18n/en.json`, `ui/src/i18n/es.json`

## 2026-06-19 22:57 — taxo/{categories,features,specifications}: align models with DDL end-to-end
- **categories.icon**: the `icon` column in `21-taxo-ddl.sql` was missing from the API models, so the value the UI sent on create/edit was silently dropped (Pydantic discarded it) and never returned. Added `icon: Optional[str]` to `CategoryBase`/`Category` (table), `CategoryCreate`, and `CategoryUpdate`. UI: added `icon?: string` to `Category`/`CategoryCreate`/`CategoryUpdate` in `types/api.ts` (and the orphan `types/category.ts`); fixed the form field to use the new `category_modal.icon` i18n key (was wrongly pointing at `module_modal.icon`) and added that key to `en.json` + `es.json`.
- **features.list**: same gap — the `list` column (FK→`lists.code`) was missing from `FeatureBase`/`Feature`, `FeatureCreate`, `FeatureUpdate`, so the list the UI sent was dropped. Added `list: Optional[str]` to all three API schemas and `list?: string` to the UI `Feature`/`FeatureCreate`/`FeatureUpdate` interfaces. `feature_modal.list` i18n key already existed. Also removed a spurious `parent` key from the features create/update payloads (copy-paste from categories; features have no parent).
- **specifications**: all 6 DDL columns were already aligned across API/UI/types/i18n — no field gap. But fixed a correctness bug: the page sent `default_value: data.default_value || false` (copy-paste from a boolean field) on create/update; `default_value` is TEXT, so an empty value sent boolean `false` → Pydantic 422 for `Optional[str]`. Changed to `|| null` and relaxed the UI `Specification*` types' `default_value` to `string | null`.
- No DDL change anywhere — all columns already exist.
- `tests/test_categories.py` now has 10 contract tests (field presence, value round-trip, optionality, OpenAPI schema for `icon`/`list`, plus specification field/None-default regression) — all pass. Note: the 14 pre-existing suite errors come from a broken SQLite `create_all` fixture (FK resolution), unrelated to this change.
- Files affected: `api/app/taxo/internal/models.py`, `api/tests/test_categories.py`, `ui/src/types/api.ts`, `ui/src/types/category.ts`, `ui/src/pages/taxo/categories.astro`, `ui/src/pages/taxo/features.astro`, `ui/src/pages/taxo/specifications.astro`, `ui/src/i18n/en.json`, `ui/src/i18n/es.json`

## 2026-06-18 12:48 — Tree-view popups on hierarchical CRUD pages (Business Units)
- Added a secondary toolbar button (hierarchy/share icon) next to "+Business Unit" that opens an XL `<dialog>` rendering the existing `TreeChart` (ECharts) over the page's rows — no duplicate page, reuses the `taxonomy.astro` visualization. Categories uses `data-i18n-title`/`data-i18n="menu_options.taxonomy"` ("View Taxonomy"); Business Units uses `menu_options.hierarchy` ("View Hierarchy"). Both dispatch a `resize` on open so ECharts (initialized 0×0 inside the hidden dialog) lays out correctly. `TreeChart` default field keys (`code`/`parent`/`name`/`description`) match both models unchanged.
- `DataTable` gained a forwarded named slot `toolbar-actions` → toolbar `actions` (renders nothing when unused, so all other pages are unaffected) for per-page toolbar buttons. No existing props/keys changed; UI-only, manual verification per Constitution III. Reused existing `menu_options.taxonomy` + `menu_options.hierarchy` i18n keys (no new keys).
- Files affected: `ui/src/pages/admin/business_units.astro`, `ui/src/components/table/DataTable.astro`, `ui/src/components/table/partials/DataTableToolbar.astro`

## 2026-06-18 04:25 — Add static HTML design mockups for asset modals (Figma import)
- Added `designs/` with self-contained HTML mockups of the asset create/edit modal (desktop + mobile 375) and the asset detail modal with its three tabs (Caracterización / Activos relacionados / Permisos), rendered from the app's Tailwind markup so a Figma import matches production.
- `designs/README.md` documents how to import into Figma (html.to.design plugin, SVG paste, or screenshot) and lists the indigo/gray design tokens. Docs/asset-only; no app code touched.
- Files affected: `designs/create-edit-modal.html`, `designs/asset-detail-tabs.html`, `designs/README.md`
## 2026-06-18 01:42 — Agent Index (HU-LI14) + reusable "big card" detail view + wider cards + value/detail fix
- **Agent Index (`/lib/agents`, HU-LI14)** shipped as the third final-user catalog and the first to use the new **hero card** (violet→indigo gradient header carrying the cpu-chip icon + name + favorite). Card face = model chip + tool chips (+N) + tags + a short INSTRUCTIONS preview; the whole card opens the detail view (Edit/Delete live there, so no per-card buttons). New `AgentCard.astro`, `AgentFormModal.astro` (grouped **Model settings** / **Behavior** sections, large INSTRUCTIONS editor), `AgentDetailModal.astro`, page `ui/src/pages/lib/agents.astro`. No backend/DB changes (menu option, `AGENTS` category + 5 specs + sample asset already seeded).
- **Reusable read-only "big card" detail view** (`CatalogDetailModal.astro` + `lib/catalogDetail.ts`) — opened by a whole-card click via the card's `data-detail-modal`. Shows the full description + configured sections (`inline`/`block`/`code`+Copy/`tools` chips), wires favorite + Edit/Delete handoff. **Wired into Prompt + MCP + Agent** (per user feedback: "view in a bigger card where all the description/instructions are visible").
- **Wider cards** everywhere: `CardGallery` grid → `repeat(auto-fill, minmax(360px, 1fr))` (was up to 4 fixed columns).
- **value/detail fix** (bug visible in the MCP screenshot: tool chips showed a summary sentence): rich payloads (TOOLS array, SERVER_CONFIG JSON, PROMPT_TEMPLATE, EXAMPLE_OUTPUT, CONTENT, INSTRUCTIONS) live in the characterization **`detail`** column, while `value` holds a short summary. `catalogModal.ts` `features` now accept `{ name, column }` so those fields read/write `detail`; pages store both columns per feature; the detail view + MCP tool chips read the correct column.
- Framework additions are **additive** (Prompt/MCP cards visually unchanged): `GalleryCard` gained opt-in `hero`/`heroClass` + `detailModalId`; `catalogGallery.ts` opens `data-detail-modal` on card click (falls back to edit); `CatalogFormModal` gained `hideDetailsHeading`.
- i18n: added `agent_modal.*`, `agent_card.*`, `catalog_detail.*` to `en.json` + `es.json`. Verified: `bunx astro check` (no new errors), `bun run build` (clean, no literal `/src/` import in the agents/prompts/mcps bundles), dev-server render of all three pages (302 auth-redirect, no SSR crash). Full click-through pending a Docker stack.
- Files affected: `ui/src/pages/lib/{agents,prompts,mcps}.astro`, `ui/src/components/lib/{AgentCard,AgentFormModal,AgentDetailModal,PromptDetailModal,McpDetailModal,PromptCard,McpCard,PromptFormModal,McpFormModal}.astro`, `ui/src/components/lib/gallery/{CardGallery,GalleryCard,CatalogFormModal,CatalogDetailModal}.astro`, `ui/src/lib/{catalogGallery,catalogModal,catalogDetail}.ts`, `ui/src/i18n/{en,es}.json`

## 2026-06-17 19:53 — MCP Directory (`/lib/mcps`, HU-LI13) on the card-gallery framework
- Implemented **HU-LI13 MCP Directory** as the second final-user card catalog, built on the reusable gallery framework from HU-LI12 (proving the extension recipe). Category-scoped view of the Asset Repository (`assets` filtered to `category='MCPS'`); no backend/DB changes (menu option, `MCPS` category + 5 specs, `EXECUTION_MODE` list, and the seeded "GitHub MCP Server" asset already existed).
- New MCP vertical: `McpCard.astro` (emerald `server-stack` accent, Mode chip with remote/local glyph, parsed `TOOLS` chips with "+N more", tags, one-click **Copy config**, edit/delete) and `McpFormModal.astro` (5 MCP fields — MODE as a select from `EXECUTION_MODE` with option **value = label** to match seeded "Remote"/"Local" data, OVERVIEW/CONTENT/TOOLS/SERVER_CONFIG). Page `ui/src/pages/lib/mcps.astro` mirrors `prompts.astro` (bundled `@/` script, `gallery-delete`→delete-modal prefill, `crud-submit`→`deleteAsset`). Tolerant `parseList()` turns the seed's array-literal `TOOLS` into chips.
- **Genericized the shared framework** so it is truly catalog-neutral for the remaining HU-LI14–19: `gallery.search_placeholder` is now generic ("Search…"), favorite tooltips moved to `gallery.favorite_add`/`favorite_remove` (referenced by `GalleryCard` + `CatalogFormModal`), and `catalogGallery.ts` gained a reusable `[data-action="copy"]` clipboard handler (used by the MCP card's Copy-config). Prompt Gallery is unaffected.
- i18n: added `mcp_modal.*` + `mcp_card.*` and the new `gallery.*` keys to both `en.json` and `es.json`. Verified: `bunx astro check` (no errors in new files), `bun run build` (clean, no literal `/src/` import in the mcps bundle), dev-server render of `/lib/mcps` + `/lib/prompts` (both compile, 302 auth-redirect). Full click-through pending a Docker stack.
- Files: `ui/src/pages/lib/mcps.astro`, `ui/src/components/lib/{McpCard,McpFormModal}.astro`, `ui/src/components/lib/gallery/{GalleryCard,CatalogFormModal}.astro`, `ui/src/lib/catalogGallery.ts`, `ui/src/i18n/{en,es}.json`.

## 2026-06-17 01:32 — Prompt Gallery (`/lib/prompts`) + reusable card-gallery foundation
- Implemented **HU-LI12 Prompt Gallery** as a final-user (consumer) card view — a Mercado-Libre-Fury-style responsive card grid, deliberately distinct from the admin `DataTable` pages. It is a category-scoped view of the Asset Repository (`assets` filtered to `category='PROMPTS'`); no backend/DB changes (the menu option, `PROMPTS` category + 5 specs, sample seed, and APIs already existed on `develop`).
- Added a **reusable, catalog-agnostic card-gallery framework** so the remaining LIB catalogs (HU-LI13–19: MCPs, Agents, Flows, Skills, Assistants, RAG Apps, Models) are built the same way with custom card/modal rendering: `CardGallery.astro` (toolbar shell: search + status filter + favorites toggle + "New" + show-more pager), `GalleryCard.astro` (card scaffold: favorite star, title/subtitle, status pill, `icon`/`chips`/`body`/`actions` slots), `lib/catalogGallery.ts` (client controller: search/filter/favorite/pagination over `[data-card]`, no DataTable dep), and `CatalogFormModal.astro` + `lib/catalogModal.ts` (create/edit modal scaffold; `mountCatalogModal({category, features, …})` saves the asset with a fixed category + upserts characterizations from feature inputs).
- Prompt vertical: `PromptCard.astro` (chat-bubble icon, model/platform/temperature chips + tags, edit/delete) and `PromptFormModal.astro` (the 5 prompt features — PLATFORM/SUGGESTED_MODEL/SUGGESTED_TEMPERATURE/PROMPT_TEMPLATE/EXAMPLE_OUTPUT — as first-class fields; defaults seeded from the category specifications).
- **Avoided a known prod bug**: the page client logic uses a bundled `@/`-alias `<script>` (Astro resolves + dedupes) instead of the inline `<script type="module">` + `/src/...` import pattern that 404s in the Vercel build (see the 2026-06-15 22:36 DataTable fix). Verified the built bundle contains no literal `/src/` import. The gallery is decoupled from the delete modal via a `gallery-delete` event the page wires to its `CrudModal`.
- i18n: added `gallery.*`, `prompt_modal.*`, `prompt_card.*` to both `en.json` and `es.json`. UI-only change → verified with `bunx astro check` (no errors in new files), `bun run build` (clean), and dev-server render (page compiles, 302 auth-redirect, no SSR crash). Full click-through pending a Docker stack (unavailable in this session).
- Files: `ui/src/pages/lib/prompts.astro`, `ui/src/components/lib/gallery/{CardGallery,GalleryCard,CatalogFormModal}.astro`, `ui/src/components/lib/{PromptCard,PromptFormModal}.astro`, `ui/src/lib/{catalogGallery,catalogModal}.ts`, `ui/src/i18n/{en,es}.json`.

## 2026-06-15 22:36 — /lib/assets responsive fixes + reset-filters button + access-level filter
- **Mobile pagination footer** compacts to ≤2 rows: grouped info + per-page select (per-page no longer `w-full`) on one row, controls on the next. (`ui/src/components/table/partials/DataTablePagination.astro`)
- **Inline asset-detail no longer overflows on mobile**: the card-view media block now exempts `tr[data-detail-row]` (renders as a full-width block panel instead of a right-aligned label/value cell); the detail tab bar wraps (`flex-wrap … sm:flex-nowrap`, `whitespace-nowrap` tabs) and characterization label/description rows wrap (`flex-wrap`, `min-w-0 break-words`). (`ui/src/styles/globals.css` card-view block, `ui/src/lib/assetDetailTabs.ts`)
- **Reset-filters button** (clears all filters + search), rendered hidden and shown only when a filter/search is active; wired generically in `advancedTable.ts` (`updateResetVisibility` + click handler). Available on every DataTable. (`partials/DataTableSearchExport.astro`, `advancedTable.ts`, i18n `data_table.reset`)
- **Access-level filter (View/Manage/Public)** added to the assets table as a **4th** DataTable filter. Extended the DataTable plumbing to `columnFilter4`/`filterOptions4`/`filterDefaultValue4`/`filter4AllLabel` (DataTable.astro → Toolbar → Filters loop → advancedTable). The 4th filter uses **membership matching** (comma-separated multi-value cell, superset of exact match). Backed by an additive `GET /api/assets/with-access` projection (`AssetWithAccessLevels`) aggregating `asset_permissions` via `array_agg(distinct access_level)` + `bool_or(target_type='PUBLIC')`; existing `GET /api/assets/` unchanged. (`api/app/lib/{routes/assets.py,internal/models.py}`, `ui/src/{types/api.ts,lib/assets.ts,pages/lib/assets.astro}`, i18n `asset_table.access_filter_*`)
- Tests: `api/tests/test_assets_access.py` locks the new endpoint's auth gate (the Postgres aggregation is verified manually on `make dev`; the SQLite test harness can't run `array_agg`/`bool_or`). UI verified via `bun run build` + dev-server render of all 4 filters + reset + 2-row footer.
- **Fixed (production-only bug): DataTable row actions + detail-expand dead on Vercel.** `DataTable.astro` bootstrapped `advancedTable.ts` via a `<script type="module" define:vars>` — `define:vars` forces the script inline/unprocessed, so its `import "/src/components/table/advancedTable"` shipped as a literal URL that 404s in the production build (works only under `astro dev`, where Vite serves `/src/`). Result: `initAdvancedTable` never ran, so row edit/delete/detail/favorite buttons (and the characterization/related/permissions tabs) never wired up. Replaced it with an inert `<script type="application/json" data-dt-config>` config carrier + one bundled module script that imports `initAdvancedTable` via the `@/` alias (Astro resolves + dedupes it) and initializes every table from its config tag. Verified the literal `/src/...` import is gone from the built bundle. (`ui/src/components/table/DataTable.astro`)
- Builds on the shared DataTable refactor already merged to `develop` (PR #49): merged `develop` in and resolved conflicts by keeping the 4th-filter/reset/footer additions on top of the merged component files.

## 2026-06-15 21:48 — Reusable parametrized DataTable column types + new desktop table design (all CRUD pages)
- Extended the shared `DataTable` column config (extend-only, no renamed keys) with parametrized field types via `as`: `title` (bold name + optional muted subtitle line), `status` (semantic pill), `tags` (chips), `date` (locale-formatted / relative), `badge`, `boolean`, `text`. New per-page `subtitleKey` + `subtitleFormat` (`relative`|`text`|`date`) drive the subtitle; added SSR `formatDate`/`formatRelative`/`renderSubtitle` helpers (locale-aware, reuse the existing `t`/`getLocale`).
- Redesigned the desktop `.datatable-dense` look in place (roomier rows, clean uppercase muted header, title+subtitle, `.dt-title`/`.dt-subtitle` hooks, dark-mode mirrored). Moved the mobile card-view title/subtitle off `:first-child`/`:nth-child(2)` heuristics onto the explicit `td[data-col="title"]` type, so column order no longer matters.
- Migrated all 19 CRUD pages to annotate their title/status/tags/date/boolean columns. The secondary field used as a subtitle is set `visible:false` (kept in `data` for export/filter/search) to avoid showing it twice. `advancedTable.ts` unchanged — search/filter/pagination/export/actions/detail-expand contract preserved (`getColumnIndex` is dead code; filters read the `data` object).
- Added `data_table` i18n keys (`updated`/`created`/`rel_ago`/`rel_now`/`unit_*`) to both `en.json` and `es.json`. Verified via `bun run build` + a throwaway sample page rendered through the dev server (title+subtitle, "Updated 2 d ago" relative, pill, date "Jan 15, 2026", check icon, chips all correct). UI-only → manual verification per Constitution III.
- Follow-up: trimmed the desktop toolbar density — filter selects, search input, and export/master-detail buttons now use `sm:py-1.5` to match the add button (mobile touch targets unchanged).
- Follow-up: made the human `name` the bold principal (title) with `code` as the muted subtitle across all 11 code+name tables (profiles, business_units, modules, options, lists, categories, features, teams, projects, dimensions, roles); previously code was the title. Pages whose entity label is a resolved `*_name` (users, privileges, assignments, specifications, assets) already lead with it. The principal/subtitle remain fully per-page configurable via `as:"title"` + `subtitleKey`/`subtitleFormat`.
- Follow-up: **modular split of the monolithic `DataTable.astro`** (god component) into an orchestrator shell + 9 sub-parts under `components/table/partials/` (`DataTableToolbar`, `DataTableFilters`, `DataTableSearchExport`, `DataTableHead`, `DataTableBody`, `DataTableCell`, `DataTableActions`, `DataTablePagination`, `DataTableEmpty`), plus extracted pure helpers in `lib/datatable.ts` (`statusTone`/`formatDate`/`formatRelative`/`renderSubtitle`) and shared types in `types/datatable.ts`. The 3 duplicated filter `<select>`s collapsed into one loop. **DOM contract is byte-identical** (proved by diffing the dev-server-rendered DOM before/after — only time/cache-buster noise differed), so `advancedTable.ts` and the card-view CSS are untouched and search/filter/pagination/export/actions/detail-expand still work.
- Files affected: `ui/src/components/table/DataTable.astro`, `ui/src/components/table/partials/*.astro` (9 new), `ui/src/lib/datatable.ts` (new), `ui/src/types/datatable.ts` (new), `ui/src/styles/globals.css`, `ui/src/i18n/{en,es}.json`, and `ui/src/pages/{admin/{users,profiles,privileges,business_units,modules,options,lists,list_items,item_translations},taxo/{categories,specifications,features},lib/assets,collab/{teams,projects,assignments,dimensions,metrics,roles}}.astro`
## 2026-06-15 18:50 — Add metrics-by-dimension endpoint

- Added `GET /api/metrics/dimension/{code}?date=` returning `List[MetricByDimension]`: latest active metric per assignment for a dimension as of the cut-off date, joined with user (name/email), role and team. The UI (`assignment.astro` → `getMetricsByDimension`) already called this route, but only the response model existed — the endpoint itself was missing, causing the browser 404.
- Dedupes assignments that share the same `measured_at` (keeps highest metric id); returns `team`/`observation` as `""` when null so the grid renders.
- Files affected: `api/app/collab/routes/metrics.py`
---

## 2026-06-15 18:40 — Assignments dashboard loads from metrics-by-dimension endpoint

- API: reworked `GET /api/metrics/dimension/{dimension_code}` to return the latest metric per assignment as of a `date` cut-off (new required query param) via a `DISTINCT ON (assignment)` join over `assignments` + `users`, instead of all raw `Metric` rows. Added a read-only `MetricByDimension` projection schema. **Contract change** on an existing endpoint: response shape changed and `date` is now required.
- UI: `collab/assignment.astro` now renders client-side from the API (dimension selector populated from `getDimensions()`, plus an as-of date picker) instead of the static `data/assignments.json` mock. Added `getMetricsByDimension()` service and `MetricByDimension` type. Saving a metric in the modal still only updates the in-memory grid — persisting edits back to the API is a separate, not-yet-wired step.
- i18n: added `assignment_dashboard` keys (`dimension`, `date`, `empty_message`) to `en.json` + `es.json`.
- Files affected: `api/app/collab/routes/metrics.py`, `api/app/collab/internal/models.py`, `ui/src/lib/metrics.ts`, `ui/src/lib/dimensions.ts`, `ui/src/types/api.ts`, `ui/src/pages/collab/assignment.astro`, `ui/src/i18n/en.json`, `ui/src/i18n/es.json`

## 2026-06-15 19:25 — Responsive UI refresh: mobile drawer, card-view tables, modal, layout, dashboard + mobile header/toolbar cleanup

Branch `feat/responsive-ui-refresh`. Refine current look + full mobile responsiveness (no rebrand). UI-only; `bun run build` passes.

- **Mobile nav drawer**: the sidebar is now an off-canvas slide-in drawer (<lg) with a dimmed backdrop, opened by the hamburger and closed on backdrop click / nav-link tap / Escape / resize-to-desktop, with page scroll lock. Desktop static sidebar + persisted collapse-to-90px behavior unchanged. New ephemeral `body.sidebar-open` state, orthogonal to `sidebar-collapsed`. (`SideBar.astro` aside classes, `BaseLayout.astro` backdrop + rewritten toggle IIFE, `globals.css` `@media (max-width:1023px)`.)
- **Responsive DataTable**: <sm each row collapses into a card via CSS only — `advancedTable.ts` untouched, so pagination/search/filter keep working (`tbody tr:not(.hidden)` preserves the `.hidden` pagination; `thead` visually hidden but kept in DOM for `getColumnIndex()`). The **first column renders as the card title and the second as a muted subtitle (no labels), with a divider beneath**; remaining columns keep their `data-label` label-left/value-right rows — giving cards real hierarchy instead of a uniform label list (matches the asset-card mockup). Columns can opt into pill rendering via `as: "status"` (a semantic colored pill — green/amber/red/indigo inferred from the status text, works across locales) or `as: "tags"` (comma value split into gray chips; stacked under its label in card view). Assets page flags `status_name`/`tags_display` accordingly. Fixed the invalid `w-100` filter selects → `w-full sm:w-auto`, search `w-56` → `w-full sm:w-56`, toolbar `flex-wrap`, per-page `ml-3` removed, pagination buttons 44px on mobile. (`DataTable.astro`, `globals.css` `@media (max-width:639px)`.)
- **Layout/padding fix**: replaced the no-op Tailwind-v4 class `max-w-(--breakpoint-2xl)` (a no-op in this v3 repo) + `md:p-0` with `max-w-screen-2xl p-4 sm:p-6 lg:p-8` in `BaseLayout`, and normalized the duplicated `mx-auto max-w-(--breakpoint-2xl) md:p-6` wrapper across all 22 pages to `mx-auto w-full max-w-full md:p-0`.
- **CrudModal**: labels stack above inputs on mobile (`flex-col sm:flex-row`, `sm:w-32` label); dialog is height-capped (`max-h-[calc(100dvh-2rem)]`) with a scrollable body and pinned header/footer.
- **Header (mobile, matches Figma mockup)**: single compact row — `toggle · brand · search · controls`. The brand (logo + "SynapxIA") shows on the left on phones; the right side carries **only the bell + account** (matching the mockup). On phones the **theme + language controls move into the account/avatar dropdown** (desktop ≥sm keeps the moon toggle + EN/ES pill in the header). Theme reuses the `data-theme-toggle` contract — `BaseLayout` now binds **all** toggles (`querySelectorAll`) so header + menu stay in sync; language reuses `setClientLocale`/`loadClientTranslations` and a `synapxia:locale-changed` event keeps both controls in sync. Account first-name hidden <sm; avatar margin trimmed <sm. The dropdown preferences are styled as a **label-left / segmented-control-right** panel: a sun/moon segmented theme control (`data-theme-set` light/dark, painted active by `BaseLayout`) + the EN/ES pill, with new `account_menu.theme`/`account_menu.language` i18n keys.
- **DataTable toolbar (mobile, matches mockup)**: full-width **"+ Activo"** primary button; a **"Filtros (N)"** toggle button (mobile-only) collapses the column-filter dropdowns into a panel that reveals on tap (always inline at `sm+`); search + export share one row. New delegated toggle script + `data_table.filters` i18n key in both `en.json`/`es.json`.
- **New `/dashboard` overview page** (`ui/src/pages/dashboard.astro`, BaseLayout): responsive KPI cards (`grid-cols-2 lg:grid-cols-4`), an asset-activity bar chart, and a recent-activity list (`grid-cols-1 lg:grid-cols-3`). KPI figures + activity feed are **placeholder/sample** values pending a backend aggregates endpoint; markup, dark mode, responsive grid and i18n are production-ready. New `dashboard_page` i18n block added to **both** `en.json` and `es.json`.
- Design refs added: private `design/responsive-preview.html` (outside `ui/public`, never deploys) + `docs/responsive-ui-implementation-plan.md`. Companion Figma mockups in a private personal Drafts file (app shell + 2 mobile frames); the CrudModal + Dashboard Figma frames are deferred (free-plan MCP quota) but both are now implemented in code.
- Files affected: `ui/src/layouts/BaseLayout.astro`, `ui/src/components/core/sidebar/SideBar.astro`, `ui/src/components/core/header/Header.astro`, `ui/src/components/table/DataTable.astro`, `ui/src/components/forms/CrudModal.astro`, `ui/src/styles/globals.css`, `ui/src/pages/dashboard.astro`, `ui/src/i18n/en.json`, `ui/src/i18n/es.json`, all `ui/src/pages/**/*.astro` wrappers, `design/responsive-preview.html`, `docs/responsive-ui-implementation-plan.md`

## 2026-06-13 23:22 — Tabbed asset modal + asset-table enhancements (filters, favorites, master-detail)

PR #45. One rollup for the whole branch (modal + table work).

- **Tabbed asset modal**: core fields are always visible at the top; the two detail collections — **Characterizations** and **Related Assets** — sit in a bottom tab group, plus a **favorite star** in the header (per-user; immediate optimistic toggle on edit, staged on create). One form + one Save: panels hide via CSS so all inputs stay in form submission, and a capture-phase `invalid` handler flips to the owning tab so native validation can focus a hidden-tab field. Create stages relations + favorite and persists them after the asset id exists; edit diffs staged-vs-initial (delete-first, create with 409→PUT reactivation fallback, update changed type/rationale).
- **i18n crash fix**: the tab `<button>`s no longer carry `data-i18n` directly — the runtime patch sets `textContent` and was wiping the nested count-badge span, nulling it and throwing in `renderRelations` on open. Labels moved into nested `<span data-i18n>`.
- **API model bug fixes (were unusable):** `AssetRelation` → real `related_assets` table, `source`/`target` as `BigInteger` FKs to `assets.id` (were `str` FKs to a non-existent `assets.code`), + the DB's `rationale` column; `Favorite` → `favorite_assets`, `asset` as BigInteger FK to `assets.id`. Mirrors the earlier Characterization `asset: str→int` fix.
- **New endpoints (additive):** `GET /api/asset_relations/source/{asset_id}`, `GET /api/assets/select`, and `GET /api/favorites/user/{user_id}` (each registered before any conflicting composite route). Relation/favorite routes use int path params; privilege gate moved from the never-seeded `ASSET_RELATIONS`/`FAVORITES` options to the seeded `(LIB, ASSETS)` (non-superusers were getting 403).
- **Asset table (Phase 1):** fixed the **Status filter** (now prefix-normalized, so seeded `IN_USE` matches the `6-IN_USE` list value); **per-row favorite star** (SSR-prefilled from the user's favorites, optimistic toggle); **"My favorites" filter** (new `columnFilter3` slot); **master-detail inline expand row** showing read-only characterizations + related assets per asset (lazy-loaded, one open at a time, purged before any table re-render so `data[rowIndex]` alignment holds). `DataTable`/`advancedTable` gained opt-in `columnFilter3`/`favoriteAction`/`detailExpand` props — other tables unaffected.
- New UI services `lib/asset_relations.ts` + `lib/favorites.ts` (`setFavorite`/`isFavorite`/`getFavoritesByUser`, handling the 404/400/409 soft-delete cases), `getAssetsSelect()` in `lib/assets.ts`, six new types in `types/api.ts`, and new `asset_detail_modal.*` + `asset_table.*` i18n keys in en + es.
- Files affected: `api/app/lib/internal/models.py`, `api/app/lib/routes/{asset_relations,favorites,assets}.py`, `ui/src/components/lib/AssetDetailModal.astro`, `ui/src/components/table/{DataTable.astro,advancedTable.ts}`, `ui/src/pages/lib/assets.astro`, `ui/src/lib/{asset_relations,favorites,assets}.ts`, `ui/src/types/api.ts`, `ui/src/i18n/{en,es}.json`

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
