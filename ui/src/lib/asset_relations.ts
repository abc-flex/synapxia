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
