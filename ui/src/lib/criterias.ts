/**
 * Criterias API Service
 * Handles all API calls related to criterias
 */

import { apiGet, apiPost, apiPut, apiDelete, buildQueryString } from './api';
import type { Criteria, CriteriaCreate, CriteriaUpdate } from '../types/api';

// Interface for select options with value and label
export interface CriteriaSelectOption {
  value: string;
  label: string;
}

/**
 * Fetch all criterias with optional pagination
 * @param skip - Number of records to skip (default: 0)
 * @param limit - Maximum number of records to return (default: 100)
 * @returns Promise with array of criterias
 */
export async function getCriterias(skip: number = 0, limit: number = 100): Promise<Criteria[]> {
  const queryString = buildQueryString({ skip, limit });
  return apiGet<Criteria[]>(`/api/criterias/${queryString}`);
}

/**
 * Fetch all criterias optimized for select fields
 * Returns only code and name of active criterias
 * @returns Promise with array of CriteriaSelectOption objects
 */
export async function getCriteriasSelect(): Promise<CriteriaSelectOption[]> {
  return apiGet<CriteriaSelectOption[]>(`/api/criterias/select`);
}

/**
 * Fetch a single criteria by its code
 * @param code - Unique criteria code
 * @returns Promise with criteria data
 */
export async function getCriteria(code: string): Promise<Criteria> {
  return apiGet<Criteria>(`/api/criterias/${encodeURIComponent(code)}`);
}

/**
 * Create a new criteria
 * @param data - Criteria data to create
 * @returns Promise with created criteria
 */
export async function createCriteria(data: CriteriaCreate): Promise<Criteria> {
  return apiPost<Criteria, CriteriaCreate>('/api/criterias/', data);
}

/**
 * Update an existing business unit
 * @param code - Criteria code to update
 * @param data - Criteria data to update
 * @returns Promise with updated business unit
 */
export async function updateCriteria(code: string, data: CriteriaUpdate): Promise<Criteria> {
  return apiPut<Criteria, CriteriaUpdate>(`/api/criterias/${encodeURIComponent(code)}`, data);
}

/**
 * Delete a business unit by its code
 * @param code - Criteria code to delete
 * @returns Promise with void
 */
export async function deleteCriteria(code: string): Promise<void> {
  return apiDelete<void>(`/api/criterias/${encodeURIComponent(code)}`);
}
