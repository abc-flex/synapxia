/**
 * Characterizations API service.
 *
 * Asset × Feature value rows — composite PK `(asset, feature)`. The API
 * routes use the asset id (BIGINT) as the `{code}` path parameter even
 * though the variable name suggests a string code; pass the integer id.
 */

import { apiGet, apiPost, apiPut, apiDelete, buildQueryString } from "./api";
import type {
  Characterization,
  CharacterizationCreate,
  CharacterizationUpdate,
} from "../types/api";

/**
 * Full list of characterizations (paginated). Until the API exposes a
 * `/by-asset/{id}` endpoint we fetch a wide page and filter client-side.
 */
export async function getCharacterizations(
  skip = 0,
  limit = 1000,
): Promise<Characterization[]> {
  return apiGet<Characterization[]>(
    `/api/characterizations/${buildQueryString({ skip, limit })}`,
  );
}

/**
 * Convenience: every characterization for a single asset, sorted by feature.
 * Used by AssetDetailModal to pre-populate the dynamic form in edit mode.
 */
export async function getCharacterizationsByAsset(
  assetId: number,
): Promise<Characterization[]> {
  const all = await getCharacterizations(0, 1000);
  return all
    .filter((c) => Number(c.asset) === Number(assetId))
    .sort((a, b) => a.feature.localeCompare(b.feature));
}

export async function getCharacterization(
  assetId: number | string,
  featureCode: string,
): Promise<Characterization> {
  return apiGet<Characterization>(
    `/api/characterizations/${encodeURIComponent(String(assetId))}/${encodeURIComponent(featureCode)}`,
  );
}

export async function createCharacterization(
  data: CharacterizationCreate,
): Promise<Characterization> {
  return apiPost<Characterization, CharacterizationCreate>(
    "/api/characterizations/",
    data,
  );
}

export async function updateCharacterization(
  assetId: number | string,
  featureCode: string,
  data: CharacterizationUpdate,
): Promise<Characterization> {
  return apiPut<Characterization, CharacterizationUpdate>(
    `/api/characterizations/${encodeURIComponent(String(assetId))}/${encodeURIComponent(featureCode)}`,
    data,
  );
}

export async function deleteCharacterization(
  assetId: number | string,
  featureCode: string,
): Promise<void> {
  return apiDelete<void>(
    `/api/characterizations/${encodeURIComponent(String(assetId))}/${encodeURIComponent(featureCode)}`,
  );
}
