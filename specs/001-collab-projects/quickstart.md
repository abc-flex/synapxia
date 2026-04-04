# Quickstart: Collab Projects CRUD with Team Filter

**Branch**: `001-collab-projects` | **Date**: 2026-03-25

## Prerequisites

- Docker and Docker Compose installed
- Project running via `make up` (API on port 8000, UI on port 4321)
- A valid user account to obtain a JWT token

## Running the Feature (Local Dev)

```bash
# Start all services
make up

# Verify API is up
curl http://localhost:8000/api/health

# Verify projects endpoint
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/projects/
```

Navigate to `http://localhost:4321/collab/projects` to access the Projects page.

## Testing the Feature

### 1. Backend endpoint (manual)

```bash
# List active projects
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/projects/

# List projects filtered by team
curl -H "Authorization: Bearer <token>" "http://localhost:8000/api/projects/?team=BACKEND"

# Create a project
curl -X POST http://localhost:8000/api/projects/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"code":"TEST-001","name":"Test Project","status":"PLANNED"}'

# Update a project
curl -X PUT http://localhost:8000/api/projects/TEST-001 \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"status":"IN_PROGRESS"}'

# Delete (logical) a project
curl -X DELETE http://localhost:8000/api/projects/TEST-001 \
  -H "Authorization: Bearer <token>"
```

### 2. UI smoke test (manual)

1. Log in and navigate to **Collaboration → Projects**
2. Verify the table shows active projects ordered by team then name
3. Select a team from the filter dropdown; verify only that team's projects appear
4. Click **+ Project** → fill required fields → submit; verify project appears
5. Click the edit icon → change the name → submit; verify the change
6. Click the delete icon → confirm; verify the project disappears from the list
7. Navigate to **Collaboration → Teams** → click the detail icon on any team → verify redirect to Projects page with team pre-filtered

### 3. Master-detail navigation test

Navigate to `/collab/projects?team=<team_code>` directly in the browser. Verify:
- The filter dropdown is pre-selected to the matching team
- Only that team's projects are shown in the table
- Clearing the filter shows all projects

## Files Changed by This Feature

### Backend
- `api/app/collab/routes/projects.py` — extend `list_projects()` with `is_active`, `team`, ordering

### Frontend (UI)
- `ui/src/types/api.ts` — add `Project`, `ProjectCreate`, `ProjectUpdate` interfaces
- `ui/src/lib/projects.ts` — new file: projects CRUD service
- `ui/src/pages/collab/projects.astro` — new file: projects page
- `ui/src/pages/collab/teams.astro` — add `detailPage` prop to DataTable
- `ui/src/i18n/en.json` — add `project_modal` section
- `ui/src/i18n/es.json` — add `project_modal` section (Spanish translations)

## Smoke Test Gate

Run `make test` to confirm API health checks pass after backend changes. No automated UI tests exist; manual verification per "UI smoke test" above is required.
