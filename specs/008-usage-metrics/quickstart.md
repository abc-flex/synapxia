# Quickstart: Usage Metrics (SpecKit 008)

How to prove the feature works end to end. Contracts are in [contracts/usage-api.md](contracts/usage-api.md) and rules in [data-model.md](data-model.md).

## 1. Prerequisites

```bash
make dev                                   # stack up; login admin / Admin123!
docker compose exec -T db psql -U synapxia -d synapxia -v ON_ERROR_STOP=1 \
  < specs/008-usage-metrics/provisioned-db.sql          # indexes (provisioned DBs only)
docker compose exec -T db psql -U synapxia -d synapxia -v ON_ERROR_STOP=1 \
  < specs/008-usage-metrics/synthetic-usage.sql         # ~4,700 synthetic executions (only that table)
```

The load writes **only** to `executions`, over the existing dashboards and users. It prints a status summary: about 84% Success, 11% Cancelled, 2–3% Failed, 2% Unauthorized and 1% Incomplete. There is no Timeout, because no seeded dashboard is an Internal Page.

To remove it later, run `synthetic-usage-remove.sql` the same way. It deletes only the executions marked `"synthetic": true`.

## 2. Automated

```bash
docker compose exec -T api uv run pytest -q          # baseline 747/0 (715 + 32 usage tests)
make test
cd ui && bun run build                              # clean; astro check at its existing baseline
```

## 3. Manual: as `admin` (Administrator, organization-wide)

1. Open the sidebar → Analytics → **Usage Metrics** (`/ana/usage`). The header shows the option name and icon, and the period defaults to **last 30 days**. Top to bottom, the page shows: one compact bar (period presets, custom dates, scope note, filter chip), the headline tiles, then **adoption** (its rows are the page filter) and the chart **side by side** from 1280 px wide (stacked below that), and finally the dashboards table. Tile explanations and the adoption note are in tooltips (hover the tile / the ⓘ).
2. **Headline.** Check the figures against a hand count:
   ```sql
   SELECT count(*) FILTER (WHERE status IS NULL OR status IN ('SUCCESS','FAILED','TIMEOUT')) runs,
          count(*) FILTER (WHERE status IN ('CANCELLED','UNAUTHORIZED')) attempts
     FROM executions
    WHERE executed_at >= (CURRENT_DATE - 29)::timestamp AT TIME ZONE 'America/Bogota';
   ```
   Runs, attempts, users and the success rate must match. Each tile shows a change against the previous 30 days.
3. **Timeline.** Switch to **last 12 months**: about 53 weekly or 12 monthly bars, depending on the bucket rule.
   - Adoption grows over the year.
   - There is a dip around late December to early January.
   - The stacked legend reads Success / Failed / Timeout / Incomplete / Cancelled / Unauthorized in the current language.
   - Hovering or tapping a bar lists its counts.
4. **Dashboards table.**
   - Default sort is by runs: *GenAI Adoption — Development Team*, then *by Team*, then *by Role*.
   - **Show unused** adds nothing with the seeded data: every active Published dashboard has runs, and *Smoke 006* is logically deleted (`is_active = false`).
   - Expand *GenAI Adoption — by Role*: its top errors include "Access to dashboard 2 is not granted." (it is not shared with everyone) and "Popup blocked".
5. **Adoption by unit.** The tree starts at Corporate; Engineering (55 members) and Generative AI (the admin) are the only units with people.
   - Corporate's runs equal Engineering's plus Generative AI's.
   - Click **Engineering**: the chip "Unit: Engineering" appears above the tiles, the row is highlighted, a **Clear filter** button shows in the adoption header, and the tiles, chart and table narrow. Clear it from either place.
6. **Adoption by project.** The seeded DB has no projects, so the tab shows only **No project** (all runs). Create a project in Collaboration → Projects for a team (e.g. ALPHA, no dates) and reload: it appears with the team's members, and selecting it filters the page.
7. **Adoption by team.** Five teams plus **No team** (members without an assignment). Seeded assignments start on the provisioning day, so older runs count in each person's current team. The note says team totals may exceed the overall total. The **No team** row shows a count and no rate. Click a team row: same filter behaviour as units.
8. **Export.** From the dashboards table and from each adoption tab, export CSV and Excel.
   - Both files open in Excel with accents intact.
   - The rows match the visible table, including the active search and the unused toggle.
   - Unit rows carry their full path.
   - The file name carries the period and the filter.
9. **Language and theme.** Switch to Español: every label, status, type and source changes. Switch to dark mode: the chart stays legible and the legend still tells the outcomes apart.
10. **Phone width (390 px).** The tiles wrap, and the tables scroll inside their own box with no page-level horizontal scroll.

## 4. Manual: scope and access

1. **ADMINISTRATIVE.** Log in as `felipe.cardenas`.
   - The scope note says the view is limited to the dashboards he manages.
   - The scope note says 2 dashboards (seeded MANAGE on 1 and 4). Only *GenAI Adoption — Development Team* appears; *Smoke 006* is inactive.
   - The headline equals the hand count restricted to those dashboard ids.
2. **COLLABORATOR.** Log in as `adriana.velez`. The option is not in the sidebar, `/ana/usage` is refused, and `GET /api/usage/metrics?...` answers 403.
3. **Errors outside scope.** As felipe, `GET /api/usage/dashboards/3/errors?...` answers 404.

## 5. Performance (SC-003)

Reload the synthetic data with the `scale` variable (`-v scale=21` multiplies the daily counts) to reach about 100 000 executions. Running the plain script several times does **not** add up, because each load first removes the previous one. Then:

```bash
time curl -s -b cookies.txt "http://localhost:8001/api/usage/metrics?date_from=2025-10-06&date_to=2026-10-05" > /dev/null
```

Expected: under 3 s end to end, with the page showing figures within 3 s. Remove the extra data afterwards with the removal script.
