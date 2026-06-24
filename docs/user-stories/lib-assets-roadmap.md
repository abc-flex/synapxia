# Lib / Asset-Management Module — Phased Implementation Roadmap

> **Status:** Phase 1 (Voting, HU-LI05) is **shipped** (PR #53, branch `feat/lib-assets-voting`).
> Phases 2–5 are scoped below and not yet started. Numbering follows the project
> user-story spreadsheet; see §4 for the mapping to `docs/user-stories/04-lib.md`.

## Context

SynapxIA is a government AI-governance platform. The `lib` module is the AI-asset
repository (prompts, MCPs, agents, …). The repository, proposal flow, asset details and
favorites already exist. This roadmap delivers the **remaining `lib` features** —
**Voting, Foro (comments & questions), Related Assets, History, Notifications** — split
into **5 review-sized PRs**, each mapped to user stories.

**Branching:** each phase branches fresh from the latest `develop`.

### Hard constraints (project decisions)
1. **NEVER create a new table.** The data model already supports every feature below via
   the generic `actions` event table and the `related_assets` table. The *only* schema-touch
   in the whole roadmap is **additive**: map the existing `workflow_status` DDL column onto
   the `Action` SQLModel (no migration — the column is already in `db/sql/41-lib-ddl.sql`).
2. **Votes are actions** (`type=VOTE`), with a **positive/negative toggle** (`content`).
3. **Notifications = workflow notifications only** (REVIEW/MODIFICATION/PUBLICATION/REJECTION
   via `workflow_status` ASSIGNED/NOTIFIED), strictly per `docs/user-stories/lib-status.md`.
   Vote/comment/Q&A do **not** generate notifications.
4. **PR labels** use the spreadsheet numbering (HU-LI05=Vote, …) with a mapping note
   to `docs/user-stories/04-lib.md` in each PR body. Do **not** edit `04-lib.md`.
5. **Lightweight planning** — this roadmap + a per-PR Constitution Check. No `specs/` folders.

---

## 1. Big-picture summary

The `actions` table (`db/sql/41-lib-ddl.sql`) is a **universal event log**:
`id, asset, user_id, type, workflow_status, content, reference, parent, detail, is_active,
created_at, updated_at`. The `ACTION_TYPE` list is **already seeded** with PROPOSAL, REVIEW,
MODIFICATION, PUBLICATION, REJECTION, DEPRECATION, VERSIONING, USAGE, **VOTE, COMMENT,
QUESTION, ANSWER**; `WORKFLOW_STATUS` is seeded with ASSIGNED/NOTIFIED/FINISHED. Therefore:

| Feature | Storage (existing) | New table? |
|---------|--------------------|-----------|
| Vote | `actions` `type=VOTE`, `content`∈{POSITIVE,NEGATIVE} | No |
| Comment / Question / Answer | `actions` `type`∈{COMMENT,QUESTION,ANSWER}, threaded via `parent` | No |
| Related Assets | `related_assets` (+ `/api/asset_relations` routes already exist) | No |
| History | read timeline over `actions` for an asset | No |
| Notifications | query over `actions` where `user_id=me` AND `workflow_status`∈{ASSIGNED,NOTIFIED} AND `type`∈{REVIEW,MODIFICATION,PUBLICATION,REJECTION} | No |

The work is therefore **service + route + UI on top of existing tables**, anchored by one
reusable backend abstraction (the **Asset Action Service**) and one reusable frontend
abstraction (the **asset-interaction components** + `ui/src/lib/actions.ts`).

The favorite feature is the **template** to mirror end-to-end:
- Backend route shape: `api/app/lib/routes/favorites.py` (by-user filter route registered
  before composite route; 409→reactivate; logical delete).
- Frontend service: `ui/src/lib/favorites.ts` (`setFavorite` toggle with 409 reactivation).
- Frontend wiring: `data-action` buttons on `GalleryCard` / `CatalogDetailModal`, optimistic
  paint + revert, SSR pre-population from `getFavoritesByUser`.

---

## 2. Recommended PR breakdown

| Phase | PR | Feature | HU (spreadsheet) | Size | Depends on | Status |
|-------|----|---------|------------------|------|-----------|--------|
| 1 | PR1 | Voting + **Asset Action Service** foundation + `workflow_status` model field | HU-LI05 | M | — | ✅ shipped (PR #53) |
| 2 | PR2 | Foro: comments, questions, answers | HU-LI06 (+HU-Comment/Question/Answer) | M | PR1 (service) | ⬜ pending |
| 3 | PR3 | Related Assets (surface existing backend on galleries) | HU-LI07 | S | — (parallelizable) | ⬜ pending |
| 4 | PR4 | History / activity timeline | HU-LI10 | M | PR1, PR2 | ⬜ pending |
| 5 | PR5 | Notifications (workflow only) | HU-LI11 (HU-Notifications) | M/L | PR1 (workflow_status); review workflow (ext.) | ⬜ pending |

Critical path: **PR1 → PR2 → PR4 → PR5**. **PR3** can run in parallel any time.

**Out of scope** (not documented enough): HU-LI08 Permission, HU-LI09 Versioning,
Deprecation. Mentioned only as future dependencies (see §13).

---

## 3. Phase-by-phase plan

### PHASE 1 / PR1 — Voting ✅ (shipped, PR #53)

1. **PR title:** `feat(lib): implement asset voting (HU-LI05)`
2. **Branch:** `feat/lib-assets-voting`
3. **User stories:** HU-LI05 — Vote (maps to repo `04-lib.md` HU-LI07 "Vote").
4. **Scope:**
   - Up/down vote on assets, stored as `actions` (`type=VOTE`, `content=POSITIVE|NEGATIVE`),
     one active vote per (user, asset); re-click toggles off, opposite click flips.
   - Vote button bar on the card galleries (`GalleryCard`/`CatalogDetailModal`) and the asset
     detail surface; net score + current-user state shown.
   - Build the reusable **Asset Action Service** (backend) + `ui/src/lib/actions.ts` (frontend).
   - **Additive model fix:** add `workflow_status` to `Action`/`ActionCreate`/`ActionUpdate`.
5. **Out of scope:** notifications on votes; comment/Q&A; history UI; review workflow.
6. **Backend tasks:**
   - `api/app/lib/internal/actions_service.py` (NEW): `list_actions_for_asset`,
     `get_user_vote`, `count_votes`, `get_vote_tally`, `set_vote` — FK validation, logical delete, 409→reactivate.
   - `api/app/lib/routes/actions.py`: add vote convenience routes mirroring favorites —
     `GET /api/actions/votes/asset/{asset_id}` (tally: positive/negative/score),
     `GET /api/actions/votes/{user_id}/{asset_id}` (current user's vote),
     `POST /api/actions/votes` (set/flip), `DELETE /api/actions/votes/{user_id}/{asset_id}`
     (clear). Register specific routes before any composite/`/{id}` route.
   - `api/app/lib/internal/models.py`: add `workflow_status: Optional[str]` to `ActionBase`
     and the Create/Update schemas (column already in DDL; purely additive).
7. **Frontend tasks:**
   - `ui/src/types/api.ts`: add `Action`, `ActionCreate`, `ActionUpdate` + a `VoteTally`
     projection (`positive`, `negative`, `score`, `my_vote`).
   - `ui/src/lib/actions.ts` (NEW): mirror `favorites.ts` — `getVoteTally(assetId)`,
     `setVote(userId, assetId, value)` (POSITIVE|NEGATIVE|null toggle handling 409 reactivation).
   - `ui/src/components/lib/gallery/` interaction bar: add vote up/down buttons
     (`data-action="vote-up"/"vote-down"`) next to the favorite star in `GalleryCard` +
     `CatalogDetailModal`; wire in `catalogGallery.ts` / `catalogDetail.ts` with optimistic
     paint+revert (mirror the favorite handler).
   - SSR pre-population on `lib/prompts.astro`, `agents.astro`, `mcps.astro`: fetch tallies +
     current user's votes, seed `data-*` on cards.
   - i18n: `gallery.vote_*` in `en.json` + `es.json`.
8. **DB/model/migration:** none (no DDL).
9. **API/contracts:** new additive routes under `/api/actions/votes/*`; `workflow_status`
   added to the action response/request schema (additive — no removed/renamed keys).
10. **Tests:** `api/tests/test_lib_votes.py` — toggle, flip, clear, reactivate, tally math,
    invalid value, route auth-gating, OpenAPI presence. Updated `test_lib.py` DDL-alignment
    test to expect `workflow_status` on `Action`.
11. **Risks/blockers:** vote uniqueness race (mitigate with pre-check + IntegrityError catch,
    as favorites does). `actions` route ordering (specific before `/{id}`).
12. **Definition of done:** can up/down/clear a vote from card + detail views; net score and
    my-vote persist across reload; tests + build green; CHANGELOG + MEMORY updated.

### PHASE 2 / PR2 — Foro (Comments & Questions)

1. **PR title:** `feat(lib): implement asset comments and questions (HU-LI06)`
2. **Branch:** `feat/lib-assets-foro`
3. **User stories:** HU-LI06 — Foro; HU-Comment, HU-Question, HU-Answer (maps to repo
   `04-lib.md` HU-LI06 "Participations" + HU-LI08 "Comment").
4. **Scope:** add/list comments (`type=COMMENT`), ask questions (`type=QUESTION`), answer
   questions (`type=ANSWER`, `parent`→question). Threaded display. Works across asset types.
   Empty/loading/error states.
5. **Out of scope:** notifications on participation; moderation/permissions; edit history.
6. **Backend tasks:** extend `actions_service.py` with `list_discussion(asset_id)` (returns
   COMMENT + QUESTION + nested ANSWER threads), `add_comment`, `add_question`, `add_answer`
   (validates `parent` is a QUESTION on the same asset). Routes in `actions.py`:
   `GET /api/actions/discussion/asset/{asset_id}`, `POST /api/actions/comments`,
   `POST /api/actions/questions`, `POST /api/actions/answers`, plus logical-delete reuse.
7. **Frontend tasks:** `ui/src/components/lib/Foro.astro` (NEW) — comment list + composer,
   Q&A list with inline answer composer, empty/loading/error states; controller
   `ui/src/lib/foro.ts` over `actions.ts`. Mount as a section/tab on `CatalogDetailModal`
   (galleries) and as a tab in the asset detail editor (`assetDetailTabs.ts`). i18n keys
   `foro.*` in both locales.
8. **DB/model/migration:** none. Optional additive seed rows.
9. **API/contracts:** additive routes under `/api/actions/{discussion,comments,questions,answers}`.
10. **Tests:** `api/tests/test_lib_foro.py` — create comment/question/answer, parent
    validation (answer must reference a question on same asset → 400), thread retrieval shape,
    logical delete.
11. **Risks/blockers:** thread depth (keep 2 levels: question→answers, comments flat).
    XSS — render user content as text, never raw HTML.
12. **Definition of done:** users can comment, ask, and answer on any asset type; threads
    render with empty/loading/error states; tests + lint + health green; CHANGELOG/MEMORY.

### PHASE 3 / PR3 — Related Assets

1. **PR title:** `feat(lib): implement related assets (HU-LI07)`
2. **Branch:** `feat/lib-assets-related-assets`
3. **User stories:** HU-LI07 — Related Assets (maps to repo `04-lib.md` HU-LI09).
4. **Scope (reduced — backend + admin editor already exist):** surface related assets as a
   **read-only section** on the card-gallery detail modals (prompts/agents/mcps), reusing
   asset cards; add **reverse/bidirectional** lookup so a target also shows its sources.
   Add/remove already exists in the asset detail editor (`assetDetailTabs.ts`).
5. **Out of scope:** new relation types; cross-module relations (INITS/PROC).
6. **Backend tasks:** add `GET /api/asset_relations/target/{asset_id}` (reverse) and a
   convenience `GET /api/asset_relations/related/{asset_id}` returning the resolved related
   **Asset** objects (both directions, de-duplicated) — mirrors the existing
   `get_by_source`. Reuse existing `asset_relations.py`.
7. **Frontend tasks:** `ui/src/lib/assetRelations.ts`: add `getRelated(assetId)`. Add a
   "Related" section to `CatalogDetailModal` (via `catalogDetail.ts` sections) rendering
   mini asset cards/links. i18n `related.*`.
8. **DB/model/migration:** none.
9. **API/contracts:** additive reverse/resolved routes; existing routes unchanged.
10. **Tests:** `api/tests/test_lib_relations.py` — reverse lookup, resolved-assets shape,
    self-relation rejection (already enforced), inactive excluded.
11. **Risks/blockers:** N+1 when resolving target assets (batch with a single `IN` query).
12. **Definition of done:** related assets appear (both directions) on gallery detail views
    and remain editable in the asset editor; tests + lint green; CHANGELOG/MEMORY.

### PHASE 4 / PR4 — History

1. **PR title:** `feat(lib): implement asset history (HU-LI10)`
2. **Branch:** `feat/lib-assets-history`
3. **User stories:** HU-LI10 — History (no direct repo story; derived from `actions`).
4. **Scope:** read-only activity timeline per asset aggregating its `actions` (creation,
   votes, comments, questions, answers, and any workflow actions present), newest first.
5. **Out of scope:** versioning/deprecation (future); permission-change audit; edits to history.
6. **Backend tasks:** extend `actions_service.py` with `get_asset_history(asset_id)` (ordered
   `actions` + asset created/updated markers). Route
   `GET /api/actions/history/asset/{asset_id}` returning typed timeline entries
   (`type`, `actor`, `summary`, `created_at`). Introduce the **Activity/History Service** as
   the read-side of the action service (no duplication).
7. **Frontend tasks:** `ui/src/components/lib/HistoryTimeline.astro` (NEW) + `ui/src/lib/history.ts`;
   mount as a section/tab on `CatalogDetailModal` and the asset detail editor. i18n `history.*`.
8. **DB/model/migration:** none.
9. **API/contracts:** additive `GET /api/actions/history/asset/{asset_id}`.
10. **Tests:** `api/tests/test_lib_history.py` — ordering (newest first), inclusion of vote/
    comment/question/answer rows, inactive excluded, empty-asset case.
11. **Risks/blockers:** actor name resolution (join users; batch). Keep summary derivation
    in the service, not the route.
12. **Definition of done:** timeline shows mixed activity for an asset in order; reuses the
    action service; tests + lint green; CHANGELOG/MEMORY.

### PHASE 5 / PR5 — Notifications (workflow only)

1. **PR title:** `feat(lib): implement asset notifications (HU-LI11)`
2. **Branch:** `feat/lib-assets-notifications`
3. **User stories:** HU-LI11 — Notifications (maps to repo `lib-status.md` "HU-Notifications").
4. **Scope (workflow only):** per `lib-status.md` — list `actions` for the current user,
   grouped by asset, whose **last** `workflow_status` is ASSIGNED (bold) or NOTIFIED
   (not bold, dismissible), and `type`∈{REVIEW,MODIFICATION,PUBLICATION,REJECTION}.
   Click-through routing (REVIEW/MODIFICATION → editor; PUBLICATION/REJECTION → show-action
   view) and status transitions: on open ASSIGNED→insert NOTIFIED; on dismiss NOTIFIED→insert
   FINISHED. Wire the header `NotificationMenu`.
5. **Out of scope:** vote/comment/Q&A activity notifications (explicitly excluded); email
   delivery; the *generation* of REVIEW/MODIFICATION/etc. assignment actions where the review
   workflow isn't yet built (see §13 dependency).
6. **Backend tasks:** **Notification Trigger Service** (read/transition side of actions):
   `list_notifications(user_id)` (group by asset, last-status logic, type filter),
   `mark_notified(action_id)`, `dismiss(action_id)` (insert FINISHED). Routes:
   `GET /api/actions/notifications` (current user from JWT),
   `POST /api/actions/notifications/{id}/notified`,
   `POST /api/actions/notifications/{id}/dismiss`. Depends on `workflow_status` (added in PR1).
7. **Frontend tasks:** `ui/src/lib/notifications.ts`; populate `NotificationMenu` (header) with
   grouped/bolded items, click-through routes, dismiss control; badge count. i18n `notifications.*`.
8. **DB/model/migration:** none (relies on PR1's `workflow_status` field).
9. **API/contracts:** additive `/api/actions/notifications*` routes.
10. **Tests:** `api/tests/test_lib_notifications.py` — last-status grouping, type filtering,
    ASSIGNED→NOTIFIED and NOTIFIED→FINISHED transitions, per-user isolation (JWT identity).
11. **Risks/blockers:** **Hard dependency** — the actions that *create* assignments
    (proposal→REVIEW/ASSIGNED, review→MODIFICATION/PUBLICATION/REJECTION) come from the
    propose/review workflow. Propose exists; confirm it inserts the REVIEW/ASSIGNED action
    (per `lib-status.md` HU-Propose). The downstream review-state machine is out of scope —
    notifications will display whatever assignment actions exist. Flag in PR if generation gaps.
12. **Definition of done:** assigned/notified workflow actions appear in the header menu with
    bold/dismiss semantics and correct click-through; transitions persist; tests + lint green;
    CHANGELOG/MEMORY.

---

## 4. User story → PR mapping

| User HU (spreadsheet) | Feature | PR | Repo `04-lib.md`/`lib-status.md` equivalent (mapping note) |
|-----------------------|---------|----|-----------|
| HU-LI05 | Vote | PR1 | HU-LI07 "Vote" |
| HU-LI06 | Foro (Comments & Questions) | PR2 | HU-LI06 "Participations" + HU-LI08 "Comment" |
| HU-LI07 | Related Assets | PR3 | HU-LI09 "Related Assets" |
| HU-LI10 | History | PR4 | (derived from `actions`; no direct story) |
| HU-LI11 | Notifications | PR5 | `lib-status.md` "HU-Notifications" |

Each PR body includes this note: *"HU-LI numbers follow the project user-story spreadsheet;
`docs/user-stories/04-lib.md` uses a different numbering — see mapping above."*

---

## 5. Branch naming plan

```
feat/lib-assets-voting
feat/lib-assets-foro
feat/lib-assets-related-assets
feat/lib-assets-history
feat/lib-assets-notifications
```
All branch from the latest `develop`.

## 6. Conventional Commit examples per PR

- PR1: `feat(lib): add asset action service and voting`,
  `feat(lib): expose workflow_status on action model`, `test(lib): add voting API tests`,
  `feat(ui): add vote bar to asset cards and detail`
- PR2: `feat(lib): add comments and questions for assets`,
  `feat(ui): add foro component to asset detail`, `test(lib): add foro API tests`
- PR3: `feat(lib): add reverse and resolved related-asset lookups`,
  `feat(ui): show related assets on gallery detail`, `test(lib): add related-asset tests`
- PR4: `feat(lib): add asset history timeline service`,
  `feat(ui): add history timeline to asset detail`, `test(lib): add history API tests`
- PR5: `feat(lib): add workflow notifications service`,
  `feat(ui): wire notification menu`, `test(lib): add notification API tests`,
  `docs(lib): document notification triggers`

## 7. Dependencies between phases

- **PR1** is foundational (Asset Action Service + `actions.ts` + interaction bar +
  `workflow_status`). No upstream deps.
- **PR2** reuses the service/components from PR1.
- **PR3** is independent (existing backend) → parallelizable.
- **PR4** reads votes (PR1) + participations (PR2) for a meaningful timeline.
- **PR5** needs `workflow_status` (PR1) and the review-workflow assignment actions (external,
  partially out of scope).

## 8. Reusable abstractions

- **Asset Action Service** — `api/app/lib/internal/actions_service.py` (PR1): create/query/
  toggle/logical-delete actions by type with FK validation; single place all action features
  build on (votes, foro, history, notifications). Avoids per-feature duplication.
- **Activity/History Service** — read-side aggregation in the same module (PR4).
- **Notification Trigger Service** — last-status grouping + ASSIGNED→NOTIFIED→FINISHED
  transitions (PR5).
- **Shared asset-interaction components (frontend)** — vote/favorite interaction bar (PR1),
  `Foro.astro` (PR2), `HistoryTimeline.astro` (PR4), all backed by `ui/src/lib/actions.ts`.

## 9. Backend impact

`api/app/lib/internal/models.py` (additive `workflow_status`), new
`api/app/lib/internal/actions_service.py`, extended `api/app/lib/routes/actions.py` and
`asset_relations.py` (additive routes only). All routes use `get_db_session` +
`require_privilege("LIB","ACTIONS"/"ASSETS", …)`, skip/limit pagination, logical delete,
409/400/404 conventions. **No endpoint/key removed or renamed** (Constitution II).

## 10. Frontend impact

New `ui/src/lib/{actions,foro,history,notifications,assetRelations(extend)}.ts`; new
components `Foro.astro`, `HistoryTimeline.astro`, vote bar in `GalleryCard`/`CatalogDetailModal`;
sections wired via `catalogDetail.ts`/`assetDetailTabs.ts`; `NotificationMenu` populated. Three
interfaces per new entity in `types/api.ts`; every string keyed in `en.json` + `es.json`.

## 11. Database / migration impact

**Zero new tables. Zero DDL changes.** `workflow_status` already exists in
`db/sql/41-lib-ddl.sql`; PR1 only maps it in Python. Optional additive seed rows in
`42-lib-insert.sql` (effective on `make rebuild`). Destructive changes: none.

## 12. Testing strategy

pytest mirrors `api/tests/conftest.py` (in-memory SQLite + `get_db_session` override) and the
`test_users.py`/`test_lib.py` style: one `test_lib_<feature>.py` per PR covering create/toggle/
validation/logical-delete/contract shape and (PR5) per-user isolation + status transitions.
Update `test_lib.py` DDL-alignment test for `workflow_status`. Run `make pytest`, `make test`
(health), `make lint`, `make fmt-check`, `make lint-ui` each PR. UI: manual verification per
`make dev` (admin / Admin123!) — vote/foro/related/history/notifications flows.

## 13. Risks, blockers & open questions

- **Notification generation dependency (PR5):** assignment actions are produced by the
  propose/review workflow. Propose exists; the review state-machine (repo HU-LI03/`lib-status.md`
  HU-Review/HU-Modify) is **not** fully in code and is out of scope. PR5 displays/transitions
  existing assignment actions; if generation gaps exist, flag in the PR rather than expanding scope.
- **Out of scope (future phases):** HU-LI08 Permission, HU-LI09 Versioning (+ Deprecation).
  Versioning will *reuse* `actions` (`type=VERSIONING`) + `related_assets` (`EXTENDS`) — still
  no new table. Future-compatible only; not built now.
- **Numbering mismatch** with `04-lib.md` is documented per-PR (not corrected in the doc).
- **Vote semantics:** one active vote per (user, asset); flipping replaces content; re-click
  clears (logical delete + 409→reactivate, mirroring favorites).
- **Action route ordering:** specific routes (`/votes/...`, `/discussion/...`,
  `/notifications`) must register before any `/{id}` route to avoid path capture.

## 14. Final roadmap table

| Phase | PR | Branch | Title | HU | New tables | Key new files |
|-------|----|--------|-------|----|-----------|---------------|
| 1 | PR1 | `feat/lib-assets-voting` | `feat(lib): implement asset voting (HU-LI05)` | HU-LI05 | 0 | `lib/internal/actions_service.py`, `ui/src/lib/actions.ts`; +`workflow_status` |
| 2 | PR2 | `feat/lib-assets-foro` | `feat(lib): implement asset comments and questions (HU-LI06)` | HU-LI06 | 0 | `ui/src/components/lib/Foro.astro`, `ui/src/lib/foro.ts` |
| 3 | PR3 | `feat/lib-assets-related-assets` | `feat(lib): implement related assets (HU-LI07)` | HU-LI07 | 0 | reverse/resolved routes, `getRelated` |
| 4 | PR4 | `feat/lib-assets-history` | `feat(lib): implement asset history (HU-LI10)` | HU-LI10 | 0 | `HistoryTimeline.astro`, `ui/src/lib/history.ts` |
| 5 | PR5 | `feat/lib-assets-notifications` | `feat(lib): implement asset notifications (HU-LI11)` | HU-LI11 | 0 | notifications service/routes, `ui/src/lib/notifications.ts` |

---

## Verification (per PR, before push)

1. `make test` — API health, DB, admin user.
2. `make pytest` — new + existing backend tests green (esp. `test_lib*.py`).
3. `make lint` + `make fmt-check` (API) and `make lint-ui` (UI) — no drift.
4. `make dev` then log in (admin / Admin123!) and exercise the feature end-to-end on
   `/lib/prompts` (+ `agents`, `mcps`) and `/lib/assets`. If seed rows were added, `make rebuild`.
5. Update `memory/CHANGELOG.md` (one rollup entry per PR, `YYYY-MM-DD HH:MM`) and
   `memory/MEMORY.md` (feature status), per AGENTS.md mandatory update rules.

## Process / Git

- Branch from latest `develop` per phase; `git push -u origin <branch>` (retry on network
  error with backoff). **Do not open PRs unless explicitly asked.**
- Conventional Commits; atomic, logically grouped commits.
- No new tables, no removed/renamed API keys, JWT+bcrypt auth preserved, secrets via env only.
