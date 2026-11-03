/**
 * Specifications API Service
 * Handles all API calls related to specifications
 */

import { apiGet, apiPost, apiPut, apiDelete, buildQueryString } from './api';
import type {
  Specification, SpecificationCreate, SpecificationUpdate, SpecificationMatrix, SpecificationMatrixEntry,
} from '../types/api';

/**
 * Fetch all specifications with optional pagination
 * @param skip - Number of records to skip (default: 0)
 * @param limit - Maximum number of records to return (default: 100)
 * @returns Promise with array of specifications
 */
export async function getSpecifications(skip: number = 0, limit: number = 100): Promise<Specification[]> {
  const queryString = buildQueryString({ skip, limit });
  return apiGet<Specification[]>(`/api/specifications/${queryString}`);
}

/**
 * Fetch all specifications by category with optional pagination
 * @param category_code - category code
 * @param skip - Number of records to skip (default: 0)
 * @param limit - Maximum number of records to return (default: 100)
 * @returns Promise with array of specifications
 */
export async function getSpecificationsbyCategory(category_code: string, skip: number = 0, limit: number = 100): Promise<Specification[]> {
  const queryString = buildQueryString({ skip, limit });
  return apiGet<Specification[]>(`/api/specifications/category/${category_code}${queryString}`);
}

/**
 * Fetch a single specification by category and feature
 * @param category_code - Unique category code
 * @param feature_code - Unique feature code
 * @returns Promise with specification data
 */
export async function getSpecification(category_code: string, feature_code: string): Promise<Specification> {
  return apiGet<Specification>(`/api/specifications/${encodeURIComponent(category_code)}/${encodeURIComponent(feature_code)}`);
}

/**
 * Create a new specification
 * @param data - Specification data to create
 * @returns Promise with created specification
 */
export async function createSpecification(data: SpecificationCreate): Promise<Specification> {
  return apiPost<Specification, SpecificationCreate>('/api/specifications/', data);
}

/**
 * Update an existing specification
 * @param category_code - Category code of the specification
 * @param feature_code - Feature code of the specification
 * @param data - Specification data to update
 * @returns Promise with updated specification
 */
export async function updateSpecification(category_code: string, feature_code: string, data: SpecificationUpdate): Promise<Specification> {
  return apiPut<Specification, SpecificationUpdate>(`/api/specifications/${encodeURIComponent(category_code)}/${encodeURIComponent(feature_code)}`, data);
}

/**
 * Delete a specification by its code
 * @param category_code - Category code of the specification
 * @param feature_code - Feature code of the specification
 * @returns Promise with void
 */
export async function deleteSpecification(category_code: string, feature_code: string): Promise<void> {
  return apiDelete<void>(`/api/specifications/${encodeURIComponent(category_code)}/${encodeURIComponent(feature_code)}`);
}

/**
 * One category's specification over every active feature (the checklist).
 * @param category_code - Category code
 */
export async function getSpecificationMatrix(category_code: string): Promise<SpecificationMatrix> {
  return apiGet<SpecificationMatrix>(`/api/specifications/category/${encodeURIComponent(category_code)}/matrix`);
}

/**
 * Save a category's specifications in one transaction.
 * @param category_code - Category code
 * @param specifications - The FULL set; features left out are removed
 */
export async function saveSpecificationMatrix(category_code: string, specifications: SpecificationMatrixEntry[]): Promise<SpecificationMatrix> {
  return apiPut<SpecificationMatrix>(`/api/specifications/category/${encodeURIComponent(category_code)}/matrix`, { specifications });
}
