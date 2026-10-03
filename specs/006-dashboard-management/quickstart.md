# Quickstart — validating Dashboard Management (006)

Runnable checks that the feature works end-to-end. The endpoints are in
[contracts/dashboards-api.md](contracts/dashboards-api.md) and the rules in
[data-model.md](data-model.md).

## Prerequisites

```bash
make rebuild        # fresh volume picks up the new es list rows
make dev            # UI http://localhost:4321 · API http://localhost:8001/docs
```

On an already-provisioned DB, run `specs/006-dashboard-management/provisioned-db.sql` once
instead of rebuilding. Then run `specs/006-dashboard-management/test-owner.sql` (test grants for
`felipe.cardenas`, ADMINISTRATIVE: MANAGE on dashboard 1, VIEW on 2. Dashboard 3 is already
PUBLIC/VIEW in the seed).

## Automated

```bash
docker compose exec -T api uv run pytest -q          # baseline 570 passed, 0 failed
docker compose exec -T api uv run pytest -q tests/test_ana_*.py
make test
cd ui && bun run build                               # clean
```

All `test_inits_*` suites must still pass unchanged, because they guard the shared list
validation and the permissions-tab extraction.

## Manual scenarios

Sign in as `felipe.cardenas` for 1–6 and as `admin` for 7. Never use the superuser alone to prove
access rules.

1. **Scoped list (US1)**: open `/ana/dashboards`. Dashboard 1 (MANAGE), 2 (VIEW) and 3 (VIEW,
   through the seed's PUBLIC grant) are listed. Rows 2 and 3 have no edit or remove action. As
   `admin`, create a dashboard and revoke its creator grant, then confirm felipe does **not**
   see it. The type, source and status funnels, the
   privileges filter and the search each narrow the list. Switch the language: type, source and
   status labels change to Spanish.
2. **Create (US1, FR-009/010)**: click *New Dashboard*. Choose source *Power BI* with
   `http://x` and the save is blocked. With `https://app.powerbi.com/view?r=test` the save
   succeeds, the status is *Draft*, and the dialog switches to edit mode with Parameters and
   Permissions enabled. The Permissions tab shows a USER/MANAGE grant for felipe. Reload: the
   dashboard is in the list.
3. **Status (US2)**: on the new dashboard the status control offers only Draft and Published.
   Publish it. It now offers Published, Archived and Retired. Archive it. It offers Archived,
   Published and Retired. Retire it. The control is locked with an explanation. As a direct API
   check, `PUT /api/dashboards/{id}` with `"status": "DRAFT"` → 400 and nothing changes.
4. **Parameters (US3)**:
   - Add `date_from` (Date, required, default `2026-13-01`) and the save is blocked. With
     `2026-01-01` it saves.
   - Add `granularity` (String) with a list and pick the default from the list values.
   - Add `date_from` again → refused (duplicate).
   - Remove `granularity`, save, then re-add it. It comes back.
   - Each row's value source reads *Entered by the viewer*, *From a list* or *Bound to a grant*.
   - At the dialog's normal size, the form takes two compact rows plus one help line. Part of
     the declared parameters list (dashboard 1 has four) is visible below it without scrolling.
     Switching the value source changes only the second row.
5. **Binding (US3-9/11, US4-7)**:
   - On dashboard 1, add a TEAM/ANALYTICS VIEW grant and save Permissions.
   - In Parameters, add `team` bound to a grant. Only non-public live grants are offered. Save.
     The row reads "Bound to the grant for team ANALYTICS".
   - Revoke that grant: a warning names `team`. After saving, the parameter is still listed.
6. **Permissions (US4)**:
   - The tab looks like the Permissions tab of `/inits/initiatives`: target type, target and
     access level only, with no date fields and no dates on the listed grants.
   - Grant VIEW to user `adriana.velez` and save. It takes effect immediately.
   - Sign in as adriana: the dashboard is visible and read-only (she needs `ANA/DASHBOARDS`;
     grant it temporarily or expect the 403 and check the grant through the API instead).
   - Back as felipe, add the same grant again → refused. Revoke it, then add it again → allowed.
7. **Superuser**: as `admin`, every active dashboard is listed with full MANAGE.
7a. **Favorites (FR-004a)**:
   - As felipe, click the star of dashboard 2 (VIEW is enough). It fills at once.
   - Turn on *My favorites*: only dashboard 2 remains. Click its star again: it leaves the
     filtered list without a reload.
   - Open dashboard 1, star it in the dialog header, then close. Its row star is now filled.
   - As `admin`, the star of dashboard 1 is empty (favorites are personal).
8. **Tab-scoped save + discard (FR-011/014/019/024)**: edit a core field and a parameter, save
   on the Parameters tab, then reopen. The parameter changed and the core field did not. Try to
   close with an unsaved edit and you are asked to confirm.

## Cleanup

Logically remove the dashboards created during testing (row action *Remove*) and revoke the test
grants.
