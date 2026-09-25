# Quickstart: validating Explore Initiatives, Propose, Diagnosis & Notifications

**Branch**: `005-explore-initiatives` | **Phase**: 1 | **Date**: 2026-09-24

This guide proves the feature end to end. For endpoint details see [contracts/initiatives-workflow-api.md](contracts/initiatives-workflow-api.md); for page behaviour see [contracts/ui-surfaces.md](contracts/ui-surfaces.md). **Validate as seeded non-superusers.** The `admin` superuser bypasses the gates this feature depends on.

## Prerequisites

```bash
make rebuild     # fresh volume: picks up the two seed edits (data-model.md § Seed changes)
make dev         # UI http://localhost:4321 · API docs http://localhost:8001/docs
make test        # health checks green
```

Seeded users (password per seed):

| User | Profile | Role in the scenarios |
|---|---|---|
| `adriana.velez` | COLLABORATOR | proposer (P) |
| `santiago.marin` | REVIEWER | reviewer (R) |
| `admin` | superuser | sanity only |

## Automated checks

```bash
docker compose exec -T api uv run pytest -q
```

- **Expected:** the 8 pre-existing failures (`test_auth` / `test_health` / `test_users`), with everything else passing. That includes the new `test_inits_{propose,diagnosis,modify,requests,votes,explore}.py` and `test_internal_reviewers.py`.
- **Regression guard for the reviewer extraction:** the lib suites `test_lib_{propose,review,modify,notifications,asset_requests,votes}.py` pass unchanged.

```bash
cd ui && bun run build && bunx astro check   # build clean; astro check at the unchanged baseline
```

## Scenario 1: Explore (US3)

1. Sign in as P and open **Explore Initiatives** from the sidebar.
   - **Expect:** a header, search, "★ My favorites", a privileges filter showing exactly Public / Shared with me / My role / My team / My unit / My projects (defaulting to Public, with no "all"), "+ Propose", and full-width initiative rows (not the asset grid).
2. Switch through the privilege options.
   - **Expect:** each shows only initiatives shared through that scope. With the seed, initiative 1 appears under Public.
   - Initiatives 4 and 5 (ACTIVATED) never appear. Neither does anything Rejected or Archived.
3. Star an initiative, then turn "My favorites" on.
   - **Expect:** it stays. Unstar it: it disappears without a reload.
4. Vote 👍, then 👍 again.
   - **Expect:** the tally goes up, then back down. 👎 switches the vote.
5. Click a card.
   - **Expect:** the detail opens with Core Fields / Diagnosis Questions / Related Assets / Discussion / History, and no Permissions tab.
   - Post a comment. **Expect:** it succeeds (this needs the R4 seed change).
6. Narrow the window to about 390 px.
   - **Expect:** the cards stack with no horizontal scroll.

## Scenario 2: Propose (US1, US2)

1. As P, press **+ Propose**.
   - **Expect:** three tabs, and the Core footer shows "Back to initiatives" and "Diagnosis questions >".
2. Open the reviewer field.
   - **Expect:** R is listed and P is not.
3. Press "Diagnosis questions >" with the name empty.
   - **Expect:** an inline error, and the wizard stays on Core.
4. Fill the required fields and advance.
   - **Expect:** six criteria, each with scale options in the current language. The footer shows Back / Request diagnosis / Related Assets >.
5. Press "Request diagnosis" with one criterion unanswered.
   - **Expect:** that question is marked and nothing is submitted.
6. Answer all of them, press "Related Assets >", and stage an asset with USED_BY. Stage the same pair again.
   - **Expect:** the duplicate is refused. The footer shows Back / Request diagnosis.
7. Press **Request diagnosis**.
   - **Expect:** a blocking dialog mentioning My Initiative Requests; "Got it" then returns you to Explore.
   - The new initiative is not in the gallery, because it is ACTIVATED.
8. Verify the stored records (`make shell`):

   ```sql
   SELECT id, status FROM initiatives ORDER BY id DESC LIMIT 1;             -- ACTIVATED
   SELECT count(*) FROM diagnostics WHERE init = <id>;                       -- 6
   SELECT type, workflow_status, user_id FROM collaborations WHERE init = <id>;  -- ACTIVATION/HANDLED (P), DIAGNOSIS/PENDING (R)
   SELECT target_code, access_level FROM init_permissions WHERE init = <id>; -- P and R, MANAGE
   SELECT * FROM asset_inits WHERE init = <id>;                              -- the staged link
   ```

9. **Negative checks** (API docs, as P):
   - a `POST /api/initiatives/propose` with `reviewer_id` = P's own id → 400;
   - one with five answers → 400;
   - one with an out-of-scale score (4) → 400.
   - **Expect:** no rows created by any of these.

## Scenario 3: Notifications and requests (US4, US5)

1. As P, open **Account Menu → My Workspace**.
   - **Expect:** "My Initiative Requests" directly below "My Asset Requests".
   - Open it. **Expect:** the new initiative, once, under Pending, marked "Someone else · Waiting for diagnosis".
2. As P, open the bell.
   - **Expect:** Assets and Initiatives tabs. The Initiatives tab does not list the proposal, because it is waiting on R.
3. Sign in as R and wait at most 60 s, or refocus the tab.
   - **Expect:** the bell badge is on. The Initiatives tab shows the initiative with "Diagnosis requested". The Assets tab is unchanged from before.

## Scenario 4: Full loop (US6, US7, US8)

1. As R, click the notification.
   - **Expect:** the diagnose page shows P's answers and rationale.
   - Opening it created no rows (`collaborations` count unchanged).
2. Press **Request changes** with empty feedback.
   - **Expect:** refused. Add feedback, answer all criteria, and submit.
   - **Expect:** status FEEDBACK. R's row is DIAGNOSIS/HANDLED, and P has MODIFICATION/PENDING with the feedback.
   - R lands on My Initiative Requests, where the initiative shows "Someone else".
3. As P, the bell shows "Changes requested". Open it.
   - **Expect:** the feedback panel and prefilled fields. Edit the description and one answer, then Resubmit.
   - **Expect:** status ACTIVATED, and R has a new DIAGNOSIS/PENDING.
4. As R, diagnose again with **Accept**.
   - **Expect:** status ACCEPTED, `score` = Σ reviewer answers, and P has ACCEPTANCE/PENDING.
   - The initiative now appears in Explore, under a scope P or R can see.
5. As P, open the acceptance notice.
   - **Expect:** the outcome card. Leave without acknowledging: it stays in the bell and under Pending, marked "You".
   - Reopen and press **Acknowledge**. **Expect:** it leaves the bell and moves to the Handled view.
6. **Negative checks:**
   - As P, `POST /api/initiatives/<id>/diagnose` → 403.
   - As R, diagnose an ACCEPTED initiative → 409.
   - As R, `POST .../resubmit` → 403.
   - Acknowledge someone else's collaboration → 404.

## Scenario 5: Asset side unchanged (SC-006)

Propose an asset as P and review it as R, using the existing flow. **Expect:** the bell's Assets tab and My Asset Requests behave exactly as before.

## Provisioned databases (no `make rebuild`)

Run once against an existing local or Neon DB:

```sql
UPDATE privileges SET can_edit = TRUE
 WHERE profile IN ('COLLABORATOR','REVIEWER') AND module = 'INITS' AND option = 'EXPLORE';
DELETE FROM collaborations WHERE id = 8 AND type = 'DELIVERY' AND workflow_status = 'PENDING';
```


## Clean-up

Test initiatives stay behind: there is no delete in the workflow. Logically delete them with `UPDATE initiatives SET is_active = FALSE WHERE id = <id>;`, or run `make rebuild`.
