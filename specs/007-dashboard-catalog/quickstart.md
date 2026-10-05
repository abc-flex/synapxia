# Quickstart: Dashboard Catalog (with Execute and Favorite)

**Feature**: `007-dashboard-catalog` · Contract: [contracts/catalog-api.md](contracts/catalog-api.md) · Model: [data-model.md](data-model.md)

## Prerequisites

```bash
make dev                      # stack up; login admin / Admin123!
docker compose exec -T db psql -U postgres -d synapxia -f - < specs/007-dashboard-catalog/test-catalog.sql
```

Fresh volumes pick up the rewritten seed payloads automatically. A provisioned DB keeps the old flat payloads, which is harmless because readers tolerate them (R5).

Test accounts (seed): `adriana.velez` (COLLABORATOR, role TL, `ANA/CATALOG` read-only), `santiago.marin` (REVIEWER), `felipe.cardenas` (ADMINISTRATIVE, also holds Dashboard Management), `admin` (superuser). The seed passwords are the ones used by the earlier quickstarts.

## Automated checks

```bash
docker compose exec -T api uv run pytest -q                       # suite stays green; new tests in test_ana_catalog*.py
docker compose exec -T api uv run pytest -q tests/test_ana_catalog.py tests/test_ana_executions.py
cd ui && bun run build && bunx astro check                        # build clean; astro check at its existing baseline
make test
```

## Manual verification (UI — no Playwright in this repo)

Run as **adriana.velez** unless stated.

### A. Catalog (US1, SC-001)

1. Open **Analytics → Dashboard Catalog**. Header shows the option's name and icon; search box, "★ My favorites", privileges filter; a **card grid**.
2. Privileges filter has exactly **Public, Shared with me, My role, My team, My unit, My projects**, defaults to Public, no "all".
3. **Public** shows dashboards 1, 3 and "Catalog Test — Internal Page". **My role** shows 1 and 2 (ROLE TL grants). "Catalog Test — Draft" never appears under any option.
4. Search `informe` and `report` both find the Internal Page test (type Report) in either language. `looker` finds dashboard 3.
5. Switch language: chips and list values relabel without reload.
6. Click a card body: the detail shows description, the rendered detail text and the parameters table. Clicking the star or Execute does **not** open the detail.
7. Phone width (~390 px): no horizontal scroll in the grid, the detail or the parameters window.

### B. Favorites (US4, SC-005, SC-006)

1. Star dashboard 3, then turn on "★ My favorites": it is listed. Unstar it with the toggle on: it disappears without a reload.
2. As **felipe.cardenas**, open `/ana/dashboards`: a favorite he set in the catalog shows starred there, and vice versa.

### C. Execute — external, grant-bound (US2, US3)

1. On dashboard 2 press **Execute**. The window shows From/To date prefilled, Granularity prefilled, and **Role = TL, read-only**.
2. Clear "From date" and press Execute: inline error, no tab opens, no request is sent.
3. Fill it in and Execute: a new tab opens at the Power BI URL with `?…&date_from=…&role=TL…`, and the window closes.
4. DB check: `SELECT status, payload, duration_ms FROM executions ORDER BY id DESC LIMIT 1;` → `SUCCESS`, `sources.role = "GRANT"`, unchanged defaults marked `DEFAULT`.
5. As **santiago.marin** on dashboard 2: **Role** is a free text field (he reached it through his USER grant, not the bound one).
6. Tamper check (API): `POST /api/dashboards/2/executions` as adriana with `{"values":{"role":"FRONT", …}}` → `launch_url` still has `role=TL`.

### D. Execute — Internal Page viewer (US2-11, US3-5/6)

1. On "Catalog Test — Internal Page" press Execute. Language is a selector (LANGUAGE list, labels in the current language), Top N is required and empty, Only mine offers "not set / yes / no".
2. Execute with Top N empty: inline error. Enter `10` and Execute: the **viewer** opens over the catalog with the name, the values used, an "open full page" link and the `/support` page **without sidebar/header** (`embed=1`). Last row: `SUCCESS` with a duration.
3. Execute again and close the viewer immediately: last row `CANCELLED`.
4. Timeout: in DevTools throttle the network to "offline" after the start request (or block `/support`), Execute, and wait 30 s. The viewer shows "did not respond" with the link, and the last row is `TIMEOUT`.

### E. Cancelled window, last values, popup block

1. Open the parameters window and close it without executing: a `CANCELLED` row with the window's values.
2. Re-open dashboard 2: fields start at the defaults, and **Use my last values** fills From date with the value used in C.3. Role stays TL.
3. Block popups for the site and Execute dashboard 3: a message with a manual link appears, and the last row is `FAILED` "popup blocked".

### F. Access (US3-3, SC-005)

1. As **admin**, archive "Catalog Test — Internal Page" while adriana has its window open. Adriana presses Execute → message, and the last row is `UNAUTHORIZED`.
2. A user without `ANA/CATALOG` gets 403 on `GET /api/dashboards/catalog`.

**Known parity caveat** (R9): a superuser only sees, under each privilege option, the dashboards whose grants actually match them (same as Explore Category / Explore Initiatives).
