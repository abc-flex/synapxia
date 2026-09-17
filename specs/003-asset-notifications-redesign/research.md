# Research: Asset Notification Scheme Redesign

**Branch**: `003-asset-notifications-redesign` | **Phase**: 0 | **Date**: 2026-09-16

All Technical Context unknowns are resolved below. Each entry records the decision, why it
was chosen, and what was rejected.

---

## R1 — Two-state vocabulary and enum values

**Decision**: Collapse `WORKFLOW_STATUS` from `ASSIGNED` / `NOTIFIED` / `FINISHED` to
`PENDING` / `HANDLED`. Labels: EN "Pending" / "Handled", ES "Pendiente" / "Atendido".

**Rationale**: The three-state model conflates *read state* (`NOTIFIED` = the user looked)
with *work state*. That conflation is the direct cause of the `DISMISSIBLE_TYPES` special
case in `actions_service.py`: dismissing writes `FINISHED`, which is also what
`review_service` / `modify_service` write to mean "already decided", so dismissing an
actionable item would silently revoke the assignee's ability to act. Removing the middle
state removes the special case rather than papering over it.

"Atendido" was chosen over "Realizado" / "Completado" because it is the natural antonym of
the already-shipped "Pendiente" (*pendiente de atender → atendido*) and because it does not
presuppose a task was executed — which matters for publication and rejection notices, where
the user only takes note. "Visto" was rejected explicitly: it is the semantics of the
`NOTIFIED` state being removed and would reintroduce the read/work conflation.

**Alternatives considered**: `PENDING`/`DONE` (rejected — "done" carries the same
task-executed presupposition as "realizado"); `PENDING`/`CLOSED` (viable and neutral, but
impersonal — it does not convey that *this user* gave the item course); keeping three states
and only changing the UI (rejected — leaves the `DISMISSIBLE_TYPES` defect in place).

---

## R2 — `WORKFLOW_STATUS` is shared with the `inits` domain

**Decision**: Rename the values for both consumers in the same change.
`db/sql/51-inits-ddl.sql:65` declares `collaborations.workflow_status` against the same
`WORKFLOW_STATUS` list, and `db/sql/52-inits-insert.sql` seeds `ACTIVATION` / `DIAGNOSIS` /
`ACCEPTANCE` / `DELIVERY` rows using all three values.

**Rationale**: Leaving `inits` on the old vocabulary would make the list self-contradictory —
a single `list_items` list cannot hold two vocabularies — and would break the admin Lists
screen, which renders the list generically. `inits` has no application code reading these
values today (it is a stub domain with read-only `initiatives` routes only), so the change is
seed-only on that side and carries no code risk.

**Alternatives considered**: A second list, `ASSET_WORKFLOW_STATUS`, leaving `inits` alone
(rejected — duplicates an enum for no benefit and contradicts Principle I's prohibition on
duplicated plumbing).

---

## R3 — `NOTIFIED` rows are deleted, not converted

**Decision**: In the seeds, delete every `NOTIFIED` row outright rather than rewriting it to
`PENDING`.

**Rationale**: A `NOTIFIED` row is always *additional* to a surviving `ASSIGNED` row.
`mark_notified()` returns early unless the thread is `ASSIGNED`, and `_insert_status()`
inserts a new row without touching the previous one — confirmed in the seed itself, where
rows 2/3/4 are `REVIEW` `ASSIGNED`/`NOTIFIED`/`FINISHED` coexisting on the same thread.
Under two states the row therefore carries zero information: converting it would produce two
identical `PENDING` rows per thread, which pollutes the activity timeline with a "was
notified to review the asset" entry that FR-002 forbids.

**Safety check performed**: no `NOTIFIED` row is referenced as a `parent` by any other row
(parents in the seed are `QUESTION` ids 8, 56, 77, 89), and both seed files end with
`setval(pg_get_serial_sequence(...), MAX(id))`, so leaving id gaps is harmless. Ids are
**not** renumbered — renumbering would require rewriting the `parent` references for no gain
and would make the diff unreviewable.

---

## R4 — No migration; seeds are edited in place

**Decision**: Edit `db/sql/41-lib-ddl.sql`, `db/sql/42-lib-insert.sql` and
`db/sql/52-inits-insert.sql` directly. No file is added under `db/sql/manual/`. Applying the
change locally is `make rebuild`.

**Rationale**: The product is unreleased (user's explicit instruction). Seeds only execute on
a fresh volume, so an in-place edit is the repo's own convention for pre-release schema
evolution, and `make rebuild` is itself the rollback. Writing a migration would create a
script that is never run against any real database.

**Constitution deviation**: this departs from "Database evolution MUST be additive and
migration-driven … destructive changes require explicit rollback instructions". Tracked and
justified in `plan.md` § Complexity Tracking.

**Alternatives considered**: keeping the DB values unchanged and mapping them in code
(rejected by the user — they asked for the values themselves to change); an additive
migration file (rejected — no database exists that would need it).

---

## R5 — Log-only action types keep the `HANDLED` state

**Decision**: `PROPOSAL`, `VERSIONING`, `DEPRECATION` (and `inits`' `ACTIVATION`) are written
directly as `HANDLED`, as they are today written directly as `FINISHED`.

**Rationale**: These types never have a pending phase — `propose_service` and
`version_service` insert them already terminal. `HANDLED` on them reads as "not pending",
which is accurate if slightly flat. The value is never surfaced raw to users on these types:
the activity timeline renders type-specific phrases from `_WORKFLOW_SUMMARIES`
(`("PROPOSAL","FINISHED")` → "proposed the asset"), and only the workflow-stage badge shows
the state directly.

**Alternatives considered**: `workflow_status = NULL` for these types, matching
`VOTE`/`COMMENT` (more honest, and tempting now that there is freedom to change anything —
but it forces changes to `get_workflow_stage` and every `_WORKFLOW_SUMMARIES` key, widening
the blast radius for a cosmetic gain). Recorded in the spec's Assumptions as a deliberate
non-goal.

---

## R6 — Deriving a participation row (resolves FR-006, FR-006a, FR-006b)

**Decision**: The page lists one row per `(user, asset)`, derived from the user's own
`actions` rows of types `PROPOSAL`, `REVIEW`, `MODIFICATION`, `PUBLICATION`, `REJECTION`,
joined to the asset for its `status`.

Derivation rules:

| Condition | View | Awaited party |
|-----------|------|---------------|
| Any thread `(asset, type∈{REVIEW,MODIFICATION,PUBLICATION,REJECTION})` for this user whose latest row is `PENDING` | In motion | `SELF` |
| Otherwise, asset `status ∈ {PROPOSED, FEEDBACK}` | In motion | `OTHER` |
| Otherwise (`status ∈ {PUBLISHED, REJECTED, DEPRECATED}`) | Closed | — |

**Rationale**: Grouping by asset rather than by `(asset, type)` is what satisfies FR-006b — it
is the mechanism that stops a proposed-then-published asset appearing twice, once as the
proposal and once as the outcome notice. The `SELF`/`OTHER` split (FR-006a) falls out of the
same pass at no extra query cost, and it is what keeps the notification indicator a strict
subset of the page (FR-013): the indicator is exactly the `SELF` rows.

`{PROPOSED, FEEDBACK}` are the non-terminal asset statuses per the `ASSET_STATUS` list in
`db/sql/41-lib-ddl.sql:166-170`. Note the rules compose correctly for the awkward case: an
asset that is `PUBLISHED` but whose publication notice this user has not yet acknowledged
still evaluates to `SELF`/in-motion via the first rule, and drops to closed only on
acknowledgement — which is exactly what FR-010a requires.

**Alternatives considered**: keying the view off the asset status alone (rejected — an
unacknowledged notice on a published asset would wrongly read as closed); keeping one row per
`(asset, type)` as today and de-duplicating in the UI (rejected — pushes a correctness
concern into presentation, and the indicator count would still double-count).

---

## R7 — Assets created directly are out of scope

**Decision**: Only assets with a `PROPOSAL` action by the user appear as "assets I proposed".
An asset created through the plain `/lib/assets` create form has no `PROPOSAL` row and does
not appear.

**Rationale**: The spec scopes the page to the workflow ("what I asked for and what was asked
of me"). A directly-created asset never entered the review workflow, has no counterparty and
no pending state — it belongs on the asset management screen, which already lists it. This is
the reading of FR-006 that keeps the page a workflow view rather than a second asset list.

---

## R8 — Query shape (avoids N+1, satisfies Principle V)

**Decision**: Three statements per request, regardless of row count: (1) select the user's
workflow `actions` ordered ascending, collapsed per `(asset, type)` in Python to find each
thread's latest row — the pattern `_list_open_actions` already uses; (2) one batched
`Asset.id IN (...)` fetch for name, status and category; (3) one batched `User` fetch only
where an actor name is displayed.

**Rationale**: Reuses the existing, reviewed batching approach rather than inventing a new
one. Grouping in Python is acceptable at this data scale (an internal tool; `actions` rows
per user are in the tens) and keeps the query portable to SQLite, which the test suite uses —
`/api/assets/with-access` is the cautionary precedent in this repo, where a Postgres-only
`array_agg`/`bool_or` aggregate had to be rewritten as a Python reduction to be testable.

**Pagination**: `skip`/`limit` are applied after grouping, per Principle II's bounded-list
requirement. Because grouping precedes pagination, the endpoint reads the user's own workflow
rows in full — bounded in practice by how many assets one person participates in, and
revisited only if that assumption breaks.

---

## R9 — API surface changes

**Decision**:

| Endpoint | Change |
|----------|--------|
| `GET /api/actions/requests` | **New.** The page's data source. `state=pending\|handled`, `skip`, `limit`. |
| `GET /api/actions/notifications` | **Narrowed.** Only `PENDING` threads awaiting the caller. Drops the `unread` response key. |
| `POST /api/actions/notifications/{id}/notified` | **Removed.** FR-002/FR-003 — viewing is no longer recorded. |
| `POST /api/actions/notifications/{id}/dismiss` | **Renamed** to `POST /api/actions/notifications/{id}/acknowledge`. Same guard (informational types only), same effect (write the terminal state). |
| `GET /api/actions/reviews`, `GET /api/actions/modifications` | **Removed.** Both are strict subsets of `participations`; keeping them is the duplication FR-027 requires retiring. |

**Rationale for renaming rather than keeping `dismiss`**: under the new model "dismiss" means
exactly what FR-017 forbids — removing an item from view without resolving it. Acknowledging
*is* resolving for informational types. Keeping the old verb would leave the endpoint named
after the behaviour the feature exists to eliminate. Since the contract is being broken in
this change anyway and the product is unreleased, clarity was preferred over minimising the
diff.

**Constitution deviation**: removing endpoints and a response key departs from Principle II.
Tracked and justified in `plan.md` § Complexity Tracking.

---

## R10 — Staying current: polling with visibility gating

**Decision**: A shared client store owns the list and refreshes it on four triggers —
initial mount, `visibilitychange` → visible, `pageshow` (including `event.persisted`), and a
timer of **60 s** that runs only while the document is visible. Mutations in the same tab
dispatch a `notifications:changed` event for an immediate refresh.

**Rationale**: The staleness has three distinct causes, and only a layered answer covers all
three:

1. **`history.back()` + bfcache.** `ReviewAction.svelte:91` calls `goHome()`, which is
   `window.history.back()`. A back navigation is served from the back/forward cache without
   re-executing the page, so `onMount` never fires again and the bell keeps the list it
   loaded before the decision. `ModifyAction.svelte` has the same `goHome()`. The `pageshow`
   trigger is the standard remedy; the navigation change in R11 avoids the path entirely.
2. **Load-once.** `NotificationBell.svelte:132` calls `load()` in `onMount` and never again —
   verified that `ui/src` contains no `setInterval`, `visibilitychange`, `focus` listener,
   `EventSource` or `WebSocket` anywhere today.
3. **Cross-user changes.** A reviewer's decision creates the proposer's notice in a different
   browser where no navigation occurs. Only a timer reaches this case.

60 s sits inside SC-005's 90 s budget with headroom for request latency.

**Why not push**: the API deploys to Vercel serverless via Mangum, which does not sustain
long-lived connections, so server-sent events and websockets are not available on the
deployment target. Rejected on that ground, not on preference.

**Alternatives considered**: refresh-on-focus only (rejected — misses case 3 for a user
sitting on a dashboard); a shorter interval (rejected — no benefit inside the 90 s budget and
more requests); `BroadcastChannel` for cross-tab (rejected — the timer already converges
those, for one more moving part).

---

## R11 — Where the user lands after resolving

**Decision**: Replace `goHome()`'s `window.history.back()` in `ReviewAction.svelte` and
`ModifyAction.svelte` with an explicit navigation to the requests page.

**Rationale**: Two benefits from one change. It sidesteps the bfcache path in R10 case 1
entirely for the most common flow, and it closes the loop visually — the user returns to
their own list and sees the item they just resolved sitting in the Handled view, which is the
confirmation FR-019 and SC-004 describe. `history.back()` also has an inherent failure mode
here: the previous entry may be any page, including the one the user was on two steps ago.

---

## R12 — Shape of the client store

**Decision**: A plain TypeScript module, `ui/src/lib/notificationsStore.ts`, holding the
list plus a subscriber set, exposing `subscribe()`, `refresh()`, `start()` and `stop()`. Not
a `.svelte.ts` runes module.

**Rationale**: Everything else in `ui/src/lib/` is framework-free, and the store must remain
callable from the `.astro` shells as well as the Svelte islands. A plain module keeps that
option open at no cost; Svelte components subscribe in `onMount` and assign into local
`$state`. This follows the repo's existing split, where `lib/*` holds services and
`components/svelte/*` holds islands — the same split applied when `lib/foro.ts` shrank to
services and `Foro.svelte` took the UI.

**Failure behaviour** (FR-023): a failed refresh leaves the previous list in place and is
swallowed — the store never publishes an empty list on error, which is what today's bell does
via its `catch { items = [] }`.

---

## R13 — The requests page becomes a Svelte island

**Decision**: Convert `ui/src/pages/lib/my_asset_requests.astro` from a server-rendered table
to a shell that mounts a `MyAssetRequests.svelte` island. Delete
`ui/src/pages/lib/modifications.astro`.

**Rationale**: The page now needs two switchable views, an awaited-party indicator, an
inline acknowledge action and live refresh — all client behaviour that the current SSR table
cannot express. More decisively, an SSR table is a snapshot taken at request time, which is
precisely the staleness FR-021 forbids; leaving it server-rendered would mean the page and
the bell disagree by construction. Mounting follows the repo's manual `mount()` convention,
not `@astrojs/svelte`, whose island codegen is broken at the pinned version.

`modifications.astro` is deleted rather than kept: it is already unreferenced from every menu
and link (its only mention is a stale comment in `lib/notifications.ts:15`), and
`participations` now covers it — exactly the redundant surface FR-027 requires retiring.

---

## R14 — "New since I last looked" emphasis

**Decision**: Out of scope for this feature. If added later, it is a `localStorage`
timestamp compared against each entry's `created_at`, purely to bold recent rows.

**Rationale**: Removing `NOTIFIED` removes the server's notion of "seen". The spec records
that read-state is cosmetic and per-device, so it must never re-enter the server model. The
practical cost of omitting it is that the attention signal stays lit while work is genuinely
outstanding, which is the correct meaning for a task indicator. Deferred rather than built so
the feature does not reintroduce a read/work distinction by the back door.
