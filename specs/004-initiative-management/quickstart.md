# Quickstart & Validation: Initiative Management

**Branch**: `004-initiative-management` | **Phase**: 1 | **Date**: 2026-09-23

This guide proves the feature works end to end. Endpoint details are in
[contracts/initiatives-api.md](contracts/initiatives-api.md); rules and the state machine are in
[data-model.md](data-model.md).

## Prerequisites

```bash
make rebuild        # seeds changed (KICKOFF, es labels, statuses, init_permissions) → fresh volume
make dev            # UI http://localhost:4321 · API docs http://localhost:8001/docs
make test           # health checks green
```

**Already-provisioned DB (Neon or a kept local volume)** — instead of `make rebuild`, apply
[`provisioned-db.sql`](provisioned-db.sql). It mirrors the seed diff exactly: `COLLAB_TYPE/KICKOFF`
plus the `es` rows of `INITIATIVE_STATUS`, `COLLAB_TYPE`, `EXPECTED_IMPACT`, `PRIORITY_LEVEL`,
`INITIATIVE_TYPE`; the initiative status/type realignment (data-model.md § 4); the
`felipe.cardenas` promotion to ADMINISTRATIVE; and the seeded ANSWER's `parent` fix (it pointed at an
ACCEPTANCE row, so it never threaded under its question). It is idempotent and runs in one
transaction:

```bash
docker compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  < specs/004-initiative-management/provisioned-db.sql
```

(This is how the local dev DB was brought up to date during implementation — `make rebuild`
would also work but wipes the volume.)

Accounts: `admin` / `Admin123!` (superuser). Validate access scoping with `felipe.cardenas`
(ADMINISTRATIVE in the seed; same default password as the other seeded users). Give him his
test grants first — they are deliberately **not** part of the seed:

```bash
docker compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  < specs/004-initiative-management/test-owner.sql
```

He then holds `INITS/INITIATIVES`, MANAGE on initiatives 1 and 3, VIEW on 2, nothing on 4–5
(the undo statement is at the bottom of [`test-owner.sql`](test-owner.sql)). Never validate
only as the superuser, which bypasses every check.

## Automated

```bash
docker compose exec -T api uv run pytest -q
```

Expected: the new `test_inits_*.py` modules pass; `lib` permission suites
(`test_lib_permissions.py`, `test_lib_access_enforcement.py`, `test_assets_access.py`,
`test_assets_category_with_access.py`) still pass after the engine extraction; only the 8
pre-existing failures in `test_auth.py` / `test_health.py` / `test_users.py` remain.

```bash
cd ui && bun run build && bunx astro check   # clean build; error count ≤ current baseline (138)
```

## Scenarios

Obtain a token for API calls from `/docs` (Authorize) or reuse the browser cookie.

### S1 — List is scoped, no create (US1)

1. As the ADMINISTRATIVE user open **Initiatives › Initiative Management**
   (`/inits/initiatives`).
   ✅ Only initiatives with a grant reaching that user are listed; no "New" button anywhere,
   including the empty state.
2. `GET /api/initiatives/with-access` as that user → same set; each row has `my_access`,
   `is_favorite`, `allowed_statuses`.
3. As `admin` → all 5 initiatives.
4. Filter by status, type, priority, impact, access level, favorites; search by name.
   ✅ Filters combine; the count updates.
5. Columns read name, type, priority, status, tags, actions (no impact, score or access). A
   VIEW-only row shows no edit/delete buttons but does show the favorite star; toggling it
   persists (reload → still starred) and the "My favorites" toggle filters by it.
6. Switch language to Español. ✅ Status, type, priority and impact labels are in Spanish.

### S2 — Tabs save only their slice (US2)

Open a MANAGE initiative.

1. ✅ Title reads "Edit initiative"; tabs in order Core Fields, Diagnosis Questions, Related
   Assets, Permissions, Discussion, History, sitting the same distance below the header line as
   in Edit Asset.
2. **Core Fields**: change description → *Save core fields*. ✅ Only the description changed; no
   History entry added. Clear the name → save is blocked, field flagged.
3. **Related Assets**: add a link (asset + relation type + rationale) → *Save related assets*.
   ✅ The link appears; open that asset in Asset Management → its **Related Inits** tab shows the
   same link. Remove it and save; add it again → ✅ restored, not duplicated.
4. **Permissions**: grant VIEW to a user → *Save permissions*. Revoke it → ✅ gone from the list;
   `GET /api/init_permissions/init/{id}` no longer returns it; the DB row still exists with
   `valid_to` set.
5. **Diagnosis Questions** on initiative 3 (diagnosed) → ✅ a table: criterion | proposer answer
   (indigo) | reviewer answer (emerald), labels in the current language; two score cards (proposer
   15, reviewer 15, "6 of 6 answered"); each rationale hidden until its Show rationale switch is
   turned on; nothing editable, save hidden.
   On initiative 4 → reviewer column and card "pending diagnosis". On initiative 5 → "not answered".
6. **Discussion** on initiative 1 → ✅ question with its answer threaded beneath, comment listed;
   post a comment and a question, answer a question, delete your own entry (others' entries offer
   no delete); save button hidden (each post saves itself).
7. **History** → ✅ newest first, actor per entry, localised labels, "created" marker last.
8. Edit a field on one tab, then close → ✅ discard confirmation.

### S3 — Owner status moves (US3)

| Start | Action | Expected |
|-------|--------|----------|
| Initiative 3 (ACCEPTED) | open Core Fields | select offers Accepted, In Progress, Delivered, Archived |
| 3 → IN_PROGRESS | save | status changes; History top entry "Kickoff" by you |
| 3 (IN_PROGRESS) | open again | select offers In Progress, Delivered, Archived |
| 3 → DELIVERED | save | History "Delivery"; **no** entry in anyone's notifications / requests |
| 3 (DELIVERED) → ARCHIVED | save | History "Archiving"; select now locked with the "closed" hint |
| Initiative 4 (ACTIVATED) | open Core Fields | select locked; hint says the workflow sets this status |
| Initiative 1 | edit description only | no Kickoff/Delivery/Archiving entry |

Direct API refusals (all must return **400** and write nothing):

```bash
# ACTIVATED → DELIVERED
curl -X PUT .../api/initiatives/4 -d '{"status":"DELIVERED"}'
# DELIVERED → IN_PROGRESS (backwards)
curl -X PUT .../api/initiatives/2 -d '{"status":"IN_PROGRESS"}'
# ARCHIVED → anything
curl -X PUT .../api/initiatives/3 -d '{"status":"ACCEPTED"}'
```

Then `GET /api/collaborations/history/init/{id}` → no new rows for the refused attempts.

### S4 — Authorization (security)

| Caller | Request | Expected |
|--------|---------|----------|
| no token | any endpoint | 401 |
| COLLABORATOR (no `INITS/INITIATIVES`) | `GET /api/initiatives/with-access` | 403 |
| ADMINISTRATIVE with VIEW only on init X | `PUT /api/initiatives/X` | 403 |
| same | `POST /api/init_permissions/` granting self MANAGE on X | 403 |
| same | `POST /api/initiatives/X/assets` | 403 |
| ADMINISTRATIVE with no grant on init Y | `GET /api/initiatives/Y/diagnostics` | 403 |
| ADMINISTRATIVE, MANAGE on X, linking an asset they cannot see | `POST /api/initiatives/X/assets` | 403 |

## Cleanup

Revert test edits by `make rebuild`, or restore the touched initiative's fields/status by hand.
Revoked grants and logically-deleted links stay as records by design.

## Not covered by automation

No browser harness exists in this repo: the tab UI, status-select narrowing, hints, Spanish
labels, and the discard dialog (S1.4–S1.6, S2, the UI half of S3) need a manual click-through,
recorded in the PR.
