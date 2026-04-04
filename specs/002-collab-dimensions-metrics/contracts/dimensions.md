# API Contracts: Dimensions & Metrics

**Branch**: `002-collab-dimensions-metrics` | **Date**: 2026-04-03  
**Base URL**: `/api`  
**Auth**: All endpoints require `Authorization: Bearer <JWT>` header.

---

## Dimensions

### `GET /api/dimensions`

List all dimensions with pagination.

**Query Parameters**:
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `skip` | integer | `0` | Records to skip |
| `limit` | integer | `100` | Max records to return |

**Response `200 OK`**:
```json
[
  {
    "code": "CODE_QUALITY",
    "name": "Code Quality",
    "description": "Measures code quality standards",
    "scale": "QUALITY_SCALE",
    "unit": "POINTS",
    "is_active": true,
    "created_at": "2026-04-03T10:00:00Z",
    "updated_at": null
  }
]
```
Ordered by `name` ascending.

---

### `GET /api/dimensions/{dimension_code}`

Get a single dimension by its code.

**Path Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `dimension_code` | string | Unique dimension code |

**Response `200 OK`**: Single `Dimension` object (same schema as list item).  
**Response `404 Not Found`**: `{"detail": "Dimension not found"}`

---

### `POST /api/dimensions/`

Create a new dimension.

**Request Body**:
```json
{
  "code": "CODE_QUALITY",
  "name": "Code Quality",
  "description": "Measures code quality standards",
  "scale": "QUALITY_SCALE",
  "unit": "POINTS",
  "is_active": true
}
```
- `code`: required, max 50 chars, unique
- `name`: required, max 100 chars
- `description`: optional, max 500 chars
- `scale`: optional, must reference existing `lists.code`
- `unit`: optional, max 100 chars

**Response `201 Created`**: Full `Dimension` object.  
**Response `409 Conflict`**: `{"detail": "Dimension with code 'CODE_QUALITY' already exists"}`

---

### `PUT /api/dimensions/{dimension_code}`

Update an existing dimension (partial update — only supplied fields are changed).

**Path Parameters**: `dimension_code` (string)

**Request Body** (all fields optional):
```json
{
  "name": "Code Quality v2",
  "description": "Updated description",
  "scale": "QUALITY_SCALE_V2",
  "unit": "PERCENT",
  "is_active": true
}
```

**Response `200 OK`**: Updated `Dimension` object.  
**Response `404 Not Found`**: `{"detail": "Dimension not found"}`

---

### `DELETE /api/dimensions/{dimension_code}`

Logical delete — sets `is_active = FALSE`.

**Path Parameters**: `dimension_code` (string)

**Response `200 OK`**: Updated `Dimension` object with `is_active: false`.  
**Response `404 Not Found`**: `{"detail": "Dimension not found"}`  
**Response `400 Bad Request`**: `{"detail": "Dimension with code 'CODE_QUALITY' is already inactive"}`

---

## Metrics

### `GET /api/metrics`

List all metrics with pagination.

**Query Parameters**:
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `skip` | integer | `0` | Records to skip |
| `limit` | integer | `100` | Max records to return |

**Response `200 OK`**:
```json
[
  {
    "id": 1,
    "dimension": "CODE_QUALITY",
    "assignment": 42,
    "value": "85",
    "observation": "Strong improvement this sprint",
    "measured_at": "2026-04-03T10:00:00Z",
    "is_active": true,
    "created_at": "2026-04-03T10:00:00Z",
    "updated_at": null
  }
]
```
Ordered by `measured_at` descending.

> **Note**: No `dimension` query parameter is supported. Client-side column filtering via DataTable is used on the metrics page.

---

### `GET /api/metrics/{metric_id}`

Get a single metric by its ID.

**Path Parameters**: `metric_id` (integer)

**Response `200 OK`**: Single `Metric` object.  
**Response `404 Not Found`**: `{"detail": "Metric not found"}`

---

### `POST /api/metrics/`

Create a new metric record.

**Request Body**:
```json
{
  "dimension": "CODE_QUALITY",
  "assignment": 42,
  "value": "85",
  "observation": "Strong improvement this sprint",
  "measured_at": "2026-04-03T10:00:00Z",
  "is_active": true
}
```
- `dimension`: required, must reference existing `dimensions.code`
- `assignment`: required, must reference existing `assignments.id`
- `value`: required, max 100 chars
- `observation`: optional, max 500 chars
- `measured_at`: optional, defaults to server `NOW()`

**Response `201 Created`**: Full `Metric` object.  
**Response `400 Bad Request`**: `{"detail": "Dimension with code 'X' does not exist"}` or `{"detail": "Assignment with id 'Y' does not exist"}`

---

### `PUT /api/metrics/{metric_id}`

Update an existing metric (partial update).

**Path Parameters**: `metric_id` (integer)

**Request Body** (all fields optional):
```json
{
  "value": "90",
  "observation": "Updated observation",
  "measured_at": "2026-04-04T12:00:00Z",
  "is_active": true
}
```
> `dimension` and `assignment` are **not** updatable.

**Response `200 OK`**: Updated `Metric` object.  
**Response `404 Not Found`**: `{"detail": "Metric not found"}`

---

### `DELETE /api/metrics/{metric_id}`

Logical delete — sets `is_active = FALSE`.

**Path Parameters**: `metric_id` (integer)

**Response `200 OK`**: Updated `Metric` object with `is_active: false`.  
**Response `404 Not Found`**: `{"detail": "Metric not found"}`  
**Response `400 Bad Request`**: `{"detail": "Metric with id 'X' is already inactive"}`

---

## UI Consumption Notes

- **Dimensions page** calls `GET /api/dimensions` at SSR time; mutations (POST/PUT/DELETE) via `lib/dimensions.ts` from client scripts.
- **Metrics page** calls `GET /api/metrics`, `GET /api/dimensions`, and `GET /api/assignments` at SSR time. Dimension filtering is client-side using DataTable `columnFilter="dimension"`.
- The `id` field for metrics data rows is set to `item.id` (integer). The `id` field for dimension rows is set to `item.code` (string).
- The detail action on Dimensions links to `/collab/metrics?dimension={code}`.
- The Metrics page reads `Astro.url.searchParams.get("dimension")` to pre-select the column filter.
