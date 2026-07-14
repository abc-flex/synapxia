/**
 * Assets API Service
 * Handles all API calls related to assets
 */

import { apiGet, apiPost, apiPut, apiDelete, buildQueryString } from './api';
import type { Asset, AssetCreate, AssetUpdate, AssetVersionRequest, AssetWithAccessLevels, ChangeType } from '../types/api';

/**
 * Client-side mirror of the backend's `version_service.bump_label` — used for
 * the live "v1.2.0 → v1.3.0" preview in the edit modal. Display-only: the
 * server recomputes the label authoritatively on save. Malformed or missing
 * labels are treated as the 1.0.0 base, matching the backend.
 */
export function bumpVersionLabel(label: string | undefined | null, changeType: ChangeType): string {
  const match = /^(\d+)\.(\d+)\.(\d+)$/.exec((label ?? '').trim());
  const [major, minor, patch] = match
    ? [Number(match[1]), Number(match[2]), Number(match[3])]
    : [1, 0, 0];
  if (changeType === 'major') return `${major + 1}.0.0`;
  if (changeType === 'minor') return `${major}.${minor + 1}.0`;
  return `${major}.${minor}.${patch + 1}`;
}

/**
 * Fetch all assets with optional pagination
 * @param skip - Number of records to skip (default: 0)
 * @param limit - Maximum number of records to return (default: 100)
 * @returns Promise with array of assets
 */
export async function getAssets(skip: number = 0, limit: number = 100): Promise<Asset[]> {
  const queryString = buildQueryString({ skip, limit });
  return apiGet<Asset[]>(`/api/assets/${queryString}`);
}

/**
 * Fetch all assets with an aggregated per-asset access summary
 * (access_levels + is_public), used to drive the access-level table filter.
 */
export async function getAssetsWithAccess(skip: number = 0, limit: number = 100): Promise<AssetWithAccessLevels[]> {
  const queryString = buildQueryString({ skip, limit });
  return apiGet<AssetWithAccessLevels[]>(`/api/assets/with-access${queryString}`);
}

export interface AssetSelectOption {
  value: string; // asset id as string
  label: string; // asset name
}

/**
 * Lightweight {value,label} list of active assets for UI dropdowns
 * (e.g. picking a related asset in the asset modal).
 */
export async function getAssetsSelect(): Promise<AssetSelectOption[]> {
  return apiGet<AssetSelectOption[]>('/api/assets/select');
}

/**
 * Fetch all assets by category with optional pagination
 * @param list_code - category code
 * @param skip - Number of records to skip (default: 0)
 * @param limit - Maximum number of records to return (default: 100)
 * @returns Promise with array of assets
 */
export async function getAssetsbyCategory(category_code: string, skip: number = 0, limit: number = 100): Promise<Asset[]> {
  const queryString = buildQueryString({ skip, limit });
  return apiGet<Asset[]>(`/api/assets/category/${category_code}${queryString}`);
}

/**
 * Fetch a single asset by its id
 * @param id - Unique asset id
 * @returns Promise with asset data
 */
export async function getAsset(id: number): Promise<Asset> {
  return apiGet<Asset>(`/api/assets/${encodeURIComponent(id)}`);
}

/**
 * Create a new asset
 * @param data - Asset data to create
 * @returns Promise with created asset
 */
export async function createAsset(data: AssetCreate): Promise<Asset> {
  return apiPost<Asset, AssetCreate>('/api/assets/', data);
}

/**
 * Update an existing asset
 * @param id - Asset id to update
 * @param data - Asset data to update
 * @returns Promise with updated asset
 */
export async function updateAsset(id: number, data: AssetUpdate): Promise<Asset> {
  return apiPut<Asset, AssetUpdate>(`/api/assets/${encodeURIComponent(id)}`, data);
}

/**
 * Save edits to an existing asset as a NEW VERSION (HU-LI09). One transaction
 * server-side: bumps `current_version` by `change_type`, applies the core
 * edits, snapshots the characterizations under the new version label and logs
 * a VERSIONING action. Leave `values` undefined for a core-only save.
 * @param id - Asset id to version
 * @param data - Change type + edited fields (+ optional full characterization set)
 * @returns Promise with the updated asset (carrying the new current_version)
 */
export async function createAssetVersion(id: number, data: AssetVersionRequest): Promise<Asset> {
  return apiPost<Asset, AssetVersionRequest>(`/api/assets/${encodeURIComponent(id)}/versions`, data);
}

/**
 * Delete a asset by its id
 * @param id - Asset id to delete
 * @returns Promise with void
 */
export async function deleteAsset(id: number): Promise<void> {
  return apiDelete<void>(`/api/assets/${encodeURIComponent(id)}`);
}

