/**
 * Business_Units API Service
 * Handles all API calls related to business_units
 */

import { apiGet, apiPost, apiPut, apiDelete, buildQueryString } from './api';
import type { BusinessUnit } from '../types/business_unit';

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
