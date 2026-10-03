/**
 * Dashboard parameters API service (Dashboard Management → Parameters tab).
 * Keyed by (dashboard, name); the name is part of the key and never renamed.
 * Removal is logical, and re-adding a removed name restores it.
 */
import { apiDelete, apiGet, apiPost, apiPut, buildQueryString } from "./api";
import type {
  DashboardParameter,
  DashboardParameterCreate,
  DashboardParameterUpdate,
} from "@/types/api";

const base = (dashboardId: number) => `/api/dashboards/${encodeURIComponent(String(dashboardId))}/parameters`;
const one = (dashboardId: number, name: string) => `${base(dashboardId)}/${encodeURIComponent(name)}`;

export async function getParameters(dashboardId: number, skip = 0, limit = 500): Promise<DashboardParameter[]> {
  return apiGet<DashboardParameter[]>(`${base(dashboardId)}${buildQueryString({ skip, limit })}`);
}

export async function createParameter(
  dashboardId: number, data: DashboardParameterCreate,
): Promise<DashboardParameter> {
  return apiPost<DashboardParameter, DashboardParameterCreate>(base(dashboardId), data);
}

export async function updateParameter(
  dashboardId: number, name: string, data: DashboardParameterUpdate,
): Promise<DashboardParameter> {
  return apiPut<DashboardParameter, DashboardParameterUpdate>(one(dashboardId, name), data);
}

export async function deleteParameter(dashboardId: number, name: string): Promise<DashboardParameter> {
  return apiDelete<DashboardParameter>(one(dashboardId, name));
}
