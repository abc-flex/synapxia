/**
 * Business_Units API Service
 * Handles all API calls related to business_units
 */

import { apiGet, apiPost, apiPut, apiDelete, buildQueryString } from './api';
import type { BusinessUnit, BusinessUnitCreate, BusinessUnitUpdate } from '../types/api';

/**
 * Fetch all business_units with optional pagination
 * @param skip - Number of records to skip (default: 0)
 * @param limit - Maximum number of records to return (default: 100)
 * @returns Promise with array of business_units
 */
export async function getBusinessUnits(skip: number = 0, limit: number = 100): Promise<BusinessUnit[]> {
  const queryString = buildQueryString({ skip, limit });
  return apiGet<BusinessUnit[]>(`/api/business_units${queryString}`);
}

/**
 * Fetch a single business_unit by its code
 * @param code - Unique business_unit code
 * @returns Promise with business_unit data
 */
export async function getBusinessUnit(code: string): Promise<BusinessUnit> {
  return apiGet<BusinessUnit>(`/api/business_units/${encodeURIComponent(code)}`);
}

/**
 * Create a new business unit
 * @param data - Business unit data to create
 * @returns Promise with created business unit
 */
export async function createBusinessUnit(data: BusinessUnitCreate): Promise<BusinessUnit> {
  return apiPost<BusinessUnit, BusinessUnitCreate>('/api/business_units/', data);
}

/**
 * Update an existing business unit
 * @param code - Business unit code to update
 * @param data - Business unit data to update
 * @returns Promise with updated business unit
 */
export async function updateBusinessUnit(code: string, data: BusinessUnitUpdate): Promise<BusinessUnit> {
  return apiPut<BusinessUnit, BusinessUnitUpdate>(`/api/business_units/${encodeURIComponent(code)}`, data);
}

/**
 * Delete a business unit by its code
 * @param code - Business unit code to delete
 * @returns Promise with void
 */
export async function deleteBusinessUnit(code: string): Promise<void> {
  return apiDelete<void>(`/api/business_units/${encodeURIComponent(code)}`);
}
