# Quickstart: Asset Notification Scheme Redesign

**Branch**: `003-asset-notifications-redesign` | **Phase**: 1 | **Date**: 2026-09-16

How to bring the feature up and prove it works. Contract details live in
[contracts/actions.md](contracts/actions.md); derivation rules in
[data-model.md](data-model.md).

---

## Prerequisites

```bash
make rebuild    # REQUIRED — seeds only run on a fresh volume, and this feature changes them
make test       # API health, DB readiness, admin user
```

`make rebuild` (not `make up`) is mandatory: the `WORKFLOW_STATUS` value rename lives in
`db/sql/41-lib-ddl.sql` and the seed rewrites in `42-lib-insert.sql` / `52-inits-insert.sql`,
none of which re-run on an existing volume. Skipping it leaves the database on the old
three-state vocabulary while the code writes the new one — every list will read as empty.

**Accounts** (all seeded with password `Admin123!`):

| Username | Profile | Use for |
|----------|---------|---------|
| `admin` | ADMINISTRATOR (superuser) | Admin paths; confirming nothing regressed for superusers |
| `santiago.marin` | REVIEWER | The reviewer side of every scenario |
| `adriana.velez` | COLLABORATOR | The proposer side of every scenario |

Run every scenario as `santiago.marin` / `adriana.velez`, **not** as `admin`. The superuser
bypasses privilege checks, which is what hid this domain's permission defects for months (see
the P1 "Known blockers" row in `memory/MEMORY.md`).

**URLs**: UI http://localhost:4321 · API docs http://localhost:8001/docs

---

## Verifying the data model changed

```bash
make shell      # psql
```

```sql
-- Expect exactly two rows: PENDING, HANDLED
SELECT value, label, sort_order FROM list_items
 WHERE list = 'WORKFLOW_STATUS' ORDER BY sort_order;

-- Expect zero rows in both
SELECT count(*) FROM actions        WHERE workflow_status IN ('ASSIGNED','NOTIFIED','FINISHED');
SELECT count(*) FROM collaborations WHERE workflow_status IN ('ASSIGNED','NOTIFIED','FINISHED');
```

---

## Scenario 1 — The page is complete and collapsed (US1)

Covers FR-006, FR-006a, FR-006b, FR-007, FR-011.

1. Log in as `adriana.velez`. Propose an asset from `/lib/explore?code=PROMPTS` → **Propose**,
   assigning `santiago.marin` as reviewer.
2. Open **Platform → My Asset Requests**.
   - **Expect**: the asset appears once, in **Pending**, marked as awaiting *another person*
     — nothing is being asked of Adriana yet.
3. Log in as `santiago.marin`, open the same page.
   - **Expect**: the same asset appears once, in **Pending**, marked as awaiting *you*, with a
     control to open the review.
4. As `santiago.marin`, approve the asset.
5. Back as `adriana.velez`, reload the page.
   - **Expect**: still **one** row for that asset — not one for the proposal and another for
     the publication notice. It is in **Pending**, awaiting *you* (the notice is
     unacknowledged).
6. Acknowledge the notice.
   - **Expect**: the row moves to **Handled**. Pending is now empty for that asset and shows
     its empty state if nothing else remains.

**The critical check is step 5.** One row, not two, is the whole point of FR-006b — two rows
would reintroduce inside the page the duplication this feature exists to remove.

## Scenario 2 — The indicator is a strict subset (US2)

Covers FR-013, FR-014, FR-015, FR-016, FR-017.

1. As `adriana.velez`, immediately after proposing (before any review), open the notification
   bell.
   - **Expect**: the proposed asset is **absent** — it is waiting on the reviewer, not on her.
     If she has nothing else outstanding, no attention dot is shown.
2. As `santiago.marin`, open the bell.
   - **Expect**: the review request is listed, and no control offers to clear it without
     deciding.
3. Open the panel's route to the full page.
   - **Expect**: arrival at My Asset Requests.
4. Give one user more than five outstanding items.
   - **Expect**: the panel shows the most recent five plus an indication that more exist.

**Invariant to check throughout**: every entry in the bell also appears in the page's Pending
view marked as awaiting *you*. The reverse must not hold — items awaiting someone else appear
only on the page.

## Scenario 3 — Nothing goes stale (US3)

Covers FR-019 through FR-024, SC-004, SC-005, SC-009.

1. **Same session.** As `santiago.marin`, decide a review. When you land back on the requests
   page, the item is in Handled and the bell count has dropped — **without reloading**.
2. **Back-navigation / bfcache.** From the requests page, open an asset, then use the
   browser's Back button.
   - **Expect**: current state, not the snapshot from the first visit. This is the specific
     failure the old `history.back()` path produced.
3. **Cross-user.** Open two browsers: `adriana.velez` sitting on any page, `santiago.marin`
   deciding her review. Leave Adriana's tab **visible** and do not touch it.
   - **Expect**: her indicator reflects the outcome within 90 seconds.
4. **Hidden tab.** Switch Adriana's tab to the background and watch the network panel.
   - **Expect**: no further requests while hidden. On returning to the tab, one immediate
     refresh.
5. **Failure.** Stop the API (`make down`), leave a tab open past the refresh interval.
   - **Expect**: the last known list stays on screen. No empty list, no blocking error.
   Restart and confirm it recovers on the next tick.
6. **Non-disruption.** Start typing review feedback and wait past the refresh interval.
   - **Expect**: the text is intact and the selected view has not changed.

## Scenario 4 — One vocabulary everywhere (US4)

Covers FR-025, FR-026, SC-006.

1. Open an asset's **Activity** tab.
   - **Expect**: no entry reading "was notified to review the asset" or similar — viewing is
     no longer recorded.
2. Check the workflow-stage badge, the requests page's state column, and the Admin → Lists
   screen for `WORKFLOW_STATUS`.
   - **Expect**: only "Pending" / "Handled" anywhere.
3. Switch language EN ⇄ ES.
   - **Expect**: "Pendiente" / "Atendido" on every one of those surfaces.

## Scenario 5 — Retired surfaces are gone (FR-027)

- `/lib/modifications` → no longer resolves to a working page.
- `GET /api/actions/reviews`, `GET /api/actions/modifications` → gone (422, same reason),
  `POST /api/actions/notifications/{id}/notified` → gone (422: the generic `/{id}` route catches the path and cannot parse the segment as an id).
- `POST /api/actions/notifications/{id}/acknowledge` on a `REVIEW` action → `400`, with the
  review still pending afterwards (it must not have been silently closed).

---

## Automated tests

Principle III requires automated tests for contract and permission changes; this feature is
both.

Run the suite **inside the container**:

```bash
docker compose exec -T api uv run pytest -q
```

The container's Python 3.14 virtualenv imports the backend fine. The pydantic
`eval_type_backport` `AssertionError` recorded in `memory/MEMORY.md` (2026-07-02) no longer
reproduces, and `api/pyproject.toml` now pins `requires-python = ">=3.14"`, so building a 3.12
virtualenv would contradict the project's own requirement. If a stale `api/.venv` leaked onto
the host through the bind mount, delete it — `docker-compose.yml:77` shields the container's
own venv with an anonymous volume, so the host copy is never used.

**Expected result**: `8 failed, 243 passed`. The 8 failures are pre-existing and live in
`test_auth.py` (3), `test_health.py` (1) and `test_users.py` (4) — none of which this feature
touches. A failure anywhere else is new.

Coverage added by this feature: `api/tests/test_lib_asset_requests.py` (the seven derivation
cases, the one-row-per-asset invariant, ordering and pagination) and a rewritten
`api/tests/test_lib_notifications.py` (the feed as a strict subset, the acknowledge guard, and
assertions that the retired routes and the `unread` field are gone).

## UI build check

```bash
cd ui && bun run build     # or: bunx astro check
```

Browser interaction — the tab switch, the acknowledge control, the refresh triggers — is not
covered by any automated harness in this repo (no Playwright). The scenarios above are the
manual pass and should be walked before the PR.
