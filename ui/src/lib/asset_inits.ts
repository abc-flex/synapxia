/**
 * Asset-initiative relations API service (Asset Management's "Related Inits"
 * tab). Composite-PK `(asset, init)` rows — mirrors asset_relations.ts, just
 * pointed at initiatives instead of another asset. `type` comes from the
 * same RELATION_TYPE list; `rationale` is an optional free-text note.
 *
 * Re-add semantics: the API's create pre-check does NOT filter is_active, so
 * POSTing a pair that was logically deleted returns 409. Callers should fall
 * back to `updateAssetInit(asset, init, { ..., is_active: true })` on 409 to
 * reactivate the row.
 */

import { apiGet, apiPost, apiPut, apiDelete, buildQueryString } from "./api";
import type { AssetInit, AssetInitCreate, AssetInitUpdate } from "../types/api";

/** Active initiative relations for the given asset. */
export async function getAssetInitsByAsset(
  assetId: number,
  skip = 0,
  limit = 100,
): Promise<AssetInit[]> {
  return apiGet<AssetInit[]>(
    `/api/asset_inits/asset/${encodeURIComponent(String(assetId))}${buildQueryString({ skip, limit })}`,
  );
}

export async function getAssetInit(
  assetId: number,
  initId: number,
): Promise<AssetInit> {
  return apiGet<AssetInit>(
    `/api/asset_inits/${encodeURIComponent(String(assetId))}/${encodeURIComponent(String(initId))}`,
  );
}

export async function createAssetInit(
  data: AssetInitCreate,
): Promise<AssetInit> {
  return apiPost<AssetInit, AssetInitCreate>("/api/asset_inits/", data);
}

export async function updateAssetInit(
  assetId: number,
  initId: number,
  data: AssetInitUpdate,
): Promise<AssetInit> {
  return apiPut<AssetInit, AssetInitUpdate>(
    `/api/asset_inits/${encodeURIComponent(String(assetId))}/${encodeURIComponent(String(initId))}`,
    data,
  );
}

export async function deleteAssetInit(
  assetId: number,
  initId: number,
): Promise<AssetInit> {
  return apiDelete<AssetInit>(
    `/api/asset_inits/${encodeURIComponent(String(assetId))}/${encodeURIComponent(String(initId))}`,
  );
}
