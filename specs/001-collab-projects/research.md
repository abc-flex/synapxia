# Research: Collab Projects CRUD with Team Filter

**Branch**: `001-collab-projects` | **Phase**: 0 | **Date**: 2026-03-25

## Summary

All unknowns resolved through direct codebase inspection. No external sources needed.

---

## Finding 1: Backend — list_projects endpoint gaps

**Question**: Does `GET /api/projects/` already support team filtering, active-only filtering, and correct ordering?

**Answer**: No. The current implementation is:

```python
@router.get("/", response_model=List[Project])
def list_projects(skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session)):
    projects = session.exec(select(Project).offset(skip).limit(limit).order_by(Project.name)).all()
    return projects
```

**Gaps identified**:
1. No `is_active=True` filter — returns all projects including deactivated ones
2. No `team` query parameter — server-side team filtering not supported
3. Ordering is by name only — spec requires order by team then name

**Decision**: Extend `GET /api/projects/` to add:
- `is_active=True` filter (always applied)
- Optional `team: Optional[str] = None` query param
- `order_by(Project.team, Project.name)`

**Rationale**: Additive-only change; no breaking impact on existing consumers (the current UI has no projects page). Consistent with how `GET /api/options/` works in the admin module.

**Alternatives considered**: Client-side filtering (rejected: the spec allows server-side when param is available; server-side is more performant and follows the same approach as options/modules).

---

## Finding 2: Frontend — Projects service and types do not exist

**Question**: Do `ui/src/lib/projects.ts` and Project types in `ui/src/types/api.ts` already exist?

**Answer**: No. The file `ui/src/lib/projects.ts` does not exist. The `ui/src/types/api.ts` file has no Project, ProjectCreate, or ProjectUpdate interfaces.

**Decision**: Create:
- `ui/src/types/api.ts` additions: `Project`, `ProjectCreate`, `ProjectUpdate`
- `ui/src/lib/projects.ts`: full CRUD service mirroring `ui/src/lib/teams.ts` structure

**Rationale**: Consistent with existing library pattern. The teams lib is the direct model (simple CRUD, typed imports from `../types/api.ts` or domain-specific type file).

---

## Finding 3: Frontend — projects.astro page does not exist

**Question**: Does `ui/src/pages/collab/projects.astro` already exist?

**Answer**: No. Only `teams.astro` and `assignments.astro` exist under `ui/src/pages/collab/`.

**Decision**: Create `ui/src/pages/collab/projects.astro` mirroring `admin/options.astro` exactly, substituting:
- Module filter → Team filter
- Options data → Projects data
- `getModules()` source → `getTeams()` source
- `PROJECT_STATUS` list items → status dropdown options (via `getListItemsbyList("PROJECT_STATUS")`)

**Pattern confirmed**: `admin/options.astro` uses `DataTable` with:
- `columnFilter="module"` → will become `columnFilter="team"`
- `filterOptions={modules}` → will become `filterOptions={teams}`
- Three `CrudModal` instances (create, edit, delete)
- `crud-submit` event handler calling lib functions

---

## Finding 4: Team filter URL parameter pre-population

**Question**: How does master-detail navigation from teams page pass the team code to the projects page?

**Answer**: The `DataTable` component generates detail links as:

```
{detailPage}?{i18Item}={row.id}
```

For teams page with `detailPage="/collab/projects"` and `i18Item="team"`, clicking a row with `id = team.code` navigates to:
`/collab/projects?team=TEAM_CODE`

**Decision**: 
- Add `detailPage="/collab/projects"` and `mdItem="project"` to `DataTable` in `teams.astro`
- On `projects.astro`, read `Astro.url.searchParams.get("team")` at build time to pass as initial filter value to the DataTable via `data-initial-filter` attribute (or via the DataTable's JavaScript initialization)
- The DataTable's existing column filter will be pre-selected via client-side JS reading a `data-initial-value` attribute on the filter `<select>`

**Rationale**: This pattern does not require changes to the DataTable Astro component — only the JS initialization in projects.astro needs to read the URL param and apply it to the column filter select.

---

## Finding 5: Project Status options source

**Question**: How to populate the status dropdown in the create/edit modal?

**Answer**: The existing `getListItemsbyList("PROJECT_STATUS")` function in `ui/src/lib/list_items.ts` fetches items from `/api/list_items/list/PROJECT_STATUS`. The project status values (PLANNED, IN_PROGRESS, ON_HOLD, COMPLETED) are seeded in the DB.

**Decision**: Call `getListItemsbyList("PROJECT_STATUS")` at page load time in `projects.astro`, map results to `{ code, name }` for the CrudModal select field `options` array.

**Rationale**: Fully consistent with how options/modules pattern works. No hardcoding of status values.

---

## Finding 6: i18n keys

**Question**: What i18n keys need to be added?

**Answer**: Inspection of `en.json` confirms:
- `menu_options.projects` = "Projects" ✓ (already exists)
- `modules.COLLAB` = "Collaboration" ✓ (already exists)
- `team_modal.*` section exists ✓
- **Missing**: `project_modal.*` section (add_new, edit, delete, empty_message, delete_confirmation, one_title, many_title)
- **Missing**: `project_modal` field labels: code, name, description, team, status, repo_url, start_date, end_date
- **Missing**: `team_modal.filter_title` key (used by DataTable for filter placeholder)

**Decision**: Add `project_modal` section to both `en.json` and `es.json`.

---

## Finding 7: Backend router registration

**Question**: Is the projects router already registered in `main.py`?

**Answer**: Yes. Line already exists:
```python
from .collab.routes import projects as projects_router
```
And the router is included in the app. **No changes to main.py needed.**

---

## Finding 8: Authentication coverage

**Question**: Does the JWT auth middleware already cover `/api/projects`?

**Answer**: Per spec (SPR-001) and the existing architecture, the centralized auth middleware covers all `/api/*` routes. The `projects_router` uses `get_db_session` from the centralized internal dependencies — same pattern as teams, options. **No auth changes needed.**

---

## Finding 9: Database schema

**Question**: Does the `projects` table exist with all needed columns?

**Answer**: Yes. The `ProjectBase` SQLModel and `Project` table are fully defined in `api/app/collab/internal/models.py` with all required fields. The `db/sql/2-collab-ddl.sql` or equivalent creates the table. **No migration needed.**

---

## Resolved Unknowns

| Unknown | Status | Resolution |
|---------|--------|------------|
| Backend list endpoint gaps | ✅ Resolved | Extend with is_active, team, ordering |
| UI types exist? | ✅ Resolved | Add to api.ts |
| UI service exists? | ✅ Resolved | Create projects.ts |
| UI page exists? | ✅ Resolved | Create projects.astro |
| Status options source | ✅ Resolved | getListItemsbyList("PROJECT_STATUS") |
| Team filter URL pre-population | ✅ Resolved | Read searchParams in .astro, set via JS |
| i18n keys needed | ✅ Resolved | Add project_modal section to en/es.json |
| Router registered? | ✅ Resolved | Already registered in main.py |
| Auth coverage? | ✅ Resolved | Already covered by middleware |
| DB schema? | ✅ Resolved | Table exists, no migration needed |
