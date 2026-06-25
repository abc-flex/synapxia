/**
 * Asset relations API service.
 *
 * Composite-PK `(source, target)` rows — both are asset ids. `type` comes
 * from the RELATION_TYPE list; `rationale` is an optional free-text note.
 *
 * Re-add semantics: the API's create pre-check does NOT filter is_active,
 * so POSTing a pair that was logically deleted returns 409. Callers should
 * fall back to `updateAssetRelation(source, target, { ..., is_active: true })`
 * on 409 to reactivate the row.
 */

import { apiGet, apiPost, apiPut, apiDelete, buildQueryString } from "./api";
import type {
  AssetRelation,
  AssetRelationCreate,
  AssetRelationUpdate,
  RelatedAsset,
} from "../types/api";

/** Active relations where the given asset is the source. */
export async function getAssetRelationsBySource(
  assetId: number,
  skip = 0,
  limit = 100,
): Promise<AssetRelation[]> {
  return apiGet<AssetRelation[]>(
    `/api/asset_relations/source/${encodeURIComponent(String(assetId))}${buildQueryString({ skip, limit })}`,
  );
}

/** Active relations where the given asset is the target (reverse lookup). */
export async function getAssetRelationsByTarget(
  assetId: number,
  skip = 0,
  limit = 100,
): Promise<AssetRelation[]> {
  return apiGet<AssetRelation[]>(
    `/api/asset_relations/target/${encodeURIComponent(String(assetId))}${buildQueryString({ skip, limit })}`,
  );
}

/**
 * Resolved related assets in both directions, de-duplicated by the other asset
 * id (outgoing wins), inactive/missing assets excluded. One call backs the
 * read-only "Related" section on the gallery detail modal (HU-LI07).
 */
export async function getRelatedAssets(
  assetId: number,
  skip = 0,
  limit = 100,
): Promise<RelatedAsset[]> {
  return apiGet<RelatedAsset[]>(
    `/api/asset_relations/related/${encodeURIComponent(String(assetId))}${buildQueryString({ skip, limit })}`,
  );
}

export async function getAssetRelation(
  sourceId: number,
  targetId: number,
): Promise<AssetRelation> {
  return apiGet<AssetRelation>(
    `/api/asset_relations/${encodeURIComponent(String(sourceId))}/${encodeURIComponent(String(targetId))}`,
  );
}

export async function createAssetRelation(
  data: AssetRelationCreate,
): Promise<AssetRelation> {
  return apiPost<AssetRelation, AssetRelationCreate>(
    "/api/asset_relations/",
    data,
  );
}

export async function updateAssetRelation(
  sourceId: number,
  targetId: number,
  data: AssetRelationUpdate,
): Promise<AssetRelation> {
  return apiPut<AssetRelation, AssetRelationUpdate>(
    `/api/asset_relations/${encodeURIComponent(String(sourceId))}/${encodeURIComponent(String(targetId))}`,
    data,
  );
}

export async function deleteAssetRelation(
  sourceId: number,
  targetId: number,
): Promise<AssetRelation> {
  return apiDelete<AssetRelation>(
    `/api/asset_relations/${encodeURIComponent(String(sourceId))}/${encodeURIComponent(String(targetId))}`,
  );
}
