/**
 * Asset-initiative relations API service (Asset Management's "Related Inits"
 * tab). Composite-PK `(asset, init, type)` rows — the same pair may be linked
 * once per relation type. Mirrors asset_relations.ts, pointed at initiatives
 * instead of another asset. `type` comes from the same RELATION_TYPE list;
 * `rationale` is an optional free-text note.
 *
 * Re-add semantics: POSTing an identical (asset, init, type) link that was
 * logically deleted reactivates it (201); an active identical link → 409.
 * Address a single link with the `…Typed` functions at the bottom.
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

// ── One link by (asset, init, type) ─────────────────────────────────────────
// The same pair may be linked once per relation type (PK asset, init, type).
// The pair-addressed functions above only work while the pair has one link.

const linkPath = (assetId: number, initId: number, type: string) =>
  `/api/asset_inits/${encodeURIComponent(String(assetId))}/${encodeURIComponent(String(initId))}/${encodeURIComponent(type)}`;

/** Update one link's rationale / active flag (its type is part of the key). */
export async function updateAssetInitTyped(
  assetId: number,
  initId: number,
  type: string,
  data: Omit<AssetInitUpdate, "type">,
): Promise<AssetInit> {
  return apiPut<AssetInit, Omit<AssetInitUpdate, "type">>(linkPath(assetId, initId, type), data);
}

/** Logically delete one link (that relation type only). */
export async function deleteAssetInitTyped(
  assetId: number,
  initId: number,
  type: string,
): Promise<AssetInit> {
  return apiDelete<AssetInit>(linkPath(assetId, initId, type));
}
