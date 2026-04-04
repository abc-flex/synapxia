# Data Model: Collab Projects CRUD with Team Filter

**Branch**: `001-collab-projects` | **Phase**: 1 | **Date**: 2026-03-25

## Entities

### Project

Core entity representing a work initiative within the Collaboration module.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `code` | `str` | PK, max 50, unique | User-defined unique identifier (validated on create) |
| `name` | `str` | max 100, required | Human-readable project name |
| `description` | `str?` | max 500, optional | Extended project description |
| `team` | `str?` | FK → `teams.code`, optional | Owning team; null = unassigned project |
| `status` | `str` | max 100, required | FK-like value from `PROJECT_STATUS` list items |
| `repo_url` | `str?` | max 500, optional | Git/VCS repository URL |
| `start_date` | `date?` | optional | Project start date |
| `end_date` | `date?` | optional | Planned or actual end date |
| `is_active` | `bool` | default=True | Logical delete flag |
| `created_at` | `datetime` | auto, server-set | Record creation timestamp |
| `updated_at` | `datetime?` | nullable, server-set on update | Last update timestamp |

**Table**: `projects` (already exists)  
**Primary Key**: `code`  
**Foreign Keys**: `team` → `teams.code`

#### Validation Rules
- `code` must be unique across all projects (checked on create, 409 on collision)
- `status` must be one of: `PLANNED`, `IN_PROGRESS`, `ON_HOLD`, `COMPLETED`
- `team` if provided, must reference an existing active team (checked server-side, 400 on miss)
- `end_date` if provided alongside `start_date`, should be ≥ `start_date` (UI-level validation preferred)
- Logical delete sets `is_active=False`; records are retained in DB

#### State Transitions (status field)
```
PLANNED → IN_PROGRESS → COMPLETED
                ↓
             ON_HOLD → IN_PROGRESS
```
All transitions are user-driven via the edit form. No automatic transitions.

---

### Team (existing — referenced, not modified)

| Field | Type | Notes |
|-------|------|-------|
| `code` | `str` | PK - used as FK in projects |
| `name` | `str` | Display name in filter dropdown and table column |
| `is_active` | `bool` | Filter to active teams only for dropdown |

**Used for**: The team filter dropdown on the projects page fetches active teams (`is_active=True`) from `GET /api/teams/`.

---

### ProjectStatus (list items — read-only reference)

Sourced from the `PROJECT_STATUS` list in the `list_items` table. Fetched via `GET /api/list_items/list/PROJECT_STATUS`.

| Value | Label |
|-------|-------|
| `PLANNED` | Planned |
| `IN_PROGRESS` | In Progress |
| `ON_HOLD` | On Hold |
| `COMPLETED` | Completed |

---

## Relationships

```
Team (1) ─────────── (0..*) Project
                              │
ProjectStatus (ref) ──────── status field
```

A `Team` has zero or many `Projects`. A `Project` belongs to zero or one `Team`. Project status is a constrained string sourced from a reference list.

---

## API Data Shapes

### Request Schemas

#### ProjectCreate
```json
{
  "code": "BE-001",
  "name": "Backend Refactor",
  "description": "Refactor the authentication layer",
  "team": "BACKEND",
  "status": "PLANNED",
  "repo_url": "https://github.com/org/repo",
  "start_date": "2026-04-01",
  "end_date": "2026-06-30",
  "is_active": true
}
```
- `code`, `name`, `status` are **required**
- All other fields are optional

#### ProjectUpdate (PATCH-style, unset fields excluded)
```json
{
  "name": "Backend Auth Refactor",
  "status": "IN_PROGRESS",
  "end_date": "2026-07-15"
}
```
- All fields optional; only included fields are updated
- `updated_at` is set server-side

### Response Schema

#### Project
```json
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
```

---

## UI Field Mapping

### Projects Table Columns

| Column Key | Source Field | Label i18n Key |
|-----------|--------------|----------------|
| `code` | `project.code` | `project_modal.code` |
| `name` | `project.name` | `project_modal.name` |
| `team` | `project.team` | `project_modal.team` |
| `status` | `project.status` | `project_modal.status` |
| `start_date` | `project.start_date` | `project_modal.start_date` |
| `end_date` | `project.end_date` | `project_modal.end_date` |

### Create/Edit Form Fields

| Field Key | Type | Required | Source/Options |
|-----------|------|----------|----------------|
| `code` | `text` | Yes (PK, create only) | User input |
| `name` | `text` | Yes | User input |
| `description` | `textarea` | No | User input |
| `team` | `select` | No | `getTeams()` → `{ code, name }` |
| `status` | `select` | Yes | `getListItemsbyList("PROJECT_STATUS")` → `{ value, label }` |
| `repo_url` | `text` | No | User input |
| `start_date` | `date` (text) | No | User input |
| `end_date` | `date` (text) | No | User input |

---

## TypeScript Interfaces (to add to `ui/src/types/api.ts`)

```typescript
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
