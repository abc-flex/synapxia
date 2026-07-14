# API Contracts: Collab Projects

**Branch**: `001-collab-projects` | **Phase**: 1 | **Date**: 2026-03-25  
**Base URL**: `/api/projects`  
**Auth**: All endpoints require `Authorization: Bearer <JWT>` header

---

## Endpoints

### GET /api/projects/

List all active projects with optional team filter and pagination.

**⚠ Backend change required**: Add `is_active`, `team`, and ordering to current implementation.

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip` | `int` | `0` | Records to skip (pagination) |
| `limit` | `int` | `100` | Max records to return |
| `team` | `str?` | `null` | Filter by team code (exact match) |

#### Response `200 OK`
```json
[
  {
    "code": "BE-001",
    "name": "Backend Auth Refactor",
    "description": "Refactor the authentication layer",
    "team": "BACKEND",
    "status": "IN_PROGRESS",
    "repo_url": "https://github.com/org/repo",
    "start_date": "2026-04-01",
    "end_date": "2026-07-15",
    "is_active": true,
    "created_at": "2026-04-01T10:00:00",
    "updated_at": "2026-04-15T09:30:00"
  }
]
```

**Ordering**: `team ASC NULLS LAST, name ASC`  
**Filter applied**: `is_active = true` (always). `team = {team}` (when provided).

#### Current vs Extended Implementation

```python
# CURRENT (to be replaced)
def list_projects(skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session)):
    projects = session.exec(select(Project).offset(skip).limit(limit).order_by(Project.name)).all()
    return projects

# EXTENDED (target implementation)
def list_projects(skip: int = 0, limit: int = 100, team: Optional[str] = None, session: Session = Depends(get_db_session)):
    query = select(Project).where(Project.is_active == True)
    if team:
        query = query.where(Project.team == team)
    query = query.order_by(Project.team, Project.name).offset(skip).limit(limit)
    return session.exec(query).all()
```

---

### POST /api/projects/

Create a new project.

**No change required** — existing implementation is correct.

#### Request Body
```json
{
  "code": "BE-001",
  "name": "Backend Auth Refactor",
  "description": "Refactor the authentication layer",
  "team": "BACKEND",
  "status": "PLANNED",
  "repo_url": "https://github.com/org/repo",
  "start_date": "2026-04-01",
  "end_date": "2026-06-30"
}
```

#### Response `201 Created` — returns full `Project` object

#### Error Cases

| Status | Condition |
|--------|-----------|
| `409 Conflict` | Project code already exists |
| `400 Bad Request` | Provided `team` code does not exist |
| `422 Unprocessable Entity` | Missing required fields (`code`, `name`, `status`) |

---

### GET /api/projects/{project_code}

Get a single project by code.

**No change required** — existing implementation is correct.

#### Response `200 OK` — returns full `Project` object  
#### Response `404 Not Found` — project code does not exist

---

### PUT /api/projects/{project_code}

Update an existing project. Partial update (only provided fields are changed).

**No change required** — existing implementation is correct.

#### Request Body (all fields optional)
```json
{
  "name": "Updated Name",
  "status": "IN_PROGRESS",
  "team": "FRONTEND",
  "end_date": "2026-08-01"
}
```

#### Response `200 OK` — returns updated `Project` object

#### Error Cases

| Status | Condition |
|--------|-----------|
| `404 Not Found` | Project code does not exist |
| `400 Bad Request` | Provided `team` code does not exist |

---

### DELETE /api/projects/{project_code}

Logical delete — sets `is_active=False`.

**No change required** — existing implementation is correct.

#### Response `200 OK` — returns the deactivated `Project` object

#### Error Cases

| Status | Condition |
|--------|-----------|
| `404 Not Found` | Project code does not exist |
| `400 Bad Request` | Project is already inactive |

---

## Backward Compatibility

| Change | Impact | Assessment |
|--------|--------|------------|
| Add `team` query param to `GET /api/projects/` | Additive; existing calls without `team` param continue to work | ✅ Safe |
| Add `is_active=True` filter to `GET /api/projects/` | Previously returned inactive projects; now filters them out | ⚠ Behavioral change — no existing UI consumer, risk is minimal |
| Add ordering by (team, name) | Previously ordered by name only | ⚠ Behavioral change — no existing UI consumer, risk is minimal |

**Assessment**: All three changes are safe for this feature since there is currently no UI page consuming the projects list endpoint.

---

## UI Service Contract (`ui/src/lib/projects.ts`)

```typescript
getProjects(team?: string, skip?: number, limit?: number): Promise<Project[]>
getProject(code: string): Promise<Project>
createProject(data: ProjectCreate): Promise<Project>
updateProject(code: string, data: ProjectUpdate): Promise<Project>
deleteProject(code: string): Promise<Project>
```
