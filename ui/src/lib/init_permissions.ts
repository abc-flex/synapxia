/**
 * Initiative permissions API service (Initiative Management → Permissions tab).
 * Mirrors lib/asset_permissions.ts: a grant is revoked (DELETE sets
 * `valid_to` = now), never deleted.
 */
import { apiDelete, apiGet, apiPost, apiPut, buildQueryString } from "./api";
import type { InitPermission, InitPermissionCreate, InitPermissionUpdate } from "@/types/api";

const enc = (v: number) => encodeURIComponent(String(v));

export async function getInitPermissionsByInit(initId: number, skip = 0, limit = 500): Promise<InitPermission[]> {
  return apiGet<InitPermission[]>(
    `/api/init_permissions/init/${enc(initId)}${buildQueryString({ skip, limit })}`,
  );
}

export async function createInitPermission(data: InitPermissionCreate): Promise<InitPermission> {
  return apiPost<InitPermission, InitPermissionCreate>("/api/init_permissions/", data);
}

export async function updateInitPermission(id: number, data: InitPermissionUpdate): Promise<InitPermission> {
  return apiPut<InitPermission, InitPermissionUpdate>(`/api/init_permissions/${enc(id)}`, data);
}

/** Revoke a grant (the row is kept with `valid_to` closed). */
export async function deleteInitPermission(id: number): Promise<InitPermission> {
  return apiDelete<InitPermission>(`/api/init_permissions/${enc(id)}`);
}
