/**
 * Asset permissions API service.
 *
 * Surrogate-id rows: a target (USER/ROLE/TEAM/UNIT/PROJECT/PUBLIC) is granted
 * an access level (VIEW/MANAGE) on an asset. `target_code` is the target
 * entity's id/code ("PUBLIC" when target_type=PUBLIC). Logical delete via
 * is_active=False.
 */

import { apiGet, apiPost, apiPut, apiDelete, buildQueryString } from "./api";
import type {
  AssetPermission,
  AssetPermissionCreate,
  AssetPermissionUpdate,
} from "../types/api";

/** Active permissions for one asset. */
export async function getAssetPermissionsByAsset(
  assetId: number,
  skip = 0,
  limit = 100,
): Promise<AssetPermission[]> {
  return apiGet<AssetPermission[]>(
    `/api/asset_permissions/asset/${encodeURIComponent(String(assetId))}${buildQueryString({ skip, limit })}`,
  );
}

export async function getAssetPermission(id: number): Promise<AssetPermission> {
  return apiGet<AssetPermission>(
    `/api/asset_permissions/${encodeURIComponent(String(id))}`,
  );
}

export async function createAssetPermission(
  data: AssetPermissionCreate,
): Promise<AssetPermission> {
  return apiPost<AssetPermission, AssetPermissionCreate>(
    "/api/asset_permissions/",
    data,
  );
}

export async function updateAssetPermission(
  id: number,
  data: AssetPermissionUpdate,
): Promise<AssetPermission> {
  return apiPut<AssetPermission, AssetPermissionUpdate>(
    `/api/asset_permissions/${encodeURIComponent(String(id))}`,
    data,
  );
}

export async function deleteAssetPermission(id: number): Promise<AssetPermission> {
  return apiDelete<AssetPermission>(
    `/api/asset_permissions/${encodeURIComponent(String(id))}`,
  );
}
