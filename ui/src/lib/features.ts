/**
 * Features API Service
 * Handles all API calls related to features
 */

import { apiGet, apiPost, apiPut, apiDelete, buildQueryString } from './api';
import type { Feature, FeatureCreate, FeatureUpdate } from '../types/api';

/**
 * Fetch all features with optional pagination
 * @param skip - Number of records to skip (default: 0)
 * @param limit - Maximum number of records to return (default: 100)
 * @returns Promise with array of features
 */
export async function getFeatures(skip: number = 0, limit: number = 100): Promise<Feature[]> {
  const queryString = buildQueryString({ skip, limit });
  return apiGet<Feature[]>(`/api/features${queryString}`);
}

/**
 * Fetch a single feature by its code
 * @param code - Unique feature code
 * @returns Promise with feature data
 */
export async function getFeature(code: string): Promise<Feature> {
  return apiGet<Feature>(`/api/features/${encodeURIComponent(code)}`);
}

/**
 * Create a new business unit
 * @param data - Business unit data to create
 * @returns Promise with created business unit
 */
export async function createFeature(data: FeatureCreate): Promise<Feature> {
  return apiPost<Feature, FeatureCreate>('/api/features/', data);
}

/**
 * Update an existing business unit
 * @param code - Business unit code to update
 * @param data - Business unit data to update
 * @returns Promise with updated business unit
 */
export async function updateFeature(code: string, data: FeatureUpdate): Promise<Feature> {
  return apiPut<Feature, FeatureUpdate>(`/api/features/${encodeURIComponent(code)}`, data);
}

/**
 * Delete a business unit by its code
 * @param code - Business unit code to delete
 * @returns Promise with void
 */
export async function deleteFeature(code: string): Promise<void> {
  return apiDelete<void>(`/api/features/${encodeURIComponent(code)}`);
}
