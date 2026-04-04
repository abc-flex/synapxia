# Implementation Plan: Collab Projects CRUD with Team Filter

**Branch**: `001-collab-projects` | **Date**: 2026-03-25 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/001-collab-projects/spec.md`

## Summary

Implement the Projects CRUD page within the Collaboration module, mirroring the admin/options page pattern but filtering by team instead of module. The backend projects API already exists with full CRUD endpoints; this feature extends the list endpoint (add `is_active` filter, optional `team` query param, and correct ordering), then builds the missing UI layer: TypeScript types, a service library, and an Astro page with DataTable + CrudModal. A master-detail link is added to the teams page so users can navigate directly to a team's projects.

## Technical Context

**Language/Version**: Python ≥3.12 (backend), TypeScript / Astro 4 (frontend)  
**Primary Dependencies**: FastAPI + SQLModel (backend), Astro + Bun + TailwindCSS (frontend)  
**Storage**: PostgreSQL — `projects` table already exists, no migration needed  
**Testing**: `make test` (API health smoke test); manual UI verification per quickstart  
**Target Platform**: Linux container (Docker Compose) — API port 8000, UI port 4321  
**Project Type**: Web service (REST API) + SSR web application  
**Performance Goals**: Projects list loads in < 3 s (≤ 200 records); CRUD feedback < 2 s  
**Constraints**: Pagination (skip/limit, default limit 100); team filter applied server-side via optional query param  
**Scale/Scope**: Single new UI page; one backend endpoint modification; 6 file changes total

## Constitution Check

*GATE: Pre-design review — all principles evaluated. Re-checked post-design below.*

- [x] **Principle I — Modular Monolith Boundaries**: All backend changes stay within `api/app/collab/routes/projects.py`. No new domain module created. Cross-domain dependencies (session, auth) reused from `api/app/internal`. UI changes stay within `ui/src/pages/collab/` and `ui/src/lib/`. ✅ Passes.

- [x] **Principle II — API-First Contract Stability**: `GET /api/projects/` extension adds optional `team` query param (additive). Behavioral changes (`is_active` filter + ordering) affect only the list endpoint; no existing UI consumer of the list endpoint exists today. New UI types added to `api.ts` without removing existing keys. ✅ Passes — no breaking changes.

- [x] **Principle III — Risk-Based Testing Discipline**: Risk class = **medium** (backend endpoint behavioral change + new UI page). Required: (1) run `make test` after backend change to confirm health check passes; (2) manual UI smoke test per quickstart for all 5 user stories; (3) verify 409 conflict on duplicate project code via API docs or curl. No automated integration tests required by constitution for this risk class. ✅ Defined and proportional.

- [x] **Principle IV — Security and Secret Hygiene**: All `/api/projects` endpoints already covered by JWT Bearer middleware (SPR-001 confirmed). No new roles, no new secrets, no CORS changes. Team validation server-side on create/update prevents FK violations. ✅ Passes.

- [x] **Principle V — Performance and Operability Baselines**: `list_projects` query uses `WHERE is_active=true` (indexed bool), optional `WHERE team=?` (FK column), and `ORDER BY team, name` — bounded by `limit` param (default 100, max configurable). No N+1 risk. Service remains runnable via `make up`. Health check path unaffected. ✅ Passes.

**Post-design re-check**: Constitution check maintained after Phase 1 design. The data model introduces zero new entities and zero schema migrations. All contracts are additive extensions of existing endpoints. No violations found.

## Project Structure

### Documentation (this feature)

```text
specs/001-collab-projects/
├── plan.md           # This file
├── research.md       # Phase 0 research findings
├── data-model.md     # Phase 1 entity design
├── quickstart.md     # Phase 1 quick start guide
├── contracts/
│   └── projects.md   # Phase 1 API contract
└── tasks.md          # Phase 2 output (created by /speckit.tasks — not yet)
```

### Source Code (repository root)

```text
api/
└── app/
    └── collab/
        └── routes/
            └── projects.py          # MODIFY: extend list_projects()

ui/
└── src/
    ├── types/
    │   └── api.ts                   # MODIFY: add Project, ProjectCreate, ProjectUpdate
    ├── lib/
    │   └── projects.ts              # CREATE: projects CRUD service
    ├── pages/
    │   └── collab/
    │       ├── projects.astro       # CREATE: projects CRUD page
    │       └── teams.astro          # MODIFY: add detailPage prop
    └── i18n/
        ├── en.json                  # MODIFY: add project_modal section
        └── es.json                  # MODIFY: add project_modal section (Spanish)
```

**Structure Decision**: Web application (Option 2 pattern). Backend under `api/`, frontend under `ui/`. No new directories required — all changes fit within existing module boundaries.

## Changes Detail

### 1. Backend — `api/app/collab/routes/projects.py`

**Change**: Replace the `list_projects` function signature and query.

```python
# Before
def list_projects(skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session)):
    projects = session.exec(select(Project).offset(skip).limit(limit).order_by(Project.name)).all()
    return projects

# After
from typing import Optional

def list_projects(
    skip: int = 0,
    limit: int = 100,
    team: Optional[str] = None,
    session: Session = Depends(get_db_session)
) -> List[Project]:
    query = select(Project).where(Project.is_active == True)
    if team:
        query = query.where(Project.team == team)
    query = query.order_by(Project.team, Project.name).offset(skip).limit(limit)
    return session.exec(query).all()
```

**Import addition**: `from typing import Optional` (already imported at top of file).

---

### 2. UI Types — `ui/src/types/api.ts`

**Change**: Append three new interfaces at the end of the file.

```typescript
// Project types
export interface Project {
  code: string;
  name: string;
  description?: string;
  team?: string;
  status: string;
  repo_url?: string;
  start_date?: string;
  end_date?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface ProjectCreate {
  code: string;
  name: string;
  description?: string;
  team?: string;
  status: string;
  repo_url?: string;
  start_date?: string;
  end_date?: string;
  is_active?: boolean;
}

export interface ProjectUpdate {
  name?: string;
  description?: string;
  team?: string;
  status?: string;
  repo_url?: string;
  start_date?: string;
  end_date?: string;
  is_active?: boolean;
}
```

---

### 3. UI Service — `ui/src/lib/projects.ts` (new file)

New service file mirroring `teams.ts` structure, with optional `team` filter on `getProjects`.

```typescript
import { apiGet, apiPost, apiPut, apiDelete, buildQueryString } from './api';
import type { Project, ProjectCreate, ProjectUpdate } from '../types/api';

export async function getProjects(team?: string, skip = 0, limit = 100): Promise<Project[]> {
  const params: Record<string, any> = { skip, limit };
  if (team) params.team = team;
  return apiGet<Project[]>(`/api/projects${buildQueryString(params)}`);
}

export async function getProject(code: string): Promise<Project> {
  return apiGet<Project>(`/api/projects/${encodeURIComponent(code)}`);
}

export async function createProject(data: ProjectCreate): Promise<Project> {
  return apiPost<Project, ProjectCreate>('/api/projects/', data);
}

export async function updateProject(code: string, data: ProjectUpdate): Promise<Project> {
  return apiPut<Project, ProjectUpdate>(`/api/projects/${encodeURIComponent(code)}`, data);
}

export async function deleteProject(code: string): Promise<Project> {
  return apiDelete<Project>(`/api/projects/${encodeURIComponent(code)}`);
}
```

---

### 4. UI Page — `ui/src/pages/collab/projects.astro` (new file)

New page mirroring `admin/options.astro` with these substitutions:

| Options page | Projects page |
|---|---|
| `getOptions()` | `getProjects()` |
| `getModules()` source for filter | `getTeams()` source for filter |
| `columnFilter="module"` | `columnFilter="team"` |
| module select field | team select field |
| status column absent | `status`, `start_date`, `end_date` columns |
| `i18Item="option"` | `i18Item="project"` |
| No status dropdown | Status dropdown from `getListItemsbyList("PROJECT_STATUS")` |

**URL param handling**: Read `Astro.url.searchParams.get("team")` at build time to populate a `data-initial-filter` attribute that a client-side script applies to the filter `<select>` on page load.

**Breadcrumb**: `Collaboration → Projects` using keys `modules.COLLAB` / `menu_options.projects`.

---

### 5. Teams Page — `ui/src/pages/collab/teams.astro`

**Change**: Add `detailPage`, `mdItem`, and pass `i18Item="team"` explicitly to `DataTable`.

```astro
<DataTable
  columns={columns}
  data={data}
  tableId="teams-datatable"
  i18Item="team"
  columnFilter={null}
  filterOptions={[]}
  detailPage="/collab/projects"
  mdItem="project"
/>
```

This generates detail links: `/collab/projects?team={team.code}`.

---

### 6. i18n — `en.json` and `es.json`

**Add** to both files a `project_modal` section parallel to `team_modal`:

```json
"project_modal": {
  "one_title": "Project",
  "many_title": "Projects",
  "add_new": "New Project",
  "edit": "Edit Project",
  "delete": "Delete Project",
  "empty_message": "No Projects found",
  "delete_confirmation": "Are you sure you want to delete this Project",
  "filter_title": "Filter by Team",
  "code": "Code",
  "name": "Name",
  "description": "Description",
  "team": "Team",
  "status": "Status",
  "repo_url": "Repository URL",
  "start_date": "Start Date",
  "end_date": "End Date"
}
```

Spanish equivalents in `es.json` (translated accordingly).

## Complexity Tracking

> No constitution violations. No complexity exceptions required.

## Artifacts Generated

| Artifact | Path | Status |
|----------|------|--------|
| Research | `specs/001-collab-projects/research.md` | ✅ Complete |
| Data Model | `specs/001-collab-projects/data-model.md` | ✅ Complete |
| API Contract | `specs/001-collab-projects/contracts/projects.md` | ✅ Complete |
| Quickstart | `specs/001-collab-projects/quickstart.md` | ✅ Complete |
| Task list | `specs/001-collab-projects/tasks.md` | ⏳ Run `/speckit.tasks` |
