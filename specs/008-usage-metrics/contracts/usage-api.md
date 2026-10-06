# Contract: Usage Metrics API (SpecKit 008)

All responses use the standard envelope `{ data, error, meta }`, and the UI unwraps `.data` in `lib/api.ts`. Auth is a JWT cookie or Bearer token.

**Common gate.** `require_privilege("ANA", "USAGE")` at read level. No token gets 401; without the privilege the answer is 403. The scope is then resolved inside the route (research R4).

**Common query parameters.**

| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `date_from` | `YYYY-MM-DD` | yes | Local date (`APP_TIMEZONE`), inclusive |
| `date_to` | `YYYY-MM-DD` | yes | Inclusive; at most 24 months after `date_from` |
| `unit` | string | no | Business-unit code; includes descendants. Mutually exclusive with `team` |
| `team` | string | no | Team code, or `__none__` for "No team". Mutually exclusive with `unit` |
| `project` | string | no | Project code, or `__none__` for "No project". Only one of `unit`, `team`, `project` (400 otherwise) |

---

## `GET /api/usage/metrics`

Returns one aggregate document for the period. No individual execution, `user_id` or payload ever appears in it.

**200**

```jsonc
{
  "period": {
    "date_from": "2026-09-06", "date_to": "2026-10-05",
    "previous_from": "2026-08-07", "previous_to": "2026-09-05",
    "bucket": "day",                       // day | week | month
    "timezone": "America/Bogota"
  },
  "scope": { "restricted": false, "dashboards": null },   // restricted=true → dashboards = count in scope
  "filter": { "unit": null, "team": null },
  "summary": {
    "current":  { "runs": 812, "attempts": 94, "users": 97, "dashboards": 11,
                  "success_rate": 0.951, "median_ms": 1240, "avg_ms": 2190, "incomplete": 10,
                  "outcomes": { "SUCCESS": 760, "FAILED": 22, "TIMEOUT": 9, "INCOMPLETE": 10,
                                "CANCELLED": 85, "UNAUTHORIZED": 9 } },
    "previous": { "...same shape..." },
    "change":   { "runs": 0.12, "attempts": -0.05, "users": 0.08, "dashboards": 0.0,
                  "success_rate": 0.011, "median_ms": -35, "avg_ms": 40, "incomplete": null }
                  // ratios for counts; plain differences for rate (points) and durations (ms);
                  // null when previous is 0 or undefined
  },
  "timeline": [
    { "start": "2026-09-06", "end": "2026-09-06",
      "outcomes": { "SUCCESS": 3, "FAILED": 0, "TIMEOUT": 0, "INCOMPLETE": 0,
                    "CANCELLED": 1, "UNAUTHORIZED": 0 } }
    // one entry per bucket, empty buckets included, oldest first
  ],
  "dashboards": [
    { "id": 1, "name": "GenAI Adoption — Development Team", "type": "DASHBOARD",
      "source": "POWER_BI", "status": "PUBLISHED",
      "runs": 160, "attempts": 12, "users": 41, "success_rate": 0.97,
      "median_ms": 980, "last_run_at": "2026-10-05T19:22:10Z", "unused": false }
    // used rows first (runs desc), then unused rows (unused=true, zero figures, last_run_at null)
  ],
  "units": [
    { "code": "CORP", "name": "Corporate", "members": 116, "direct_members": 0,
      "runs": 812, "users": 97, "success_rate": 0.951, "adoption_rate": 0.836,
      "children": [ { "code": "ENG", "...": "...", "children": [] } ] }
  ],
  "projects": [
    { "code": "P1", "name": "Apollo", "team": "ALPHA", "team_name": "Alpha", "members": 9,
      "runs": 120, "users": 7, "success_rate": 0.96, "adoption_rate": 0.778 },
    { "code": "__none__", "name": null, "team": null, "team_name": null, "members": null,
      "runs": 300, "users": 40, "success_rate": 0.97, "adoption_rate": null }
  ],
  "teams": [
    { "code": "ALPHA", "name": "Alpha", "members": 9, "runs": 140, "users": 8,
      "success_rate": 0.95, "adoption_rate": 0.889 },
    { "code": "__none__", "name": null, "members": null, "runs": 210, "users": 30,
      "success_rate": 0.94, "adoption_rate": null }
  ]
}
```

**Notes**
- `dashboards` is bounded by the dashboards in scope, and `units` and `teams` by the organization's structure. None of them is an execution list (Constitution II: no unbounded list of records).
- `units` and `teams` are **not** narrowed by `unit` / `team` (data-model "Group filter").
- Labels for `type`, `source`, `status` and outcome keys are codes. The UI translates them from `list_items`. The team display name for `__none__` is i18n.

**Errors**: 400 (validation, see data-model), 401, 403.

---

## `GET /api/usage/dashboards/{dashboard_id}/errors`

The most frequent error messages of one dashboard in the period, across all outcomes that carry one.

**Extra query**: `limit` (int, 1–50, default 10).

**200**

```jsonc
{
  "dashboard": 6,
  "items": [
    { "message": "Popup blocked", "count": 14, "statuses": ["FAILED"] },
    { "message": "Did not load within 30 s", "count": 6, "statuses": ["TIMEOUT"] }
  ],
  "total_with_error": 23   // records with a non-empty error_message in the period (before limit)
}
```

- Ordered by `count` desc, then `message` asc. Messages are returned as stored (capped at 1 000 characters by SpecKit 007).
- The `unit` / `team` filter applies, so the list matches the narrowed table.

**Errors**: 400 (validation), 401, 403, **404** when the dashboard does not exist or is outside the caller's scope. The response is the same in both cases, so it does not reveal whether the dashboard exists.

---

## Not provided

- No create, update or delete operation (FR-003).
- No server-side export. CSV and Excel files are generated in the browser from the `metrics` document (research R11).
