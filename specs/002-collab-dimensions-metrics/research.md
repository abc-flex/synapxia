# Research: Collab Dimensions CRUD with Metrics Master-Detail

**Branch**: `002-collab-dimensions-metrics` | **Date**: 2026-04-03

## Research Questions & Resolutions

### RQ-1: Does the backend API for dimensions and metrics already exist?

**Decision**: Yes — both `/api/dimensions` and `/api/metrics` are fully implemented.  
**Rationale**: `api/app/collab/routes/dimensions.py` and `api/app/collab/routes/metrics.py` exist with full CRUD (POST, GET list, GET by id, PUT, DELETE/logical). Models (`Dimension`, `DimensionCreate`, `DimensionUpdate`, `Metric`, `MetricCreate`, `MetricUpdate`) are in `api/app/collab/internal/models.py`.  
**Alternatives considered**: N/A — backend is already complete.

---

### RQ-2: Does the metrics list endpoint support server-side dimension filtering?

**Decision**: No — `/api/metrics` does not accept a `dimension` query parameter. Client-side DataTable column filtering will be used, consistent with the existing pattern in `admin/options.astro` (module filter) and `collab/assignments.astro` (team filter).  
**Rationale**: The metrics list route only accepts `skip` and `limit`. Adding a `dimension` query param would be a backend change, which falls out of scope for this feature (UI-only). The DataTable `columnFilter` prop handles this fully client-side with no backend change required.  
**Alternatives considered**: Extending the backend metrics endpoint was evaluated but rejected because (a) ~1 000 records comfortably fits the client-side filter, and (b) it avoids scope creep.

---

### RQ-3: What UI lib and type files need to be created?

**Decision**: Create `ui/src/lib/dimensions.ts` and `ui/src/lib/metrics.ts`; extend `ui/src/types/api.ts` with `Dimension`, `DimensionCreate`, `DimensionUpdate`, `Metric`, `MetricCreate`, `MetricUpdate` interfaces.  
**Rationale**: `lib/dimensions.ts` and `lib/metrics.ts` do not exist. `api.ts` has no Dimension or Metric types. All other collab entities follow the same pattern (`lib/teams.ts`, `lib/projects.ts`, `lib/assignments.ts` + types in `api.ts`).  
**Alternatives considered**: Using inline `any` types was rejected — existing pages use typed interfaces consistently.

---

### RQ-4: How does the master-detail navigation pattern work (Roles → Privileges mapped to Dimensions → Metrics)?

**Decision**: The Dimensions page will render a detail-link action on each row using `detailPage="/collab/metrics"`. The Metrics page accepts a `?dimension=CODE` query parameter and pre-populates the `columnFilter` prop. The Metrics page renders a `masterPage="/collab/dimensions"` back-link.  
**Rationale**: This is the exact pattern used by `admin/roles.astro` → `admin/privileges.astro` and `collab/teams.astro` → `collab/assignments.astro`. The DataTable component's `columnFilter` + `filterOptions` props handle the filtering; the query param is read from `Astro.url.searchParams` at SSR time.  
**Alternatives considered**: A separate nested route was rejected since flat page routing with query params is the established convention throughout the app.

---

### RQ-5: How is the `value` field in a Metric populated (dropdown options)?

**Decision**: The `value` field will be a free-text input in the initial implementation. The dimension's `scale` field references a list code, but dynamically fetching list items per selected dimension requires client-side state management not present in the current CrudModal component.  
**Rationale**: The CrudModal `fields` array is defined at SSR time and is static. The select options cannot change dynamically based on another field's value without custom JavaScript. Using a text input is safe and correct — the `value` column is `VARCHAR(100)` with no DB-level enum constraint.  
**Alternatives considered**: Pre-loading all list items and filtering client-side was evaluated but adds complexity out of scope for this story. A future enhancement can add dynamic option loading to CrudModal.

---

### RQ-6: What i18n keys are missing?

**Decision**: Add `"metrics": "Metrics"` to `menu_options` in both `en.json` and `es.json`. Add `dimension_modal.*` and `metric_modal.*` key groups for form field labels, following the pattern (`role_modal.*`, `privilege_modal.*`, `team_modal.*`).  
**Rationale**: `"dimensions": "Dimensions"` already exists in `menu_options`. `"metrics"` is absent. The modal field keys are referenced in the Astro page `tableFields` arrays; missing keys fall back to raw strings but should be properly translated.  
**Alternatives considered**: Inline strings were rejected — all existing pages use i18n keys consistently.

---

### RQ-7: What select options does the Metrics create/edit form need?

**Decision**: Three selects are needed:
1. **dimension** — populated from `getDimensions()` (active dimensions via `/api/dimensions`)
2. **assignment** — populated from `getAssignments()` (active assignments via `/api/assignments`)
3. **value** — free-text input (see RQ-5)

**Rationale**: Dimension and assignment are foreign keys with server-validated references. Both have existing lib functions. The assignments select should display a label combining user and team for readability; this will be derived from the `assignment` records at SSR time.  
**Alternatives considered**: A separate `/api/assignments/select` endpoint was considered but `getAssignments()` already returns sufficient data.

---

## Summary of Decisions

| Question | Resolution |
|----------|-----------|
| Backend API complete? | ✅ Yes — no backend changes needed |
| Metrics dimension filter | Client-side via DataTable `columnFilter` |
| New UI lib files | `dimensions.ts`, `metrics.ts` — to create |
| New UI type interfaces | Dimension/Metric in `api.ts` — to extend |
| Master-detail pattern | `detailPage` + `?dimension=CODE` query param + `masterPage` back-link |
| Metric value field | Free-text input (VARCHAR, no enum constraint) |
| Missing i18n keys | `menu_options.metrics` + `dimension_modal.*` + `metric_modal.*` groups |
| Metrics form selects | `dimension` (from getDimensions) + `assignment` (from getAssignments) |
