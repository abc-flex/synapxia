/**
 * Dashboards API service — Dashboard Management (`/ana/dashboards`,
 * specs/006-dashboard-management). A new dashboard starts in DRAFT and its
 * creator gets MANAGE; every other write needs MANAGE on the dashboard.
 */
import { apiDelete, apiGet, apiPost, apiPut, buildQueryString } from "./api";
import type {
  Dashboard,
  DashboardCreate,
  DashboardUpdate,
  DashboardWithAccess,
  ListOption,
} from "@/types/api";

const enc = (v: number) => encodeURIComponent(String(v));
const PAGE = 500;
const MAX_ROWS = 10_000;

export async function getDashboardsWithAccess(skip = 0, limit = PAGE): Promise<DashboardWithAccess[]> {
  return apiGet<DashboardWithAccess[]>(`/api/dashboards/with-access${buildQueryString({ skip, limit })}`);
}

/** Every accessible dashboard, page by page — the list table filters
 *  client-side, so it must never stop at the first page. */
export async function getAllDashboardsWithAccess(): Promise<DashboardWithAccess[]> {
  const rows: DashboardWithAccess[] = [];
  for (let skip = 0; skip < MAX_ROWS; skip += PAGE) {
    const page = await getDashboardsWithAccess(skip, PAGE);
    rows.push(...page);
    if (page.length < PAGE) break;
  }
  return rows;
}

export async function getDashboard(id: number): Promise<DashboardWithAccess> {
  return apiGet<DashboardWithAccess>(`/api/dashboards/${enc(id)}`);
}

export async function createDashboard(data: DashboardCreate): Promise<DashboardWithAccess> {
  return apiPost<DashboardWithAccess, DashboardCreate>("/api/dashboards/", data);
}

export async function updateDashboard(id: number, data: DashboardUpdate): Promise<DashboardWithAccess> {
  return apiPut<DashboardWithAccess, DashboardUpdate>(`/api/dashboards/${enc(id)}`, data);
}

/** Logical removal: the record, its parameters and grants are kept. */
export async function deleteDashboard(id: number): Promise<Dashboard> {
  return apiDelete<Dashboard>(`/api/dashboards/${enc(id)}`);
}

/** Mark / clear the caller's favorite (VIEW access suffices; personal, not an edit). */
export async function setDashboardFavorite(
  id: number, on: boolean,
): Promise<{ dashboard: number; is_favorite: boolean }> {
  const route = `/api/dashboards/${enc(id)}/favorite`;
  return on
    ? apiPut<{ dashboard: number; is_favorite: boolean }, Record<string, never>>(route, {})
    : apiDelete<{ dashboard: number; is_favorite: boolean }>(route);
}

/** The LIST_OF_VALUES lists a parameter may take its allowed values from. */
export async function getParameterLists(): Promise<ListOption[]> {
  return apiGet<ListOption[]>("/api/dashboards/parameter-lists");
}
