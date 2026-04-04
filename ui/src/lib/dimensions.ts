/**
 * Dimensions API Service
 * Handles all API calls related to dimensions
 */

import { apiGet, apiPost, apiPut, apiDelete, buildQueryString } from './api';
import type { Dimension, DimensionCreate, DimensionUpdate } from '../types/api';

/**
 * Fetch all dimensions with optional pagination
 * @param skip - Number of records to skip (default: 0)
 * @param limit - Maximum number of records to return (default: 100)
 * @returns Promise with array of dimensions
 */
export async function getDimensions(skip: number = 0, limit: number = 100): Promise<Dimension[]> {
  const queryString = buildQueryString({ skip, limit });
  return apiGet<Dimension[]>(`/api/dimensions${queryString}`);
}

/**
 * Fetch a single dimension by its code
 * @param code - Unique dimension code
 * @returns Promise with dimension data
 */
export async function getDimension(code: string): Promise<Dimension> {
  return apiGet<Dimension>(`/api/dimensions/${encodeURIComponent(code)}`);
}

/**
 * Create a new dimension
 * @param data - Dimension data to create
 * @returns Promise with created dimension
 */
export async function createDimension(data: DimensionCreate): Promise<Dimension> {
  return apiPost<Dimension, DimensionCreate>('/api/dimensions/', data);
}

/**
 * Update an existing dimension
 * @param code - Dimension code to update
 * @param data - Dimension data to update
 * @returns Promise with updated dimension
 */
export async function updateDimension(code: string, data: DimensionUpdate): Promise<Dimension> {
  return apiPut<Dimension, DimensionUpdate>(`/api/dimensions/${encodeURIComponent(code)}`, data);
}

/**
 * Delete a dimension by its code (logical delete)
 * @param code - Dimension code to delete
 * @returns Promise with void
 */
export async function deleteDimension(code: string): Promise<void> {
  return apiDelete<void>(`/api/dimensions/${encodeURIComponent(code)}`);
}
