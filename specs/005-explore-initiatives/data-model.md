# Data Model: Explore Initiatives, Propose Initiative & Initiative Notifications

**Branch**: `005-explore-initiatives` | **Phase**: 1 | **Date**: 2026-09-24

**No DDL change.** Every table already exists in `db/sql/51-inits-ddl.sql` and is mapped by spec 004 (`api/app/inits/internal/models.py`; `AssetInit` in `lib`). This feature adds **request/response schemas**, **state rules**, and **two seed edits**.

## Tables used (unchanged)

| Table | Role in this feature |
|---|---|
| `initiatives` | Created by Propose (ACTIVATED), status moved by Diagnosis and Modify, `score` set by Diagnosis |
| `criterias` | Defines the questions. Active rows = the required set. `list` → the answer scale |
| `list_items` | Scale values and labels per criterion (`list = criterias.list`, `lang`) |
| `diagnostics` | PK `(init, criteria)`. `creator_score` + `rationale` written by Propose and Modify; `reviewer_score` written by Diagnosis |
| `asset_inits` | PK `(asset, init, type)`. Written by Propose |
| `collaborations` | Workflow and community substrate (see state machine below). VOTE rows for votes |
| `init_permissions` | USER/MANAGE grants for the proposer and the reviewer, written by Propose |
| `favorite_inits` | Read by Explore (`is_favorite`). The existing PUT/DELETE favorite routes are reused |

## Collaboration threads

A **thread** is `(init, user_id, type)`. Its **current state** is its newest row (`created_at`, then `id`). Rows are only ever inserted.

| `type` | Written as | By | Transition |
|---|---|---|---|
| `ACTIVATION` | HANDLED | proposer | Propose |
| `DIAGNOSIS` | PENDING | reviewer | Propose; Modify (re-arm) |
| `DIAGNOSIS` | HANDLED | reviewer | Diagnosis decision |
| `MODIFICATION` | PENDING | proposer | Diagnosis (`changes`) |
| `MODIFICATION` | HANDLED | proposer | Modify |
| `ACCEPTANCE` / `REJECTION` | PENDING | proposer | Diagnosis (`accept` / `reject`), `content` = feedback |
| `ACCEPTANCE` / `REJECTION` | HANDLED | proposer | Acknowledge |
| `VOTE` | `workflow_status` NULL | voter | Vote set/toggle/clear (one active row per user + init) |
| `KICKOFF` / `DELIVERY` / `ARCHIVING` | HANDLED | owner | Spec 004. Not participation types, so ignored here |

Constant sets (`inits/internal/requests_service.py`):

```text
NOTIFICATION_TYPES    = (DIAGNOSIS, MODIFICATION, ACCEPTANCE, REJECTION)
PARTICIPATION_TYPES   = (ACTIVATION,) + NOTIFICATION_TYPES
ACKNOWLEDGEABLE_TYPES = (ACCEPTANCE, REJECTION)
IN_MOTION_STATUSES    = (ACTIVATED, FEEDBACK)
EXPLORE_STATUSES      = (ACCEPTED, IN_PROGRESS, DELIVERED)   # in initiatives_explore / status_service
```

## Initiative status machine (workflow part, added by this feature)

```text
            propose                 diagnose: accept
   (none) ─────────► ACTIVATED ──────────────────────► ACCEPTED ──► (spec 004 owner moves)
                        │  ▲     diagnose: reject
                        │  │  ──────────────────────► REJECTED   (terminal)
      diagnose: changes │  │ modify (resubmit)
                        ▼  │
                      FEEDBACK
```

- Diagnosis requires `ACTIVATED` and resubmission requires `FEEDBACK`. Anything else → **409**.
- The spec 004 `status_service.ALLOWED_TRANSITIONS` (owner moves) is unchanged. `PUT /api/initiatives/{id}` still refuses ACTIVATED/FEEDBACK/ACCEPTED/REJECTED moves.

## Request / response schemas (new, `inits/internal/models.py`)

### `DiagnosisAnswer`
| Field | Type | Rule |
|---|---|---|
| `score` | int | Must be a value of the criterion's scale (`list_items.value` where `list = criterias.list`, `lang = 'en'`) |
| `rationale` | str? | ≤ 2000 chars. Blank → NULL. Proposer only; ignored on Diagnosis |

### `InitiativeProposeRequest`
| Field | Type | Rule |
|---|---|---|
| `name` | str | Required, trimmed non-empty, ≤ 100 |
| `description` | str? | ≤ 500 |
| `type` | str? | `INITIATIVE_TYPE` value |
| `expected_impact` | str | Required, `EXPECTED_IMPACT` value |
| `priority_level` | str | Required, `PRIORITY_LEVEL` value |
| `reference`, `detail` | str? | — |
| `tags` | list[str]? | — |
| `reviewer_id` | int? | Eligible reviewer. A non-admin proposer may not name themselves. Omitted → auto-assigned (R2) |
| `answers` | dict[criteria_code → DiagnosisAnswer] | Must cover exactly the active criteria. Unknown codes → 400 |
| `assets` | list[{asset: int, type: str, rationale?: str}] | Each asset active and visible to the caller. `type` a `RELATION_TYPE` value. No duplicate `(asset, type)` |

No `status`: the proposal is always `ACTIVATED`. No `score`: that is set by Diagnosis.

### `InitiativeDiagnoseRequest`
| Field | Type | Rule |
|---|---|---|
| `decision` | `"accept" \| "reject" \| "changes"` | — |
| `feedback` | str? | ≤ 2000. Required (non-blank) for `reject` and `changes` |
| `answers` | dict[criteria_code → int] | Reviewer scores covering every active criterion, in scale |

### `InitiativeResubmitRequest`
All core fields of `InitiativeProposeRequest` are optional and applied when sent (`exclude_unset`), with the same validation. `answers` (dict → DiagnosisAnswer) is optional; when sent it must be complete. `reviewer_id`, `assets` and `status` are not accepted.

### `ReviewerOption` (reused from `lib` models)
`{value: int, label: str, profile: str, is_superuser: bool}`

### `LinkableAsset`
`{value: int, label: str, category: str}`: active assets the caller can see (superuser: all).

### `InitiativeExploreItem`
Every `InitiativeBase` field plus `id`, and:

| Field | Type |
|---|---|
| `my_access` | `"MANAGE" \| "VIEW"` |
| `is_favorite` | bool |
| `permission_scopes` | list[str] from {PUBLIC, USER, ROLE, TEAM, UNIT, PROJECT} |
| `votes` | `InitVoteTally` |
| `discussion_count` | int (active COMMENT + QUESTION + ANSWER) |
| `related_assets_count` | int (active `asset_inits` rows) |

### `InitVoteTally`
`{init: int, positive: int, negative: int, score: int, my_vote: "POSITIVE" | "NEGATIVE" | null}`

### `InitiativeRequest` (the My Initiative Requests row)
Mirrors the lib `AssetRequest`:

| Field | Type |
|---|---|
| `init` | int |
| `init_name` | str? |
| `init_status` | str? |
| `roles` | list[`"PROPOSER" \| "REVIEWER"`] |
| `state` | `"PENDING" \| "HANDLED"` |
| `awaited_party` | `"SELF" \| "OTHER" \| null` |
| `pending_collab_id` | int? (only when SELF) |
| `pending_collab_type` | str? (only when SELF) |
| `last_change_at` | datetime |

### `InitNotificationItem` / `InitNotificationFeed`
- `InitNotificationItem {id (= pending_collab_id), init, init_name, type (= pending_collab_type), created_at (= last_change_at)}`
- `InitNotificationFeed {items: InitNotificationItem[], total: int}`

## Derivation rules (My Initiative Requests)

For each initiative where the caller has any participation-type thread:

1. **owed** = the newest of the caller's threads whose type ∈ `NOTIFICATION_TYPES` and whose current state is PENDING.
2. If **owed** exists → `state = PENDING`, `awaited_party = SELF`, `pending_collab_* = owed`.
3. Else, if `initiative.status ∈ IN_MOTION_STATUSES` → `PENDING` / `OTHER`.
4. Else → `HANDLED` / null.

Step 1 always runs before the status check (FR-034). Notifications = the `SELF` rows only (FR-036), newest first, `limit` default 5, `total` = the full SELF count.

## Validation summary (server-authoritative, FR-022)

| Check | Propose | Diagnose | Modify |
|---|---|---|---|
| Required core fields + list values | ✔ | — | ✔ (when sent) |
| Answers cover all active criteria, in scale | ✔ | ✔ | ✔ (when sent) |
| Reviewer eligible + no self-review (non-admin) | ✔ | ✔ (still eligible) | — |
| Assets active + visible + relation type valid + no duplicates | ✔ | — | — |
| Caller holds the PENDING thread | — | DIAGNOSIS | MODIFICATION |
| Caller is the proposer (earliest ACTIVATION) | — | — | ✔ |
| Status precondition | — | ACTIVATED | FEEDBACK |
| Feedback required | — | reject / changes | — |

## Seed changes

| File | Change | Why |
|---|---|---|
| `db/sql/12-admin-insert.sql` | `('COLLABORATOR','INITS','EXPLORE', TRUE)` and `('REVIEWER','INITS','EXPLORE', TRUE)` (were FALSE) | R4: those profiles must be able to propose, vote and post |
| `db/sql/52-inits-insert.sql` | Delete collaboration row id 8 (`DELIVERY` / `PENDING`) | R7: Delivery raises no notice (spec 004). The row carried no information, since the HANDLED row 10 survives |

Provisioned DBs: see [quickstart.md](quickstart.md) § Provisioned databases.
