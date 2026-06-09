/**
 * Assets API Service
 * Handles all API calls related to assets
 */

import { apiGet, apiPost, apiPut, apiDelete, buildQueryString } from './api';
import type { Asset, AssetCreate, AssetUpdate } from '../types/api';

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
 * Delete a asset by its id
 * @param id - Asset id to delete
 * @returns Promise with void
 */
export async function deleteAsset(id: number): Promise<void> {
  return apiDelete<void>(`/api/assets/${encodeURIComponent(id)}`);
}

