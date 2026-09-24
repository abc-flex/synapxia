/**
 * Asset relations API service.
 *
 * Composite-PK `(source, target, type)` rows — both ends are asset ids; the
 * same pair may be related once per relation type. `type` comes
 * from the RELATION_TYPE list; `rationale` is an optional free-text note.
 *
 * Re-add semantics: POSTing an identical (source, target, type) link that was
 * logically deleted reactivates it (201); an active identical link → 409.
 * Address a single link with the `…Typed` functions at the bottom — the
 * pair-addressed ones only work while the pair has one link.
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

// ── One link by (source, target, type) ──────────────────────────────────────
// The same pair may be related once per relation type (PK source, target,
// type). These address a single link exactly; the pair-addressed functions
// above only work while the pair has one link (the API answers 409 otherwise).

const relPath = (sourceId: number, targetId: number, type: string) =>
  `/api/asset_relations/${encodeURIComponent(String(sourceId))}/${encodeURIComponent(String(targetId))}/${encodeURIComponent(type)}`;

/** Update one link's rationale / active flag (its type is part of the key). */
export async function updateAssetRelationTyped(
  sourceId: number,
  targetId: number,
  type: string,
  data: Omit<AssetRelationUpdate, "type">,
): Promise<AssetRelation> {
  return apiPut<AssetRelation, Omit<AssetRelationUpdate, "type">>(relPath(sourceId, targetId, type), data);
}

/** Logically delete one link (that relation type only). */
export async function deleteAssetRelationTyped(
  sourceId: number,
  targetId: number,
  type: string,
): Promise<AssetRelation> {
  return apiDelete<AssetRelation>(relPath(sourceId, targetId, type));
}
