# Data Model: Asset Notification Scheme Redesign

**Branch**: `003-asset-notifications-redesign` | **Phase**: 1 | **Date**: 2026-09-16

No new table is created. Per the Constitution's *Established Domain Patterns*
("Contribution / approval workflows"), this feature extends the existing `actions`
substrate and its `WORKFLOW_STATUS` enum rather than introducing a bespoke table.

---

## 1. Enum change: `WORKFLOW_STATUS`

Seeded in `db/sql/41-lib-ddl.sql` as a `list_items` list, referenced by
`actions.workflow_status` (`41-lib-ddl.sql:51`) and `collaborations.workflow_status`
(`51-inits-ddl.sql:65`).

| Before | After | Label EN | Label ES | Notes |
|--------|-------|----------|----------|-------|
| `ASSIGNED` (sort 10) | `PENDING` (sort 10) | Pending | Pendiente | Awaiting someone's action |
| `NOTIFIED` (sort 20) | *(removed)* | — | — | Read-state; see research R3 |
| `FINISHED` (sort 30) | `HANDLED` (sort 20) | Handled | Atendido | No longer awaiting action |

The list is seeded in `en` only; the Spanish label is supplied by the UI i18n files, matching
current behaviour.

## 2. Table: `actions` — unchanged structurally

No DDL change. Only the values written into `workflow_status` change, and which rows the seed
contains.

**Row lifecycle (unchanged mechanism, per FR-005)**: every transition is a new row; the
original assignment row is never mutated. A thread is the set of rows sharing
`(asset, type, user_id)`; its state is the `workflow_status` of its newest row.

| Action type | Has a pending phase? | States written |
|-------------|----------------------|----------------|
| `REVIEW` | yes | `PENDING` on assignment → `HANDLED` on decision |
| `MODIFICATION` | yes | `PENDING` on assignment → `HANDLED` on resubmit |
| `PUBLICATION` | yes | `PENDING` on outcome → `HANDLED` on acknowledgement |
| `REJECTION` | yes | `PENDING` on outcome → `HANDLED` on acknowledgement |
| `PROPOSAL` | no | written directly as `HANDLED` |
| `VERSIONING` | no | written directly as `HANDLED` |
| `DEPRECATION` | no | written directly as `HANDLED` |
| `VOTE`, `COMMENT`, `QUESTION`, `ANSWER` | n/a | `workflow_status` stays `NULL` |

**Seed rows affected** (`db/sql/42-lib-insert.sql`, `actions` block from line 458):
24 rows `ASSIGNED` → `PENDING`; 24 rows `FINISHED` → `HANDLED`; ~24 `NOTIFIED` rows deleted.
Ids are not renumbered — gaps are harmless because the block ends with
`setval(pg_get_serial_sequence('actions','id'), MAX(id))`, and no deleted row is referenced
as a `parent`.

## 3. Table: `collaborations` (inits) — unchanged structurally

Same value rewrite in `db/sql/52-inits-insert.sql` (block from line 113): `ACTIVATION`,
`DIAGNOSIS`, `ACCEPTANCE`, `DELIVERY` rows. No application code reads these values today, so
this side is seed-only.

---

## 4. Derived read model: `Participation`

Not persisted. Computed per request by `actions_service` from the caller's own workflow rows
joined to their assets. This is the unit the requests page lists (FR-006b: one per
`(user, asset)`).

### Fields

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `asset` | `int` | `actions.asset` | Grouping key |
| `asset_name` | `str \| null` | batched `Asset` fetch | `null` if the asset was hard-deleted |
| `asset_status` | `str` | `Asset.status` | One of the `ASSET_STATUS` values |
| `category` | `str \| null` | `Asset.category` | For display/linking |
| `roles` | `list[str]` | which types the user has | `PROPOSER` and/or `REVIEWER` |
| `pending_action_id` | `int \| null` | newest `PENDING` row for this user | The id the action screen is opened with |
| `pending_action_type` | `str \| null` | that row's `type` | Drives which screen to open |
| `awaited_party` | `"SELF" \| "OTHER" \| null` | derived (see below) | `null` when closed |
| `state` | `"PENDING" \| "HANDLED"` | derived | Which view the entry belongs to |
| `last_change_at` | `datetime` | newest contributing row | Sort key, newest first |

### Derivation rules

Let `T` be the caller's threads on this asset over types
`{REVIEW, MODIFICATION, PUBLICATION, REJECTION}`, and `S` the asset's status.

```
awaits_self := ∃ t ∈ T where latest(t).workflow_status == PENDING

if awaits_self:
    state = PENDING,  awaited_party = SELF
    pending_action_id/type = newest such row
elif S ∈ {PROPOSED, FEEDBACK}:
    state = PENDING,  awaited_party = OTHER
else:                       # S ∈ {PUBLISHED, REJECTED, DEPRECATED}
    state = HANDLED, awaited_party = null
```

`ASSET_STATUS` values are seeded in `db/sql/41-lib-ddl.sql:166-170`.

**Worked cases**

| Situation | `state` | `awaited_party` |
|-----------|---------|-----------------|
| Review assigned to me, undecided | PENDING | SELF |
| I proposed; reviewer has not decided | PENDING | OTHER |
| Reviewer asked for changes; I have not resubmitted | PENDING | SELF |
| Published; I have not acknowledged the notice | PENDING | SELF |
| Published; I acknowledged | HANDLED | — |
| Published; I was the reviewer (no notice for me) | HANDLED | — |
| I proposed long ago; never reviewed | PENDING | OTHER |

The fifth and sixth rows are why `awaits_self` is evaluated **before** asset status: an
unacknowledged notice on a terminal asset must still read as pending (FR-010a).

### Invariants

- **INV-1** (FR-006b): at most one `Participation` per `(user, asset)`.
- **INV-2** (FR-013): the notification feed is exactly the subset with
  `awaited_party == SELF`. The indicator can never contain something the page does not.
- **INV-3** (FR-003): opening any screen writes no row. State changes only on decide,
  resubmit or acknowledge.
- **INV-4**: an asset with no `PROPOSAL` row by the caller and no request directed at the
  caller yields no `Participation` (research R7).

---

## 5. Entities removed from the model

| Removed | Replaced by |
|---------|-------------|
| `NOTIFIED` workflow state | nothing — read-state leaves the server model entirely |
| `unread` field on the notification item | `awaited_party`; a feed entry is by definition awaiting the user |
| `DISMISSIBLE_TYPES` / `NotificationNotDismissible` | the acknowledge guard, which keeps the same informational-types-only rule under an accurate name |
| `list_review_requests` / `list_pending_modifications` | `list_participations`, filtered by `state` |
