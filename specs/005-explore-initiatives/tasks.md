---
description: "Task list for Explore Initiatives, Propose Initiative & Initiative Notifications"
---

# Tasks: Explore Initiatives, Propose Initiative & Initiative Notifications

**Input**: Design documents from `/specs/005-explore-initiatives/`

**Prerequisites**: plan.md, spec.md, research.md (R1–R16), data-model.md, contracts/initiatives-workflow-api.md, contracts/ui-surfaces.md, quickstart.md

**Tests**: REQUIRED. Constitution Principle III mandates automated tests for contract, permission and workflow-transition changes (plan § Constitution Check III). Backend test tasks precede the implementation in each story. UI behaviour is verified through quickstart.md scenarios, since there is no browser harness.

**Organization**: Tasks are grouped by user story (spec.md US1–US8), so each story can be implemented and tested as an increment.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: US1–US8 from spec.md
- Paths are relative to the repo root (`api/`, `ui/`, `db/`, `docs/`, `memory/`)

**Conventions to follow in every task** (so no other context is needed):
- **API.** Domain split: `internal/` holds logic and schemas, `routes/` holds HTTP.
  - Routes return bare models and raise `HTTPException`; the global envelope wraps them.
  - Error mapping: `ValueError` → 400, `*Forbidden` → 403, `*Conflict` → 409, and `IntegrityError` → rollback + 409.
  - Actors always come from `current_active_user`, never from the body.
- **Tests.** Run with `docker compose exec -T api uv run pytest -q`; the baseline is 8 pre-existing failures in `test_auth`, `test_health` and `test_users`. Use `api/tests/inits_helpers.py` (`user`, `superuser`, `override`, `mk_user_row`, `seed_privileges`, `mk_init`, `mk_perm`, `mk_fav`, `mk_list`, `seed_core_lists`, `mk_criteria`, `mk_diag`, `data`) and the `session`/`client` fixtures from `api/tests/conftest.py`.
- **UI.**
  - Svelte 5 islands are mounted manually with `mount()` from a bundled `<script>`, never with `@astrojs/svelte`.
  - Every user-facing string goes in both `ui/src/i18n/en.json` and `es.json`.
  - Services live in `ui/src/lib/*.ts` around `lib/api.ts`, which unwraps `.data`.
  - Toggles use the Show/Hide switch style: right-aligned, collapsed by default.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Seed changes and test helpers that every story relies on.

- [X] T001 [P] In `db/sql/12-admin-insert.sql`, change `('COLLABORATOR','INITS','EXPLORE', FALSE)` and `('REVIEWER','INITS','EXPLORE', FALSE)` to `TRUE` (research R4), and add a one-line SQL comment explaining that Explore is the participation surface.
- [X] T002 [P] In `db/sql/52-inits-insert.sql`, delete the collaborations seed row with id 8 (`DELIVERY` / `PENDING`) (research R7). Do NOT renumber the other ids; the existing `setval(..., MAX(id))` still applies.
- [X] T003 [P] Extend `api/tests/inits_helpers.py`. Add:
  - `mk_collab(session, init, user_id, type, workflow_status=None, content=None, parent=None, created_at=None, active=True)`;
  - `seed_criteria_with_scale(session, codes=("C1","C2"), values=(1,2,3))`, which creates one `CRITERIA`-type list per code with `en` + `es` `list_items` rows plus an active `Criteria` row;
  - `mk_asset(session, id, name="Asset", category="PROMPTS", status="PUBLISHED")`;
  - `mk_asset_perm(session, asset, target_type="USER", target_code="1", access_level="VIEW")`, using the lib `Asset` / `AssetPermission` models.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The shared reviewer rule, schemas, answer validation and the single-collaboration read. All stories depend on these.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 Create `api/app/internal/reviewers.py`.
  - **Moved from `api/app/lib/internal/propose_service.py` unchanged in behaviour:** `REVIEWER_PROFILES`, `ADMIN_PROFILES`, `is_eligible(user)` (was `_is_eligible`), `is_admin(user)`, `list_reviewers(session, exclude_user_id=None)` and `resolve_reviewer(session, reviewer_id, proposer=None)`. Auto-assignment picks the lowest-id eligible user minus the excluded proposer. The same `ValueError` messages are kept.
  - **Module docstring:** it is shared by `lib` and `inits` (research R2).
- [X] T005 Refactor `api/app/lib/internal/propose_service.py` to import the names moved in T004 and re-export them: keep `_is_eligible = is_eligible` as an alias, so existing imports in `review_service.py`, `routes/assets.py` and the tests keep working. Then run `test_lib_propose.py`, `test_lib_review.py` and `test_lib_modify.py`; they must pass unchanged.
- [X] T006 [P] Create `api/tests/test_internal_reviewers.py`. Cover: eligible profiles plus superuser; inactive users excluded; non-admin proposer excluded from the list and refused when self-selected; admin proposer allowed to self-select; auto-assign picks the lowest eligible id; `ValueError` when nobody is eligible.
- [X] T007 Add the new schemas to `api/app/inits/internal/models.py`, per data-model.md:
  - `DiagnosisAnswer`, `InitiativeProposeRequest` (with `assets: List[ProposeAssetLink{asset, type, rationale?}]`), `InitiativeDiagnoseRequest`, `InitiativeResubmitRequest`;
  - `LinkableAsset`, `InitVoteTally`, `InitiativeExploreItem`, `InitiativeRequest`;
  - `InitNotificationItem`, `InitNotificationFeed`, `CollaborationDetail` (`Collaboration` fields + `initiative` + `actor_name`).
  - Length limits: name ≤ 100, description ≤ 500, feedback/rationale ≤ 2000.
- [X] T008 Create `api/app/inits/internal/criteria_validation.py` with:
  - `active_criteria(session) -> List[Criteria]`;
  - `scale_values(session, criteria) -> Dict[str, Set[int]]`: the integer `list_items.value` where `list = criteria.list` and `lang = 'en'`, in one batched query;
  - `validate_creator_answers(session, answers: Dict[str, DiagnosisAnswer])`;
  - `validate_reviewer_answers(session, answers: Dict[str, int])`.

  Both validators raise `ValueError` when an active criterion is missing, a code is unknown or inactive, or a score is outside the scale. With zero active criteria, an empty dict is accepted (research R10).
- [X] T009 Add to `api/app/inits/internal/models.py` or a new `api/app/inits/internal/list_validation.py` a helper `validate_list_value(session, list_code, value, required)`. It validates `INITIATIVE_TYPE`, `EXPECTED_IMPACT`, `PRIORITY_LEVEL` and `RELATION_TYPE` values. Reuse the existing list-value check from `api/app/inits/routes/initiatives.py` PUT: move it into this helper and call it from both places.
- [X] T010 [P] Create `api/tests/test_inits_criteria_validation.py`. Cover: complete and valid answers; a missing criterion; an unknown code; an inactive criterion ignored; an out-of-scale value; the zero-criteria case; blank rationale normalised to None.
- [X] T011 In `api/app/inits/routes/collaborations.py`, add `GET /api/collaborations/{collab_id}` → `CollaborationDetail`, declared LAST so it stays after any static paths.
  - **Access:** `current_active_user`, and 404 unless `row.user_id == current.id` or the caller is a superuser.
  - **Payload:** embeds `initiative` (the full row) and `actor_name` (contract #13).
- [X] T012 [P] Add tests for T011 in `api/tests/test_inits_requests.py`, creating the file: owner gets 200 with the embedded initiative; another user gets 404; superuser gets 200; a missing id gets 404.
- [X] T013 [P] Add the TypeScript types to `ui/src/types/api.ts`, mirroring T007: `DiagnosisAnswer`, `InitiativeProposeRequest`, `InitiativeDiagnoseRequest`, `InitiativeResubmitRequest`, `LinkableAsset`, `InitVoteTally`, `InitiativeExploreItem`, `InitiativeRequest`, `InitNotificationItem`, `InitNotificationFeed`, `CollaborationDetail`.
- [X] T014 [P] Add `getCollaboration(id): Promise<CollaborationDetail>` to `ui/src/lib/collaborations.ts`, calling `GET /api/collaborations/{id}`.
- [X] T015 Extract `ui/src/components/svelte/DiagnosisTable.svelte` from the diagnosis tab of `ui/src/components/svelte/InitiativeDetailTabs.svelte` (`loadDiagnosis` markup, score cards, `answerCell` / `rationaleToggle` snippets).
  - **Props:** `rows: DiagnosticRow[]`, `mode: "view" | "propose" | "review" | "modify"`, `status?: string`, `onChange?: (answers) => void`.
  - **Exported method:** `validate(): string[]`, which returns the codes of unanswered criteria.
  - **Behaviour per mode** follows contracts/ui-surfaces.md § DiagnosisTable:
    - `propose`: a scale `<select>` per row plus a rationale textarea behind a Show/Hide switch; proposer card only, with a live total.
    - `review`: the proposer column is read-only with its rationale toggle, and the reviewer column is editable; live reviewer total.
    - `modify`: the proposer column is editable and prefilled, and the reviewer column is read-only, labelled "Previous review".
    - `view`: the current rendering, with reviewer values hidden while `status === "ACTIVATED"`.
- [X] T016 Make `ui/src/components/svelte/InitiativeDetailTabs.svelte` render `<DiagnosisTable mode="view" …>` in place of its inline diagnosis markup. The visual output must be unchanged; check it on `/inits/initiatives`.
- [X] T017 [P] Add the `inits_diagnosis.*` i18n keys to `ui/src/i18n/en.json` and `es.json`: proposer, reviewer, previous_review, rationale_show, rationale_hide, total, unanswered.

**Checkpoint**: The reviewer rule is shared and the lib suites are green. Schemas, validation and the collaboration read exist, and the diagnosis table is reusable.

---

## Phase 3: User Story 1 — Propose an initiative and request its diagnosis (Priority: P1) 🎯 MVP

**Goal**: A user proposes an initiative through Core Fields → Diagnosis Questions → Related Assets. "Request diagnosis" records everything in one transaction (FR-011 – FR-017, FR-021 – FR-024).

**Independent Test**: As `adriana.velez`, complete the wizard and submit. The DB then shows the ACTIVATED initiative, 6 diagnostics rows, the link, ACTIVATION/HANDLED + DIAGNOSIS/PENDING, and two MANAGE grants (quickstart Scenario 2).

### Tests for User Story 1

- [X] T018 [P] [US1] Create `api/tests/test_inits_propose.py` (service + route).
  - **Happy path:** one call creates the initiative (ACTIVATED, score None), one diagnostics row per criterion (`creator_score`, `rationale`), the `asset_inits` rows, ACTIVATION/HANDLED for the proposer, DIAGNOSIS/PENDING for the reviewer, and USER/MANAGE grants for both. An admin self-review yields one grant.
  - **400 with NOTHING persisted:** blank name; invalid or missing `expected_impact` / `priority_level`; invalid `type`; incomplete, unknown or out-of-scale answers; an invisible or inactive asset; an invalid relation type; a duplicate `(asset, type)`; a non-admin self-review; no eligible reviewer.
  - **Access:** 403 without the `INITS` edit privilege. A COLLABORATOR holding `INITS/EXPLORE` with `can_edit` gets 201.
  - **Attribution:** the actor comes from the session.

### Implementation for User Story 1

- [X] T019 [US1] Create `api/app/inits/internal/propose_service.py` with `propose_initiative(session, proposer: User, data: InitiativeProposeRequest) -> Initiative`.
  - **Validate first (any failure → `ValueError`):**
    - core fields via T009;
    - answers via T008 `validate_creator_answers`;
    - reviewer via `app.internal.reviewers.resolve_reviewer(session, data.reviewer_id, proposer)`;
    - each asset active and visible: superuser, or `lib.internal.permissions_service.user_asset_access` not None;
    - relation types valid, no duplicate `(asset, type)`.
  - **Then in one `try` / commit:**
    1. insert `Initiative(status="ACTIVATED")` and flush;
    2. `Diagnostic` rows;
    3. `AssetInit` rows;
    4. `Collaboration(ACTIVATION, HANDLED)` for the proposer;
    5. `Collaboration(DIAGNOSIS, PENDING)` for the reviewer;
    6. `InitPermission(USER, str(id), MANAGE)` for each id in `{proposer.id, reviewer.id}`.
  - **On `IntegrityError`:** rollback and re-raise.
- [X] T020 [US1] In `api/app/inits/routes/initiatives.py`, add `GET /api/initiatives/linkable-assets` → `List[LinkableAsset]`. It is gated by `check_any_privilege(session, user, "INITS", ["EXPLORE","INITIATIVES"])` and returns active assets the caller can see (superuser: all; otherwise ids from `lib` `accessible_assets`), ordered by name. Declare it before `/{init_id}`.
- [X] T021 [US1] In `api/app/inits/routes/initiatives.py`, add `POST /api/initiatives/propose` → `Initiative`, 201.
  - **Gate:** `check_any_privilege(..., ["EXPLORE","INITIATIVES"], can_edit=True)`.
  - **Behaviour:** calls T019 and maps `ValueError` → 400, and `IntegrityError` → rollback + 409 "Could not propose the initiative due to a data conflict".
  - **Order:** declare it before `/{init_id}`.
- [X] T022 [P] [US1] Add a test for `/linkable-assets` to `api/tests/test_inits_propose.py`: VIEW-granted assets are listed, ungranted ones are not, and a superuser sees all.
- [X] T023 [P] [US1] Create `ui/src/lib/ackDialog.ts` and `ui/src/components/ui/AckDialog.astro` by extracting `showAckDialog(message, variant)` and the `#propose-ack-dialog` markup from `ui/src/pages/lib/propose.astro`. Keep the blocking behaviour: Esc is `preventDefault()`ed, and the promise resolves only on "Got it". The component takes an `id` prop, so two pages don't collide.
- [X] T024 [US1] Make `ui/src/pages/lib/propose.astro` use `AckDialog.astro` + `lib/ackDialog.ts` (T023). Asset propose behaviour must be byte-for-byte equivalent; confirm by proposing an asset.
- [X] T025 [P] [US1] Add to `ui/src/lib/initiatives.ts`: `getLinkableAssets()` → `GET /api/initiatives/linkable-assets`, and `proposeInitiative(payload)` → `POST /api/initiatives/propose`.
- [X] T026 [US1] Create `ui/src/pages/inits/propose.astro` (BaseLayout, Breadcrumb "Explore Initiatives › Propose Initiative"). Use `components/ui/Tabs.astro` with tabs `core`, `diagnosis`, `related`, plus `FormField.astro`, `Button.astro` and `lib/formClasses.ts`.
  - **Core panel:** name*, description, type (`INITIATIVE_TYPE`), expected impact* (`EXPECTED_IMPACT`), priority* (`PRIORITY_LEVEL`), reference, tags and detail, with options from `getListItemsbyList(code)` filtered by the current language. No status field.
  - **Diagnosis panel:** mounts `DiagnosisTable` in `propose` mode, with rows built from `getCriterias()` + `getListItemsbyList(criteria.list)`. When there are no active criteria it shows `inits_propose.no_criteria`.
  - **Related panel:** a target asset select from `getLinkableAssets()`, a relation type select (`RELATION_TYPE`), a rationale input, "Add relation", and a staged list with Remove. It mirrors the `#propose-rel-*` markup and the `addRelation` / `buildStagedRow` logic of `pages/lib/propose.astro`. A duplicate `(asset, type)` shows `inits_propose.related_duplicate`.
  - **Footer:** `#inits-propose-back` (ghost, `inits_propose.back`), `#inits-propose-submit-secondary` (secondary, `inits_propose.submit`, visible only on `diagnosis`), and `#inits-propose-submit` (primary).
  - **Step labels:** `stepOrder = ["core","diagnosis","related"]`. `NEXT_STEP_LABEL = {diagnosis: "inits_propose.next_diagnosis", related: "inits_propose.next_related"}`. The last step reads `inits_propose.submit`, and `DIRECT_SUBMIT_TABS = ["diagnosis"]`. This gives 2 / 3 / 2 visible buttons (FR-013, FR-015, FR-017).
  - **Validation:** "Diagnosis questions >" validates core. Any submit validates core, then `DiagnosisTable.validate()`, activating the first invalid tab and marking its fields with `setFieldInvalid` + a toast (`inits_propose.required` / `inits_propose.answers_required`).
  - **Double submission:** an in-flight flag disables both submit buttons.
  - **Payload:** built per contract #4.
  - **Outcome:** `showAckDialog(tr("inits_propose.success"), "success")`, then `window.location.href = "/inits/explore"`. On failure it shows the server message and keeps the form intact.
  - **Back:** "Back to initiatives" goes to `/inits/explore` with no save.
- [X] T027 [P] [US1] Add the `inits_propose.*` keys to `ui/src/i18n/en.json` and `es.json`: title, subtitle, tab_core, tab_diagnosis, tab_related, next_diagnosis ("Diagnosis questions >" / "Preguntas de diagnóstico >"), next_related ("Related Assets >" / "Activos relacionados >"), submit ("Request diagnosis" / "Solicitar diagnóstico"), back ("Back to initiatives" / "Volver a iniciativas"), required, answers_required, related_hint, related_duplicate, success (mentions My Initiative Requests), failure, no_criteria.

**Checkpoint**: Proposals are fully recorded. They are visible in Initiative Management (`/inits/initiatives`) to the proposer and reviewer through their MANAGE grants.

---

## Phase 4: User Story 2 — Choose the reviewer exactly as in Propose an asset (Priority: P1)

**Goal**: The Core Fields tab has a reviewer select with the asset eligibility rule, self-exclusion and auto-assignment (FR-018 – FR-020).

**Independent Test**: As `santiago.marin` (REVIEWER), the list excludes them; as `admin`, it includes admin. A submission with no reviewer is auto-assigned, never to the non-admin proposer (quickstart Scenario 2, steps 2 and 9).

### Tests for User Story 2

- [X] T028 [P] [US2] Add route tests for `GET /api/initiatives/reviewers` to `api/tests/test_inits_propose.py`:
  - a non-admin caller is excluded from the list, and an admin caller is included;
  - 403 without any `INITS` privilege;
  - a propose with no `reviewer_id` is assigned the lowest eligible id other than the non-admin proposer.

### Implementation for User Story 2

- [X] T029 [US2] In `api/app/inits/routes/initiatives.py`, add `GET /api/initiatives/reviewers` → `List[ReviewerOption]` (import the model from `app.lib.internal.models`).
  - **Gate:** `check_any_privilege(..., "INITS", ["EXPLORE","INITIATIVES"])`.
  - **Exclusion:** `exclude = None if is_admin(current) else current.id`, then `list_reviewers(session, exclude)`, mapped like `lib/routes/assets.py` `/reviewers`.
  - **Order:** declare it before `/{init_id}`.
- [X] T030 [P] [US2] Add `getInitiativeReviewers()` → `GET /api/initiatives/reviewers` to `ui/src/lib/initiatives.ts`.
- [X] T031 [US2] In `ui/src/pages/inits/propose.astro`, add the reviewer select to the Core panel.
  - **Placeholder:** `inits_propose.reviewer_auto` ("Auto-assign"), which omits `reviewer_id`.
  - **Options:** `label — role`, using `reviewer_role.*`, mirroring `fillReviewers` in `pages/lib/propose.astro`.
  - **Payload:** send `reviewer_id` only when chosen, and surface the server's self-review 400 inline on the field.
- [X] T032 [P] [US2] Add the `inits_propose.reviewer` and `inits_propose.reviewer_auto` keys to `ui/src/i18n/en.json` and `es.json`.

**Checkpoint**: US1 + US2 together form the P1 propose MVP.

---

## Phase 5: User Story 3 — Browse the initiative portfolio (Priority: P1)

**Goal**: The Explore Initiatives gallery: Accepted, In Progress and Delivered initiatives the user can access, the six-option privilege filter, favorites, search, votes, full-width rows, "+ Propose", and a read-only detail on card click (FR-001 – FR-010).

**Independent Test**: As `adriana.velez`, each privilege option shows only initiatives shared through that scope; ACTIVATED initiatives never appear; favorites and votes work; a card opens the 5-tab detail; the page is usable at 390 px (quickstart Scenario 1).

### Tests for User Story 3

- [X] T033 [P] [US3] Create `api/tests/test_inits_votes.py`:
  - positive vote; the same value toggles it off; the other value switches it;
  - DELETE clears it, and returns 404 without an active vote;
  - at most one active VOTE row per `(user, init)`;
  - the tally counts only active votes, with `my_vote` per caller;
  - an invalid content returns 400; no VIEW returns 403; no edit privilege returns 403;
  - the voter is always the session user;
  - vote rows have `workflow_status` NULL.
- [X] T034 [P] [US3] Create `api/tests/test_inits_explore.py`:
  - only ACCEPTED, IN_PROGRESS and DELIVERED initiatives are returned (ACTIVATED, FEEDBACK, REJECTED, ARCHIVED and inactive ones excluded);
  - only initiatives the caller can access are returned, and a superuser sees all;
  - filtering happens BEFORE `skip` / `limit`;
  - `permission_scopes`, `is_favorite` and `my_access` are correct;
  - `votes`, `discussion_count` (active COMMENT, QUESTION and ANSWER) and `related_assets_count` (active links) are correct;
  - the endpoint is reachable with `INITS/EXPLORE` only;
  - ordering is `created_at` desc.

### Implementation for User Story 3

- [X] T035 [P] [US3] Create `api/app/inits/internal/votes_service.py`:
  - `get_vote_tally(session, init_id, user_id=None) -> InitVoteTally`;
  - `tallies_for(session, init_ids, user_id) -> Dict[int, InitVoteTally]`: one grouped query plus one query for the user's votes;
  - `set_vote(session, user_id, init_id, content)`: deactivates the existing active vote; the same value only withdraws it; `workflow_status` None; commit;
  - `clear_vote(session, user_id, init_id)`: raises `LookupError` when there is no active vote.
- [X] T036 [P] [US3] Create `api/app/inits/internal/explore_service.py` with `EXPLORE_STATUSES = ("ACCEPTED","IN_PROGRESS","DELIVERED")` and `list_explore(session, user, skip, limit) -> List[InitiativeExploreItem]`.
  - **Access:** a superuser sees all active initiatives; otherwise use `accessible_inits(session, user)` ids.
  - **Filter:** status via `app.internal.status.normalize` ∈ `EXPLORE_STATUSES`, ordered by `created_at` desc then `id` desc, filtered BEFORE `skip` / `limit`.
  - **Per page:** `inits_user_scopes`, favorites (one query), `tallies_for`, grouped discussion counts and grouped `asset_inits` counts, each a single `GROUP BY init` query over the page's ids.
- [X] T037 [US3] In `api/app/inits/routes/initiatives.py`, add `GET /api/initiatives/explore?skip=0&limit=100` (`limit` 1–500) → `List[InitiativeExploreItem]`, gated by `check_any_privilege(..., ["EXPLORE","INITIATIVES"])`. Declare it before `/{init_id}`.
- [X] T038 [US3] In `api/app/inits/routes/collaborations.py`, add the vote routes, declared before `/{collab_id}`:
  - `GET /votes/init/{init_id}` → `InitVoteTally`: read gate, active initiative, VIEW;
  - `PUT /votes/init/{init_id}` with body `{content}` → `InitVoteTally`: the `_gate_write` pattern (edit privilege + VIEW); `ValueError` → 400;
  - `DELETE /votes/init/{init_id}` → `InitVoteTally`: `LookupError` → 404;
  - `IntegrityError` → 409.
- [X] T039 [P] [US3] Add to `ui/src/lib/initiatives.ts` `getInitiativesExplore(skip=0, limit=500)`, and to `ui/src/lib/collaborations.ts` `getInitiativeVoteTally(id)`, `setInitiativeVote(id, content)` and `clearInitiativeVote(id)`.
- [X] T040 [US3] Add an optional prop `layout?: "grid" | "list"` (default `"grid"`) to `ui/src/components/lib/gallery/CardGallery.astro`. `"list"` renders the slot container as a single-column stack (`flex flex-col gap-4`) instead of the auto-fill grid. Existing callers (`pages/lib/explore.astro`) must be unchanged.
- [X] T041 [US3] Extend `initCardGallery` in `ui/src/lib/catalogGallery.ts` with an optional `idAttr` (default `"assetId"`) and an optional `services`:

  ```ts
  { toggleFavorite(id, on): Promise<void>; vote(id, value: "POSITIVE"|"NEGATIVE"|null): Promise<{positive,negative,my_vote}>; tally(id): Promise<{positive,negative,my_vote}> }
  ```

  The defaults wrap today's asset calls (`setFavorite`, `setVote`, `getVoteTally`). The synthetic discuss and card openers must set `data-${kebab(idAttr)}` instead of the hard-coded `data-asset-id`. Asset gallery behaviour must be unchanged (verify `/lib/explore?code=PROMPTS`).
- [X] T042 [P] [US3] Create `ui/src/components/inits/InitiativeCard.astro`, a full-width row card.
  - **Data attributes:** `<article data-card data-id data-search data-favorite data-permissions data-detail-modal="inits-view-modal">`.
  - **Accent:** a left bar coloured by status (ACCEPTED indigo, IN_PROGRESS amber, DELIVERED emerald).
  - **Header:** name, status pill (label passed in), chips for type / priority / expected impact, and the relative time.
  - **Body:** a two-line clamped description and `#tags`.
  - **Footer:** the vote bar using the same `data-action="vote-up|vote-down"` + `[data-vote-up-count]` / `[data-vote-down-count]` hooks as `GalleryCard.astro`, the `data-action="discuss"` button with `[data-discuss-count]`, a related-assets count (`inits_explore.related_count`), and the `data-action="favorite"` star.
  - **Small screens:** stacked below `sm`, with no version pill.
- [X] T043 [P] [US3] Create `ui/src/components/svelte/InitiativeDetailView.svelte`, a read-only view island.
  - **Props:** `modalId`, `onVoteChange?`, `onFavoriteChange?`.
  - **Exported method:** `open(item: InitiativeExploreItem)`.
  - **Tabs:**
    - Core Fields (read-only fields with list labels);
    - Diagnosis Questions (`DiagnosisTable` mode `view`, data from `getInitiativeDiagnostics(id, lang)`);
    - Related Assets (read-only list from `getInitiativeAssets(id)`);
    - Discussion (`<Foro modalId={modalId} api={initiativeForoApi} idAttr="initId" />`);
    - History (a `<section id="{modalId}-history">` shell with `[data-history-status]` and `[data-history-list]`).
  - **Header:** a vote bar and favorite that call the T039 services and `setInitiativeFavorite`.
  - **Not shown:** no Permissions tab and no save controls.
- [X] T044 [US3] Create `ui/src/components/inits/InitiativeExploreModal.astro`, a `<dialog id={modalId}>` shell.
  - It mounts `InitiativeDetailView` with `mount()` and calls `mountHistory({ modalId, fetcher: getInitiativeHistory, idAttr: "initId", labelNamespace: "initiative_history.action" })`.
  - On a `[data-modal-open=modalId]` click it reads `data-init-id` and opens the view with the matching item from a `window`-scoped JSON map the page provides (id → `InitiativeExploreItem`).
  - `data-foro-focus` activates the Discussion tab.
  - Card and modal stay in sync: vote and favorite changes dispatch `datatable`-style events that `initCardGallery` repaints.
- [X] T045 [US3] Create `ui/src/pages/inits/explore.astro` (BaseLayout, Breadcrumb from `getOption("INITS","EXPLORE")` name and icon).
  - **SSR:** `getInitiativesExplore()`, plus list labels for `INITIATIVE_STATUS`, `INITIATIVE_TYPE`, `PRIORITY_LEVEL` and `EXPECTED_IMPACT` in the current language.
  - **Privilege options:** `PRIVILEGE_OPTIONS`, identical to `pages/lib/explore.astro`.
  - **Gallery:** `<CardGallery galleryId="inits-gallery" layout="list" statuses={[]} privileges={PRIVILEGE_OPTIONS} showFavorites proposeHref="/inits/propose" emptyKey="inits_explore.empty">` with one `<InitiativeCard>` per item, plus `<InitiativeExploreModal modalId="inits-view-modal">`.
  - **Client data:** the items JSON map is embedded for the modal.
  - **Client script:** `initCardGallery({ galleryId: "inits-gallery", pageSize: 20, idAttr: "initId", services: { toggleFavorite: setInitiativeFavorite, vote, tally } })`, then `loadClientTranslations()` and `installGlobalToast()`.
- [X] T046 [P] [US3] Add the `inits_explore.*` keys to `ui/src/i18n/en.json` and `es.json`: title, subtitle, empty, related_count, discuss.

**Checkpoint**: All three P1 stories work. Browsing plus proposing is a shippable increment.

---

## Phase 6: User Story 4 — See what is waiting on me, split between assets and initiatives (Priority: P2)

**Goal**: The bell has Assets and Initiatives tabs. The Initiatives tab lists only pending DIAGNOSIS, MODIFICATION, ACCEPTANCE and REJECTION items owed by the user, one per initiative, with no dismiss control (FR-025 – FR-031).

**Independent Test**: After a proposal naming `santiago.marin`, he sees the diagnosis request under Initiatives within 60 s, and the Assets tab is unchanged (quickstart Scenario 3).

### Tests for User Story 4

- [X] T047 [P] [US4] Extend `api/tests/test_inits_requests.py`.
  - **Threads:** the newest row wins per `(init, type)`.
  - **Derivation:** SELF when a PENDING notification-type thread is owed; OTHER when nothing is owed and the status is ACTIVATED or FEEDBACK; HANDLED otherwise. Owed is evaluated before status: an ACCEPTED initiative with an unacknowledged ACCEPTANCE is still PENDING/SELF.
  - **Rows:** one row per initiative across roles.
  - **Ignored rows:** KICKOFF, DELIVERY, ARCHIVING, VOTE, COMMENT, QUESTION and ANSWER never create or close a thread.
  - **Feed:** only SELF rows, newest first; `limit` caps `items` but not `total`; one user's feed is isolated from another's.
  - **Acknowledge:** ACCEPTANCE/REJECTION → a new HANDLED row, and the item leaves the feed; idempotent on an already-handled thread; 400 for DIAGNOSIS/MODIFICATION; 404 for a foreign or missing row.
  - **Pagination:** the `state` filter and `skip` / `limit` on `/requests`.

### Implementation for User Story 4

- [X] T048 [US4] Create `api/app/inits/internal/requests_service.py`, ported from `api/app/lib/internal/actions_service.py` (`_latest_threads`, `_participations`, `list_participations`, `list_notifications`, `acknowledge_notification`, `_insert_status`).
  - **Constants:** `NOTIFICATION_TYPES`, `PARTICIPATION_TYPES`, `ACKNOWLEDGEABLE_TYPES`, `IN_MOTION_STATUSES` (data-model.md); `AWAITED_SELF` / `OTHER`; exception `NotificationNotAcknowledgeable(ValueError)`.
  - **Mapping:** `asset` → `init`, and `Action` → `Collaboration`.
  - **Roles:** PROPOSER from ACTIVATION, REVIEWER from DIAGNOSIS.
  - **Queries:** one batched initiatives query; the derivation order is kept verbatim.
- [X] T049 [US4] In `api/app/inits/routes/collaborations.py`, add the following routes (`current_active_user` only, scoped to `current.id`), declared before `/{collab_id}`:
  - `GET /requests?state=PENDING&skip=0&limit=50` (`limit` 1–200) → `List[InitiativeRequest]`;
  - `GET /notifications?limit=5` (1–50) → `InitNotificationFeed`;
  - `POST /notifications/{collab_id}/acknowledge` → `Collaboration`. It uses an `_own_notification` helper that returns 404 unless the row is the caller's and of a notification type; `NotificationNotAcknowledgeable` → 400, `IntegrityError` → 409.
- [X] T050 [P] [US4] Add to `ui/src/lib/collaborations.ts`: `getInitiativeRequests(state)`, `getInitiativeNotifications(limit=5)`, and `acknowledgeCollaboration(id)`.
- [X] T051 [US4] Extend `ui/src/lib/notificationsStore.ts`.
  - **State:** add `initFeed: InitNotificationFeed`, `initPending: InitiativeRequest[]` and `initHandled: InitiativeRequest[]`.
  - **Refresh:** `refresh()` fetches the three asset lists and the three initiative lists with `Promise.allSettled`. Each list keeps its last value when its own request fails; a failure must never blank the other domain.
  - **Unchanged:** the subscribe / start / stop API, `CHANGED_EVENT`, polling, visibility and bfcache handling.
- [X] T052 [US4] Split `ui/src/components/svelte/NotificationBell.svelte` into two tabs.
  - **Tabs:** Assets (`inits_notifications.tab_assets`) and Initiatives (`inits_notifications.tab_initiatives`), each with a count pill.
  - **Badge:** the dot shows when `feed.total + initFeed.total > 0`.
  - **Opening:** the bell opens on the first tab with items, Assets on a tie.
  - **Assets tab:** the existing markup, routing and footer, unchanged.
  - **Initiatives tab:**
    - Items show `init_name` and `inits_notifications.type.<TYPE> · formatRelative`, with `MAX_SHOWN = 5` and an "and N more" line.
    - Routing: DIAGNOSIS → `/inits/diagnose?collab={id}`, MODIFICATION → `/inits/modify?collab={id}`, ACCEPTANCE/REJECTION → `/inits/show-collab?collab={id}`.
    - The empty state (`inits_notifications.empty`) has a link, and the footer link goes to `/inits/my_initiative_requests`.
  - **No dismiss control** in either tab.
- [X] T053 [P] [US4] Add the `inits_notifications.*` keys to `ui/src/i18n/en.json` and `es.json`: tab_assets, tab_initiatives, empty, see_all, and `type.DIAGNOSIS` ("Diagnosis requested"), `type.MODIFICATION` ("Changes requested"), `type.ACCEPTANCE` ("Initiative accepted"), `type.REJECTION` ("Initiative rejected").

**Checkpoint**: Reviewers learn about assignments. Clicking routes to pages built in US6–US8; until those land, the routes 404.

---

## Phase 7: User Story 5 — Keep a durable record of my initiative requests (Priority: P2)

**Goal**: My Initiative Requests sits under My Asset Requests, with Pending and Handled views, one row per initiative, and whose turn it is (FR-032 – FR-037).

**Independent Test**: As the proposer of a pending proposal, the page shows it once under Pending, marked "Someone else · Waiting for diagnosis" (quickstart Scenario 3, step 1).

**Depends on**: US4 (T048–T051: service, routes, store).

- [X] T054 [US5] Create `ui/src/components/svelte/MyInitiativeRequests.svelte`, a structural twin of `ui/src/components/svelte/MyAssetRequests.svelte`.
  - **Data:** it subscribes to `notificationsStore` (`initPending` / `initHandled`).
  - **Tabs:** Pending and Handled with counts.
  - **Columns:**
    - Initiative;
    - Request: the pending type label, else `proposed_by_me` / `diagnosed_by_me` from `roles`;
    - Status: the list label;
    - Waiting on (Pending only): SELF shows an amber "You" pill; OTHER shows a gray "Someone else" pill plus the stage: ACTIVATED → `stage.diagnosis`, FEEDBACK → `stage.modification`;
    - Updated (relative);
    - Action.
  - **Action column:**
    - SELF + ACCEPTANCE/REJECTION: "Got it", which calls `acknowledgeCollaboration`, then `notifyChanged()`.
    - SELF + DIAGNOSIS/MODIFICATION: "Open", using the bell's routing.
    - OTHER: no button.
  - Empty states per tab.
- [X] T055 [US5] Create `ui/src/pages/inits/my_initiative_requests.astro` (BaseLayout, Breadcrumb, subtitle `my_initiative_requests.subtitle`, a `#my-initiative-requests-root` div mounted with `mount(MyInitiativeRequests, { target })`), mirroring `ui/src/pages/lib/my_asset_requests.astro`.
- [X] T056 [US5] In `ui/src/components/core/header/Header.astro`, add `{ label: "account_menu.my_initiative_requests", href: "/inits/my_initiative_requests" }` to `workItems` directly after the My Asset Requests item, with no `profiles` list (research R14). Also add the matching entry to the `ICONS` map in `ui/src/components/core/header/AccountMenu.astro`, reusing an existing icon style.
- [X] T057 [P] [US5] Add i18n keys to `ui/src/i18n/en.json` and `es.json`: `account_menu.my_initiative_requests` ("My Initiative Requests" / "Mis Solicitudes de Iniciativas"), and `my_initiative_requests.*` (title, subtitle, tab_pending, tab_handled, col_initiative, col_request, col_status, col_waiting, col_updated, col_action, you, someone_else, stage.diagnosis, stage.modification, proposed_by_me, diagnosed_by_me, got_it, open, empty_pending, empty_handled).

**Checkpoint**: The bell and requests page agree and refresh live; the bell is a strict subset.

---

## Phase 8: User Story 6 — Diagnose a proposed initiative (Priority: P2)

**Goal**: The reviewer scores each criterion and accepts, rejects or requests changes, in one transaction that notifies the proposer (FR-040 – FR-044).

**Independent Test**: As the reviewer, open the bell item, request changes with feedback, and verify: status FEEDBACK, DIAGNOSIS/HANDLED, and MODIFICATION/PENDING for the proposer carrying the feedback (quickstart Scenario 4, steps 1–2).

### Tests for User Story 6

- [X] T058 [P] [US6] Create `api/tests/test_inits_diagnosis.py`.
  - **Decisions (parametrized):** accept → ACCEPTED + ACCEPTANCE/PENDING; reject → REJECTED + REJECTION/PENDING; changes → FEEDBACK + MODIFICATION/PENDING.
  - **Each decision:** writes `reviewer_score` per criterion; leaves `rationale` untouched; `score` = Σ reviewer scores; inserts DIAGNOSIS/HANDLED; puts the proposer row's `content` = feedback; the proposer is the author of the earliest ACTIVATION.
  - **Guard order:**
    1. unknown decision → 400;
    2. missing or inactive initiative → 400;
    3. ineligible caller → 403;
    4. no PENDING DIAGNOSIS for the caller → 403;
    5. status ≠ ACTIVATED → 409 (a double submit returns 409);
    6. incomplete or out-of-scale answers → 400; missing feedback for reject or changes → 400.
  - **No partial writes** on any error.
  - **Viewing records nothing:** there is no GET side effect.

### Implementation for User Story 6

- [X] T059 [US6] Create `api/app/inits/internal/diagnosis_service.py`.
  - **Declarations:** `DiagnosisForbidden`, `DiagnosisConflict`, and `DECISIONS = {"accept": ("ACCEPTED","ACCEPTANCE"), "reject": ("REJECTED","REJECTION"), "changes": ("FEEDBACK","MODIFICATION")}`.
  - **Function:** `diagnose_initiative(session, reviewer, init_id, data: InitiativeDiagnoseRequest) -> Initiative`.
  - **Guards,** in the T058 order, reusing `app.internal.reviewers.is_eligible` and T008 `validate_reviewer_answers`.
  - **Transaction:**
    1. upsert `Diagnostic.reviewer_score` (create the row with `creator_score` NULL-safe only if missing; it should exist from propose);
    2. set `initiative.score` = the sum over active criteria and `initiative.status` = the new status;
    3. insert DIAGNOSIS/HANDLED for the reviewer;
    4. insert `<type>`/PENDING for the proposer with `content = feedback.strip() or None`;
    5. commit.
- [X] T060 [US6] In `api/app/inits/routes/initiatives.py`, add `POST /api/initiatives/{init_id}/diagnose` → `Initiative`. It is `current_active_user` only (the service enforces the rest) and maps `DiagnosisForbidden` → 403, `DiagnosisConflict` → 409, `ValueError` → 400 and `IntegrityError` → 409.
- [X] T061 [P] [US6] Add `diagnoseInitiative(id, payload)` → `POST /api/initiatives/{id}/diagnose` to `ui/src/lib/initiatives.ts`.
- [X] T062 [US6] Create `ui/src/components/svelte/InitiativeDiagnose.svelte`.
  - **Load:** reads `?collab=` and calls `getCollaboration(id)`. It shows `inits_diagnose.not_found` if missing or not `type === "DIAGNOSIS"`, and `inits_diagnose.blocked` if not PENDING or `initiative.status !== "ACTIVATED"`, with a link to `/inits/my_initiative_requests` in both cases.
  - **Content:** the initiative's core fields read-only (list labels), related assets via `getInitiativeAssets(init)`, `DiagnosisTable` mode `review` from `getInitiativeDiagnostics(init, lang)`, and a feedback textarea.
  - **Buttons:** Accept (emerald), Request changes (amber), Reject (red) and Back (`history.back`).
  - **Validation:** feedback is required for reject and changes, and `DiagnosisTable.validate()` must return empty.
  - **On success:** `notifyChanged()`, then `/inits/my_initiative_requests`.
  - Opening the page makes no write call.
- [X] T063 [US6] Create `ui/src/pages/inits/diagnose.astro` (BaseLayout, Breadcrumb "My Initiative Requests › Diagnose Initiative", mounting `InitiativeDiagnose`), mirroring `ui/src/pages/lib/review.astro`.
- [X] T064 [P] [US6] Add the `inits_diagnose.*` keys to `ui/src/i18n/en.json` and `es.json`: title, feedback, feedback_required, accept, changes, reject, blocked, not_found.

**Checkpoint**: Proposals can be accepted, rejected or sent back.

---

## Phase 9: User Story 7 — Modify and resubmit after a change request (Priority: P2)

**Goal**: The proposer edits core fields and their answers and resubmits to the same reviewer (FR-045 – FR-048).

**Independent Test**: As the proposer of a FEEDBACK initiative, edit and resubmit. The result is ACTIVATED, MODIFICATION/HANDLED, and a new DIAGNOSIS/PENDING for the same reviewer (quickstart Scenario 4, step 3).

### Tests for User Story 7

- [X] T065 [P] [US7] Create `api/tests/test_inits_modify.py`:
  - sent core fields are applied, and unsent ones are untouched;
  - `creator_score` and `rationale` are upserted;
  - `reviewer_score` is preserved;
  - MODIFICATION/HANDLED is inserted, the status becomes ACTIVATED, and DIAGNOSIS/PENDING goes to the reviewer of the newest DIAGNOSIS row;
  - 403 without a PENDING MODIFICATION, or when the caller is not the proposer; 409 when the status ≠ FEEDBACK; 400 for invalid values or incomplete answers when sent;
  - `reviewer_id`, `assets` and `status` in the body are ignored or rejected by the schema;
  - a two-round loop (changes → resubmit → changes → resubmit → accept) works.

### Implementation for User Story 7

- [X] T066 [US7] Create `api/app/inits/internal/modify_service.py`.
  - **Declarations:** `ModifyForbidden`, `ModifyConflict`, and `resubmit_initiative(session, proposer, init_id, data: InitiativeResubmitRequest) -> Initiative`.
  - **Guards** per research R9.
  - **Validation:** core fields via T009; answers via T008 when sent.
  - **Transaction:**
    1. apply the fields (`exclude_unset`) and upsert creator answers;
    2. insert MODIFICATION/HANDLED;
    3. set the status to ACTIVATED;
    4. insert DIAGNOSIS/PENDING for the newest DIAGNOSIS row's user (`ValueError` when there is none);
    5. commit.
- [X] T067 [US7] In `api/app/inits/routes/initiatives.py`, add `POST /api/initiatives/{init_id}/resubmit` → `Initiative` (`current_active_user`; `ModifyForbidden` → 403, `ModifyConflict` → 409, `ValueError` → 400, `IntegrityError` → 409).
- [X] T068 [P] [US7] Add `resubmitInitiative(id, payload)` → `POST /api/initiatives/{id}/resubmit` to `ui/src/lib/initiatives.ts`.
- [X] T069 [US7] Create `ui/src/components/svelte/InitiativeModify.svelte`.
  - **Load:** reads `?collab=` and calls `getCollaboration`. It shows not-found and blocked states like T062 (`type === "MODIFICATION"`, PENDING, status FEEDBACK).
  - **Content:** the reviewer feedback (read-only panel from `collab.content`), the editable core fields prefilled from `collab.initiative` (same controls and lists as the propose Core panel), and `DiagnosisTable` mode `modify`.
  - **Resubmit:** validates the fields and answers, sends only the changed core fields plus the full answers, then `notifyChanged()` and `/inits/my_initiative_requests`.
- [X] T070 [US7] Create `ui/src/pages/inits/modify.astro` (BaseLayout, Breadcrumb, mounting `InitiativeModify`), mirroring `ui/src/pages/lib/modify.astro`.
- [X] T071 [P] [US7] Add the `inits_modify.*` keys to `ui/src/i18n/en.json` and `es.json`: title, reviewer_feedback, resubmit, blocked, not_found.

**Checkpoint**: The change-request loop is complete and unlimited.

---

## Phase 10: User Story 8 — Acknowledge the outcome of my initiative (Priority: P3)

**Goal**: The proposer reads the accepted or rejected outcome with the reviewer's message and explicitly acknowledges it (FR-049 – FR-051).

**Independent Test**: Open the ACCEPTANCE notice. Leaving without acknowledging keeps it pending; pressing Acknowledge removes it from the bell and moves it to Handled (quickstart Scenario 4, step 5).

**Depends on**: US4 (T049 acknowledge endpoint, T050 service).

- [X] T072 [US8] Create `ui/src/components/svelte/InitiativeOutcome.svelte`, mirroring `ui/src/components/svelte/ShowAction.svelte`.
  - **Load:** reads `?collab=` and calls `getCollaboration`. It shows not-found unless the type is ACCEPTANCE or REJECTION.
  - **Theme:** ACCEPTANCE is emerald with a check; REJECTION is red with an ×.
  - **Content:** the initiative name, `inits_show_collab.title_accepted|title_rejected`, the reviewer message (`collab.content`) and the relative time.
  - **Buttons:** Acknowledge (shown only while PENDING) calls `acknowledgeCollaboration(id)`, then `notifyChanged()`, then `/inits/my_initiative_requests`. Back only navigates.
  - Opening the page makes no write call.
- [X] T073 [US8] Create `ui/src/pages/inits/show-collab.astro` (BaseLayout, Breadcrumb, mounting `InitiativeOutcome`), mirroring `ui/src/pages/lib/show-action.astro`.
- [X] T074 [P] [US8] Add the `inits_show_collab.*` keys to `ui/src/i18n/en.json` and `es.json`: title_accepted, title_rejected, acknowledge, message, handled.

**Checkpoint**: The full propose → diagnose → modify → accept → acknowledge loop runs from the bell and requests page alone (SC-008).

---

## Phase 11: Polish & Cross-Cutting Concerns

- [X] T075 Run the full backend suite with `docker compose exec -T api uv run pytest -q`. Expect only the 8 pre-existing failures, with every lib workflow suite (`test_lib_propose`, `test_lib_review`, `test_lib_modify`, `test_lib_notifications`, `test_lib_asset_requests`, `test_lib_votes`) passing unchanged.
- [X] T076 Run `cd ui && bun run build && bunx astro check`. The build must be clean and the `astro check` error count must not exceed the recorded baseline (138).
- [X] T077 Run `make test` (health checks) and confirm `make up` still boots all services.
- [X] T078 Walk through quickstart.md Scenarios 1–5 as `adriana.velez` (COLLABORATOR) and `santiago.marin` (REVIEWER), never as the superuser. Include the negative API checks and the ~390 px layout check. Clean up the test initiatives afterwards (`is_active = FALSE`).
- [X] T079 [P] Security review of the new routes against contract #1–#13:
  - no route accepts a `user_id`;
  - every write is behind the `INITS` edit privilege or a workflow assignment;
  - `/linkable-assets` and propose never expose or link invisible assets;
  - `GET /api/collaborations/{id}` returns 404 for foreign rows;
  - the existing `GET /api/initiatives/{id}` is unchanged (Known blocker P2 stays as-is).
- [X] T080 [P] Update `docs/user-stories/05-inits.md`: HU-IN05 gets the Related Assets step and "Request diagnosis" on steps 2–3; HU-IN13 drops DELIVERY; HU-IN04/05/06/13–17 link to `specs/005-explore-initiatives`.
- [X] T081 [P] Update `docs/user-stories/states-and-types.md`: the tab matrix's Propose Initiative → Related Assets becomes "Add relation (staged)"; remove the "propose / diagnose / modify rows are still seed data only" sentence; note that DELIVERY raises no notice.
- [X] T082 [P] Update `docs/user-stories/inits-status.md`. Replace the stub note: the workflow is implemented. HU-Initiative Notifications drops DELIVERY. HU-Modify re-arms `DIAGNOSIS`, not `REVIEW`, fixing the doc typo.
- [X] T083 Update `memory/MEMORY.md`:
  - **Decisions log:** a new row for the inits workflow on `collaborations`, the reviewer rule moved to `api/app/internal/reviewers.py`, all-or-nothing propose, `INITS/EXPLORE` edit for COLLABORATOR/REVIEWER, and the split bell.
  - **Feature status:** Explore Initiatives, Propose, Diagnose, Modify, Acknowledge, initiative notifications and My Initiative Requests become ✅.
  - **Stubs table:** update the inits row.
  - **Known blockers P2 row:** update it.
  - **Stale claim:** fix the one that says My Asset Requests is gated to certain profiles.
- [X] T084 Add ONE rollup entry at the top of `memory/CHANGELOG.md` (format `## YYYY-MM-DD HH:MM — …`; get the time from `date '+%Y-%m-%d %H:%M'`) covering the whole branch, with 1–3 bullets and a "Files affected" list. On later commits to this branch, update this entry instead of adding another.

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1):** no dependencies.
- **Foundational (Phase 2):** depends on Setup and BLOCKS all stories.
- **US1 (Phase 3):** after Foundational. The MVP core.
- **US2 (Phase 4):** after US1, since it adds the reviewer control to the US1 page. Its backend T028/T029 can start right after Foundational.
- **US3 (Phase 5):** after Foundational; independent of US1/US2 (it reads seeded initiatives).
- **US4 (Phase 6):** after Foundational. Realistic validation needs proposals (US1).
- **US5 (Phase 7):** after US4 (service, routes, store).
- **US6 (Phase 8):** after Foundational (T011, T015). Its end-to-end check needs US1 + US4.
- **US7 (Phase 9):** after US6 (a FEEDBACK state is produced by a diagnosis).
- **US8 (Phase 10):** after US4 (acknowledge endpoint). Its end-to-end check needs US6.
- **Polish (Phase 11):** after every desired story.

### Story graph

```text
Setup → Foundational ─┬─ US1 ── US2
                      ├─ US3
                      ├─ US4 ─┬─ US5
                      │       └─ US8
                      └─ US6 ── US7
```

### Within each story

Tests are written first and must fail. Then: services → routes → UI services → components → page → i18n.

### Shared-file sequencing (not parallel)

- `api/app/inits/routes/initiatives.py`: T020 → T021 → T029 → T037 → T060 → T067
- `api/app/inits/routes/collaborations.py`: T011 → T038 → T049
- `ui/src/lib/initiatives.ts`: T025 → T030 → T039 → T061 → T068
- `ui/src/lib/collaborations.ts`: T014 → T039 → T050
- `api/tests/test_inits_propose.py`: T018 → T022 → T028
- `api/tests/test_inits_requests.py`: T012 → T047
- `ui/src/i18n/{en,es}.json` edits are all additive but touch the same files, so apply them one at a time.

## Parallel Opportunities

- **Phase 1:** T001, T002 and T003 in parallel.
- **Phase 2:** T006, T010, T013, T014 and T017 in parallel once their prerequisites (T004, T008) exist. T015 and T016 are sequential.
- **Phase 5 (US3):**
  - tests T033 ∥ T034;
  - services T035 ∥ T036;
  - UI pieces T042 ∥ T043 ∥ T046 while the backend routes land.
- **Across stories:** after Foundational, US3, US4 and US6 can be worked by different people in parallel. The API-side services of different stories are in separate files.

### Parallel example: User Story 3

```text
Task: "T033 [US3] Create api/tests/test_inits_votes.py"
Task: "T034 [US3] Create api/tests/test_inits_explore.py"
Task: "T035 [US3] Create api/app/inits/internal/votes_service.py"
Task: "T036 [US3] Create api/app/inits/internal/explore_service.py"
Task: "T042 [US3] Create ui/src/components/inits/InitiativeCard.astro"
Task: "T043 [US3] Create ui/src/components/svelte/InitiativeDetailView.svelte"
```

### Parallel example: User Story 6

```text
Task: "T058 [US6] Create api/tests/test_inits_diagnosis.py"
Task: "T061 [US6] Add diagnoseInitiative to ui/src/lib/initiatives.ts"
Task: "T064 [US6] Add inits_diagnose.* i18n keys"
```

## Implementation Strategy

### MVP first (P1: US1 + US2, then US3)

1. Phase 1 Setup, then Phase 2 Foundational (the lib suites must stay green after T005).
2. US1 + US2, then validate quickstart Scenario 2. **Stop and demo:** initiatives can be proposed with a proper reviewer.
3. US3, then validate Scenario 1. **P1 complete:** browse + propose.

### Incremental delivery

4. US4 + US5 → Scenario 3: reviewers are notified, and everyone has a durable record.
5. US6 + US7 → Scenario 4, steps 1–4: the diagnosis loop.
6. US8 → Scenario 4, step 5: outcomes are acknowledged, and the loop is closed (SC-008).
7. Phase 11 Polish, docs, MEMORY and CHANGELOG.

### Notes

- The bell's initiative routes (US4) point at pages delivered in US6–US8. If you ship US4 alone, expect those links to 404 until then.
- There is no DDL. The seed edits need `make rebuild`, or the one-off SQL in quickstart § Provisioned databases.
- Commit after each task or logical group. Keep the single CHANGELOG rollup entry updated.
