# Research: Explore Initiatives, Propose Initiative & Initiative Notifications

**Branch**: `005-explore-initiatives` | **Phase**: 0 | **Date**: 2026-09-24

The spec left no `[NEEDS CLARIFICATION]` markers after the 2026-09-24 session. Each decision below resolves a design unknown found while mapping the existing code. Every decision mirrors the shipped asset implementation (`lib`) unless a reason is given.

---

## R1 — Workflow substrate: `collaborations`, one service module per transition

- **Decision.** All initiative workflow rows go to `collaborations` (`type` + `workflow_status`), following the asset rules exactly:
  - every transition inserts a new row and never updates one;
  - the newest row of a `(init, type)` thread is its current state;
  - one service function owns each transition, inside one transaction.
- **Services.** They live in `api/app/inits/internal/`:
  - `propose_service.py` (activation)
  - `diagnosis_service.py` (reviewer decision)
  - `modify_service.py` (resubmit)
  - `requests_service.py` (notifications, requests and acknowledgment)
- **Rationale.** This is the same justified deviation spec 004 already recorded: `actions.asset` is a NOT NULL FK to `assets`, and the user named `collaborations` explicitly. The `COLLAB_TYPE` list already holds every type needed (ACTIVATION, DIAGNOSIS, MODIFICATION, ACCEPTANCE, REJECTION, VOTE), so no enum extension is required.
- **Alternatives.** A generic cross-domain workflow engine parameterised by model was rejected for now. The lib services are small, and their guards are domain-specific (characterizations vs diagnostics). Extracting an engine for two consumers would rewrite shipped, tested lib code for little gain. See Complexity Tracking in plan.md.

## R2 — Reviewer eligibility is shared, not copied

- **Decision.** Move `REVIEWER_PROFILES`, `ADMIN_PROFILES`, `_is_eligible`, `is_admin`, `list_reviewers` and `resolve_reviewer` from `lib/internal/propose_service.py` into a new `api/app/internal/reviewers.py`. `lib/internal/propose_service.py` keeps thin re-exports, so its public names and behaviour are unchanged, and the lib test suites are the acceptance test.
- **What the rule is.** An eligible reviewer has an Administrator, Administrative or Reviewer profile, or is a superuser. A non-admin proposer is excluded from their own list. When no reviewer is chosen, the eligible user with the lowest id is picked, minus the excluded proposer.
- **Rationale.** FR-018 – FR-020 require "the same rule as Propose an asset". Constitution I forbids duplicating workflow plumbing per module, and spec 004 set the precedent with `resource_permissions.py`.
- **Alternatives.** Importing `lib.internal.propose_service` from `inits` was rejected: it couples the inits workflow to an asset service module.

## R3 — Propose writes everything in ONE transaction, including links and answers

- **Decision.** `POST /api/initiatives/propose` receives the core fields, `reviewer_id`, `answers` and `assets`. It writes all of the following in one commit:
  - the initiative (ACTIVATED);
  - the diagnostics rows (`creator_score`, `rationale`);
  - the `asset_inits` rows;
  - ACTIVATION/HANDLED for the proposer;
  - DIAGNOSIS/PENDING for the reviewer;
  - two USER/MANAGE `init_permissions` (deduplicated when proposer == reviewer, for admins).
- **Rationale.** FR-021 and SC-002 require all-or-nothing. The asset wizard saves related rows with separate calls after propose returns, so a partial failure leaves a proposal without its links. That is acceptable for optional asset links, but it would break the spec's guarantee here.
- **Alternatives.** Mirroring the asset flush-after pattern was rejected because it violates FR-021.

## R4 — RBAC for collaborators: flip `INITS/EXPLORE` to `can_edit = TRUE` in the seed

- **Finding.** COLLABORATOR and REVIEWER hold `INITS/EXPLORE` with `can_edit = FALSE`. Every inits write guard checks `can_edit=True`, so today those profiles cannot post in the discussion. They could not propose or vote either.
- **Decision.** In `db/sql/12-admin-insert.sql`, set `can_edit = TRUE` on `INITS/EXPLORE` for COLLABORATOR and REVIEWER. The write guards for propose, vote and discussion then use `check_any_privilege(session, user, "INITS", ["EXPLORE","INITIATIVES"], can_edit=True)`. Provisioned DBs get a one-off `UPDATE privileges …` (quickstart § Provisioned DBs).
- **Rationale.** This matches the asset side, where those profiles hold `LIB.<category>` with `can_edit = TRUE`, which is exactly what lets them propose, vote and comment. Explore is by definition the participation surface.
- **Alternatives.** Relaxing the write guards to read-level was rejected. It would make `can_edit` meaningless for the whole INITS module.

## R5 — A dedicated Explore list endpoint with batched counts

- **Decision.** Add `GET /api/initiatives/explore?skip&limit`, gated on read access to `INITS` with any of `EXPLORE` or `INITIATIVES`.
  - **Filtering.** It returns active initiatives the caller can access (superuser: all) whose status is in `EXPLORE_STATUSES = (ACCEPTED, IN_PROGRESS, DELIVERED)`, filtered before `skip`/`limit`, ordered by `created_at` desc.
  - **Fields.** Each item carries `permission_scopes`, `is_favorite`, `my_access`, `votes {positive, negative, my_vote}`, `discussion_count` and `related_assets_count`.
  - **Queries.** The counts come from three `GROUP BY init` queries restricted to the page's ids: votes, discussion and links. That is a constant query count with no N+1, and the queries are portable to SQLite.
- **Rationale.** `/with-access` requires `INITS/INITIATIVES`, which EXPLORE-only users lack, and it has no counts. The asset gallery computes counts client-side from `getActions(0,1000)`. That is unbounded-ish and a known P1 truncation risk, so it is not copied.
- **Alternatives.** Widening `/with-access` was rejected: it changes a shipped contract's gating and semantics (Principle II).

## R6 — Initiative votes on `collaborations` `type = VOTE`, actor from the session

- **Decision.** Mirror the asset `set_vote` semantics:
  - `content` is POSITIVE or NEGATIVE;
  - at most one active VOTE row per `(user, init)`;
  - the same value toggles the vote off, the other value switches it, and clearing deactivates it;
  - `workflow_status` stays NULL, so votes never enter the notification threads.
- **Endpoints.**
  - `GET /api/collaborations/votes/init/{id}` returns the tally.
  - `PUT /api/collaborations/votes/init/{id}` with `{content}` sets or toggles the vote.
  - `DELETE /api/collaborations/votes/init/{id}` clears it.
  - All require view access to the initiative. The writes also need `can_edit`.
- **Rationale.** FR-008 and FR-053. The asset vote API takes `user_id` in the body; the initiative API deliberately does not.
- **Alternatives.** A new `init_votes` table was rejected: the substrate already models votes.

## R7 — Notifications and requests: port `_participations` over `collaborations`

- **Decision.** `requests_service.py` ports `actions_service._latest_threads` / `_participations` / `list_participations` / `list_notifications` / `acknowledge_notification` with these equivalences:

  | asset constant | initiative constant |
  |---|---|
  | `NOTIFICATION_TYPES` REVIEW, MODIFICATION, PUBLICATION, REJECTION | DIAGNOSIS, MODIFICATION, ACCEPTANCE, REJECTION |
  | `PARTICIPATION_TYPES` + PROPOSAL | + ACTIVATION |
  | `IN_MOTION_ASSET_STATUSES` PROPOSED, FEEDBACK | ACTIVATED, FEEDBACK |
  | `ACKNOWLEDGEABLE_TYPES` PUBLICATION, REJECTION | ACCEPTANCE, REJECTION |
  | roles PROPOSER / REVIEWER | PROPOSER (ACTIVATION) / REVIEWER (DIAGNOSIS) |

- **Derivation order.** The asset derivation order is kept verbatim: "owed by me" is evaluated before the initiative's status (FR-034).
- **Excluded types.** KICKOFF, DELIVERY and ARCHIVING are HANDLED log rows and are not participation types, so they never create or close a thread.
- **Endpoints.**
  - `GET /api/collaborations/requests?state&skip&limit`
  - `GET /api/collaborations/notifications?limit`
  - `POST /api/collaborations/notifications/{id}/acknowledge`
  - `GET /api/collaborations/{id}`: a single row, owner or superuser only, used by the three action pages to resolve `?collab=`.
  - All are `current_active_user`-scoped to the caller, like the asset equivalents (Known blockers row: no never-seeded privilege gates).
- **Seed cleanup.** `52-inits-insert.sql` row 8 (`DELIVERY` / `PENDING`) predates the 004 decision that Delivery raises no notice. It is deleted, as the 2026-09-16 notifications redesign deleted obsolete `NOTIFIED` rows. Ids are not renumbered.
- **Alternatives.** A shared generic "threads" helper parameterised by model and FK was considered. It was deferred for the same reason as R1, and noted as a follow-up.

## R8 — Diagnosis: the reviewer answers per criterion, overall feedback goes on the collaboration

- **Finding.** `diagnostics` has a single `rationale` column. Spec 004 displays it as the proposer's rationale.
- **Decision.**
  - The reviewer submits `answers {criteria: score}` plus `decision` and `feedback`.
  - Scores are written to `reviewer_score`; `rationale` is left untouched.
  - `feedback` goes to the proposer's new collaboration `content`, exactly like asset review feedback.
  - `initiatives.score = Σ reviewer_score` over the active criteria. This is confirmed against the seed: initiative 1 has reviewer scores 3+3+3+2+2+3 = 16 = `score`, and initiative 3 gives 15.
  - `DECISIONS = {accept: (ACCEPTED, ACCEPTANCE), reject: (REJECTED, REJECTION), changes: (FEEDBACK, MODIFICATION)}`.
- **Guards, in the order of `review_service`:**
  1. unknown decision → 400;
  2. initiative missing or inactive → 400;
  3. reviewer not eligible → 403;
  4. no PENDING DIAGNOSIS for the caller → 403;
  5. status ≠ ACTIVATED → 409;
  6. incomplete or out-of-scale answers → 400;
  7. missing feedback for reject or changes → 400.
- **Proposer.** The proposer is the author of the earliest ACTIVATION row.
- **Alternatives.** Adding a `reviewer_rationale` column was rejected: it is DDL for something the spec does not require.

## R9 — Modify: core fields and proposer answers, same reviewer re-armed

- **Decision.** `resubmit_initiative` accepts the editable core fields (name, description, type, expected_impact, priority_level, reference, tags, detail) and `answers {criteria: {score, rationale}}` for the proposer's answers. It re-validates them like propose. Links are not editable here; the spec scopes Modify to Core Fields and Diagnosis Questions.
- **Transition.** FEEDBACK → ACTIVATED. MODIFICATION/HANDLED is written for the proposer, and DIAGNOSIS/PENDING for the reviewer of the newest DIAGNOSIS row.
- **Guards.**
  - initiative missing → 400;
  - no PENDING MODIFICATION for the caller → 403;
  - caller is not the ACTIVATION author → 403;
  - status ≠ FEEDBACK → 409.
- **Reviewer scores are left as they were.** `reviewer_score` from the previous round is kept until the next diagnosis overwrites it, so the reviewer sees their prior scores. The detail views only show reviewer scores as final once the status has left ACTIVATED.

## R10 — Criteria scale validation uses `list_items` values

- **Decision.** An answer is valid when it is the integer value of an `en` `list_items` row whose `list = criterias.list` for that criterion. Every active criterion must be answered, on propose, diagnosis and modify. With zero active criteria, answers may be empty (spec edge case).
- **Rationale.** `diagnostics_service.get_diagnostics` already resolves labels this way. Validating on `en` avoids duplicate checks per language.

## R11 — Explore gallery UI: reuse `CardGallery`, add a list layout, parameterise the controller

- **Decision.**
  - **Layout.** `CardGallery.astro` gains an opt-in `layout?: "grid" | "list"` prop, default `"grid"`, so existing callers are unchanged. `"list"` renders one full-width card per row.
  - **Card.** The new `components/inits/InitiativeCard.astro` has a left status-coloured accent bar and a header row (name, status pill, type / priority / expected-impact chips, relative time). Below it are a two-line description, `#tags`, and a footer with the vote bar, discussion count, related-assets count and favorite star. It collapses to a stacked card below `sm`. It is built on `GalleryCard`'s data attributes (`data-card`, `data-search`, `data-favorite`, `data-permissions`, `data-action=*`) so filtering works unchanged.
  - **Controller.** `initCardGallery` gains an optional `services` object (`toggleFavorite(id,on)`, `vote(id,value)`, `tally(id)`) and an `idAttr`. The defaults are today's asset services and `assetId`, so existing callers are unchanged.
- **Rationale.** FR-006 and FR-007. This follows the 004 approach of parameterising the shared reader instead of forking it, and it keeps the six-option privilege filter and favorites pill identical (FR-003, FR-004).

## R12 — Initiative Detail (card click): a read-only view island, not a mode on the edit island

- **Decision.**
  - New `components/svelte/InitiativeDetailView.svelte`, mounted in `components/inits/InitiativeExploreModal.astro`, with tabs Core Fields, Diagnosis Questions, Related Assets, Discussion and History (FR-010).
  - The header shows the vote bar and favorite, kept in sync with the card.
  - The Diagnosis table is extracted from `InitiativeDetailTabs.svelte` into a shared `components/svelte/DiagnosisTable.svelte` with `mode: "view" | "propose" | "review" | "modify"`. It serves the detail views (view), the Propose wizard (the proposer column is editable), the diagnose page (proposer read-only, reviewer editable) and the modify page (the proposer column is editable).
  - Discussion is `<Foro api={initiativeForoApi} idAttr="initId">`, fully interactive. History is `mountHistory({fetcher: getInitiativeHistory, idAttr: "initId", labelNamespace: "initiative_history.action"})`.
- **Rationale.** The 850-line edit island is shipped and tab-save-coupled. A view mode would thread `readonly` checks through every tab. Extracting the one genuinely shared piece (the diagnosis table) avoids duplicating it three more times.

## R13 — Split bell: one store, two feeds, independent failure

- **Decision.**
  - **Store.** `notificationsStore.ts` state gains `initFeed`, `initPending` and `initHandled`. `refresh()` fetches the six lists in parallel with `Promise.allSettled`, so a failure on one domain keeps the last-known value for that domain only.
  - **Bell.** `NotificationBell.svelte` gets two tabs, Assets and Initiatives, each with its own count. The badge shows `feed.total + initFeed.total`. The bell opens on the first tab with items, Assets on a tie. Initiative items route DIAGNOSIS → `/inits/diagnose?collab=`, MODIFICATION → `/inits/modify?collab=`, ACCEPTANCE/REJECTION → `/inits/show-collab?collab=`. The footer link follows the active tab.
  - **Unchanged.** The asset tab's markup and behaviour stay the same (FR-026, SC-006). The existing `notifications:changed` event, polling and bfcache handling are reused as they are.
- **Rationale.** FR-025 and FR-037. This reuses the store the 2026-09-16 redesign built for exactly this purpose.

## R14 — Account menu entry is not profile-gated

- **Finding.** The spec assumed My Asset Requests is profile-gated. The current `Header.astro` passes it with **no** `profiles` list, on purpose (comment at lines 93–100); the MEMORY.md note is stale.
- **Decision.** Add `{label: "account_menu.my_initiative_requests", href: "/inits/my_initiative_requests"}` right after the asset item, also ungated, plus an `ICONS` entry in `AccountMenu.astro`. This satisfies the spec's intent (every proposer can follow their proposals) with no special case.

## R15 — Propose wizard page: new page on shared primitives, ack dialog extracted

- **Decision.** New `ui/src/pages/inits/propose.astro`, built on `components/ui/{Tabs,FormField,Button}.astro`, `lib/tabs.ts` and `lib/formClasses.ts`.
  - **Step order.** `["core", "diagnosis", "related"]`.
  - **Primary button labels.** `inits_propose.next_diagnosis` ("Diagnosis questions >"), then `inits_propose.next_related` ("Related Assets >"), and finally `inits_propose.submit` ("Request diagnosis").
  - **Direct submit.** `DIRECT_SUBMIT_TABS = ["diagnosis"]` shows the secondary "Request diagnosis". This gives exactly the 2 / 3 / 2 buttons of FR-013, FR-015 and FR-017.
  - **Validation.** Submitting from any step validates Core Fields and all answers, and jumps to the first invalid tab.
  - **Double submission.** An in-flight guard disables both submit buttons, so a double click cannot create two initiatives.
  - **Ack dialog.** The blocking `showAckDialog` is extracted from `pages/lib/propose.astro` into `components/ui/AckDialog.astro` + `lib/ackDialog.ts`, then adopted by both pages. The asset page's behaviour is unchanged.
  - **Pickers.** The reviewer select uses the new `GET /api/initiatives/reviewers`. The asset target picker uses the new `GET /api/initiatives/linkable-assets`, which lists only assets the caller can see. The server re-checks visibility on submit (spec edge case).
- **Rationale.** `pages/lib/propose.astro` is heavily category-bound (themes, characterizations, locked category). Reusing its primitives rather than forking the page keeps both readable. The 004 Related Assets tab reads `getAssetsWithAccess`, which EXPLORE-only users cannot call; hence the new picker endpoint.

## R16 — Testing strategy

- **Backend.** New `api/tests/test_inits_*.py` modules on the existing `inits_helpers.py`, with the lib workflow suites as templates:
  - `test_inits_propose.py`
  - `test_inits_diagnosis.py`
  - `test_inits_modify.py`
  - `test_inits_requests.py` (notifications + requests + acknowledge)
  - `test_inits_votes.py`
  - `test_inits_explore.py`
  - `test_internal_reviewers.py`
- **Regression.** The lib suites (propose, review, modify, notifications, asset_requests) must pass unchanged, which guards R2.
- **UI.** `bun run build`, `astro check` at the unchanged baseline, and a quickstart click-through as non-superuser seeded users.
