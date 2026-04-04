# Quickstart: Collab Dimensions CRUD with Metrics Master-Detail

**Branch**: `002-collab-dimensions-metrics` | **Date**: 2026-04-03

## Prerequisites

- Docker and Docker Compose installed
- Project running via `make up` (API on port 8000, UI on port 4321)
- A valid user account with COLLAB/DIMENSIONS privilege to obtain a JWT token

## Running the Feature (Local Dev)

```bash
# Start all services
make up

# Verify API is up
curl http://localhost:8000/api/health

# Verify dimensions endpoint
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/dimensions/

# Verify metrics endpoint
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/metrics/
```

Navigate to `http://localhost:4321/collab/dimensions` to access the Dimensions page.  
Navigate to `http://localhost:4321/collab/metrics` to access the Metrics page directly.

## Testing the Feature

### 1. Backend endpoints (manual)

```bash
# List active dimensions
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/dimensions/

# Create a dimension
curl -X POST http://localhost:8000/api/dimensions/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"code":"CODE_QUALITY","name":"Code Quality","unit":"POINTS"}'

# Update a dimension
curl -X PUT http://localhost:8000/api/dimensions/CODE_QUALITY \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Code Quality Score"}'

# Delete (logical) a dimension
curl -X DELETE http://localhost:8000/api/dimensions/CODE_QUALITY \
  -H "Authorization: Bearer <token>"

# List all metrics
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/metrics/

# Create a metric
curl -X POST http://localhost:8000/api/metrics/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"dimension":"CODE_QUALITY","assignment":1,"value":"85","observation":"Good sprint"}'

# Update a metric
curl -X PUT http://localhost:8000/api/metrics/1 \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"value":"90","observation":"Updated observation"}'

# Delete (logical) a metric
curl -X DELETE http://localhost:8000/api/metrics/1 \
  -H "Authorization: Bearer <token>"
```

### 2. UI smoke test — Dimensions page (manual)

1. Log in and navigate to **Collaboration → Dimensions**
2. Verify the table shows active dimensions with columns: code, name, scale, unit — ordered by name
3. Click **+ Dimension** → fill code and name → submit; verify the new dimension appears
4. Click the edit icon → change the name → submit; verify the change reflects in the table
5. Click the delete icon → confirm → verify the dimension disappears from the active list
6. Click the detail icon on a dimension row → verify navigation to `/collab/metrics?dimension=<code>` with the filter pre-applied

### 3. UI smoke test — Metrics page (manual)

1. Navigate to **Collaboration → Metrics** (or via the Dimensions detail link)
2. Verify the table shows active metrics with columns: dimension, assignment, value, measured_at
3. If arrived via dimension detail link, verify the dimension filter is pre-selected
4. Select a dimension from the filter dropdown; verify only that dimension's metrics appear
5. Click **+ Metric** → fill dimension, assignment, value → submit; verify the new metric appears
6. Click the edit icon on a metric → change the value → submit; verify the change
7. Click the delete icon → confirm → verify the metric disappears from the active list
8. Click the back link → verify navigation returns to the Dimensions page

### 4. Master-detail navigation test

Navigate to `/collab/metrics?dimension=CODE_QUALITY` directly in the browser. Verify:
- The filter dropdown is pre-selected to `CODE_QUALITY`
- Only metrics for that dimension are shown
- Clearing the filter shows all metrics
- The back link points to `/collab/dimensions`

## Files Changed by This Feature

### Frontend (UI) — new files
- `ui/src/lib/dimensions.ts` — dimensions CRUD service
- `ui/src/lib/metrics.ts` — metrics CRUD service
- `ui/src/pages/collab/dimensions.astro` — dimensions master page
- `ui/src/pages/collab/metrics.astro` — metrics detail page

### Frontend (UI) — modified files
- `ui/src/types/api.ts` — add `Dimension`, `DimensionCreate`, `DimensionUpdate`, `Metric`, `MetricCreate`, `MetricUpdate` interfaces
- `ui/src/i18n/en.json` — add `menu_options.metrics`, `dimension_modal.*`, `metric_modal.*` keys
- `ui/src/i18n/es.json` — same keys in Spanish

### Backend — no changes required
All `/api/dimensions` and `/api/metrics` routes and models are already implemented.
