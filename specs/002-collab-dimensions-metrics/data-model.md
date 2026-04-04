# Data Model: Collab Dimensions CRUD with Metrics Master-Detail

**Branch**: `002-collab-dimensions-metrics` | **Date**: 2026-04-03

## Entities

### Dimension

**Purpose**: A measurement axis used to evaluate assignments within a team. Defines what is being measured (e.g., "Code Quality", "Collaboration Score").

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `code` | VARCHAR(50) | PK, NOT NULL | Unique identifier chosen by the user (e.g., `CODE_QUALITY`) |
| `name` | VARCHAR(100) | NOT NULL | Human-readable name (e.g., "Code Quality") |
| `description` | VARCHAR(500) | nullable | Optional description of the dimension |
| `scale` | VARCHAR(100) | FK → `lists.code`, nullable | Reference to the list that defines the rating scale |
| `unit` | VARCHAR(100) | nullable | Unit label sourced from `DIMENSIONS_UNIT` list items |
| `is_active` | BOOLEAN | NOT NULL, default TRUE | Logical delete flag |
| `created_at` | TIMESTAMPTZ | NOT NULL, default NOW() | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | nullable | Last update timestamp |

**Validation rules**:
- `code` is immutable after creation (read-only in edit modal)
- `code` must be unique; duplicate insert returns HTTP 409
- `name` is required (max 100 chars)
- `scale` must reference an existing `lists.code` if provided
- Deletion is logical: sets `is_active = FALSE`; already-inactive records raise HTTP 400

**State transitions**:
```
ACTIVE (is_active=TRUE)  ──delete──►  INACTIVE (is_active=FALSE)
```
No reactivation flow is exposed in the current UI.

---

### Metric

**Purpose**: A single measurement event recorded for a specific assignment along a given dimension. Tracks measurement values over time.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | BIGINT | PK, auto-generated (IDENTITY), NOT NULL | Surrogate key |
| `dimension` | VARCHAR(50) | FK → `dimensions.code`, NOT NULL | Which dimension is being measured |
| `assignment` | BIGINT | FK → `assignments.id`, NOT NULL | Which assignment (team-user-role pair) is measured |
| `value` | VARCHAR(100) | NOT NULL | Measurement value (free text or from list) |
| `observation` | VARCHAR(500) | nullable | Free-text notes about this measurement |
| `measured_at` | TIMESTAMPTZ | NOT NULL, default NOW() | When the measurement was recorded |
| `is_active` | BOOLEAN | NOT NULL, default TRUE | Logical delete flag |
| `created_at` | TIMESTAMPTZ | NOT NULL, default NOW() | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | nullable | Last update timestamp |

**Validation rules**:
- `dimension` must reference an active `dimensions.code` (validated at create time)
- `assignment` must reference an existing `assignments.id` (validated at create time)
- `value` is required (max 100 chars)
- `measured_at` defaults to `NOW()` if not provided at creation
- Editable fields: `value`, `observation`, `measured_at`, `is_active`
- `dimension` and `assignment` are immutable after creation (not included in `MetricUpdate`)
- Deletion is logical: sets `is_active = FALSE`; already-inactive records raise HTTP 400

---

## Relationships

```
lists ──(scale FK)──► dimensions ──(dimension FK)──► metrics
                                                          │
assignments ──────────────────────(assignment FK)─────────┘
```

- One **Dimension** has zero-to-many **Metrics**
- One **Assignment** has zero-to-many **Metrics**
- One **List** (scale) describes the measurement scale for zero-to-many **Dimensions**
- **Metrics** are the intersection of a Dimension and an Assignment at a point in time

---

## API DTOs

### DimensionCreate
```python
code: str              # required, max 50
name: str              # required, max 100
description: str       # optional, max 500
scale: str             # optional, max 50
unit: str              # optional, max 100
is_active: bool        # optional, default True
```

### DimensionUpdate
```python
name: str              # optional, max 100
description: str       # optional, max 500
scale: str             # optional, max 50
unit: str              # optional, max 100
is_active: bool        # optional
```

### MetricCreate
```python
dimension: str         # required, FK dimensions.code
assignment: int        # required, FK assignments.id
value: str             # required, max 100
observation: str       # optional, max 500
measured_at: datetime  # optional, defaults to NOW()
is_active: bool        # optional, default True
```

### MetricUpdate
```python
value: str             # optional, max 100
observation: str       # optional, max 500
measured_at: datetime  # optional
is_active: bool        # optional
```

---

## UI Type Interfaces (TypeScript — to add to `ui/src/types/api.ts`)

```typescript
// Dimension types
export interface Dimension {
  code: string;
  name: string;
  description?: string;
  scale?: string;
  unit?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface DimensionCreate {
  code: string;
  name: string;
  description?: string;
  scale?: string;
  unit?: string;
  is_active?: boolean;
}

export interface DimensionUpdate {
  name?: string;
  description?: string;
  scale?: string;
  unit?: string;
  is_active?: boolean;
}

// Metric types
export interface Metric {
  id: number;
  dimension: string;
  assignment: number;
  value: string;
  observation?: string;
  measured_at: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface MetricCreate {
  dimension: string;
  assignment: number;
  value: string;
  observation?: string;
  measured_at?: string;
  is_active?: boolean;
}

export interface MetricUpdate {
  value?: string;
  observation?: string;
  measured_at?: string;
  is_active?: boolean;
}
```
