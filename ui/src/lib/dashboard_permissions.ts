/**
 * Dashboard permissions API service (Dashboard Management → Permissions tab).
 * Mirrors lib/init_permissions.ts: a grant is revoked (DELETE sets
 * `valid_to` = now), never deleted.
 */
import { apiDelete, apiGet, apiPost, apiPut, buildQueryString } from "./api";
import type {
  DashboardPermission,
  DashboardPermissionCreate,
  DashboardPermissionUpdate,
  RevokedDashboardPermission,
} from "@/types/api";

const enc = (v: number) => encodeURIComponent(String(v));

export async function getDashboardPermissions(
  dashboardId: number, skip = 0, limit = 500,
): Promise<DashboardPermission[]> {
  return apiGet<DashboardPermission[]>(
    `/api/dashboard_permissions/dashboard/${enc(dashboardId)}${buildQueryString({ skip, limit })}`,
  );
}

export async function createDashboardPermission(data: DashboardPermissionCreate): Promise<DashboardPermission> {
  return apiPost<DashboardPermission, DashboardPermissionCreate>("/api/dashboard_permissions/", data);
}

export async function updateDashboardPermission(
  id: number, data: DashboardPermissionUpdate,
): Promise<DashboardPermission> {
  return apiPut<DashboardPermission, DashboardPermissionUpdate>(`/api/dashboard_permissions/${enc(id)}`, data);
}

/** Revoke a grant (kept with `valid_to` closed). Also reports the parameters
 *  still bound to it — their binding stops applying. */
export async function revokeDashboardPermission(id: number): Promise<RevokedDashboardPermission> {
  return apiDelete<RevokedDashboardPermission>(`/api/dashboard_permissions/${enc(id)}`);
}
