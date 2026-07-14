/**
 * Features API Service
 * Handles all API calls related to features
 */

import { apiGet, apiPost, apiPut, apiDelete, buildQueryString } from './api';
import type { Feature, FeatureCreate, FeatureUpdate } from '../types/api';

// Interface for select options with value and label
export interface FeatureSelectOption {
  value: string;
  label: string;
}

/**
 * Fetch all features with optional pagination
 * @param skip - Number of records to skip (default: 0)
 * @param limit - Maximum number of records to return (default: 100)
 * @returns Promise with array of features
 */
export async function getFeatures(skip: number = 0, limit: number = 100): Promise<Feature[]> {
  const queryString = buildQueryString({ skip, limit });
  return apiGet<Feature[]>(`/api/features/${queryString}`);
}

/**
 * Fetch all features optimized for select fields
 * Returns only code and name of active features
 * @returns Promise with array of FeatureSelectOption objects
 */
export async function getFeaturesSelect(): Promise<FeatureSelectOption[]> {
  return apiGet<FeatureSelectOption[]>(`/api/features/select`);
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
 * Create a new feature
 * @param data - Feature data to create
 * @returns Promise with created feature
 */
export async function createFeature(data: FeatureCreate): Promise<Feature> {
  return apiPost<Feature, FeatureCreate>('/api/features/', data);
}

/**
 * Update an existing business unit
 * @param code - Feature code to update
 * @param data - Feature data to update
 * @returns Promise with updated business unit
 */
export async function updateFeature(code: string, data: FeatureUpdate): Promise<Feature> {
  return apiPut<Feature, FeatureUpdate>(`/api/features/${encodeURIComponent(code)}`, data);
}

/**
 * Delete a business unit by its code
 * @param code - Feature code to delete
 * @returns Promise with void
 */
export async function deleteFeature(code: string): Promise<void> {
  return apiDelete<void>(`/api/features/${encodeURIComponent(code)}`);
}
