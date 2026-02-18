/**
 * Lists API Service
 * Handles all API calls related to lists
 */

import { apiGet, apiPost, apiPut, apiDelete, buildQueryString } from './api';
import type { List } from '../types/list';

/**
 * Fetch all lists with optional pagination
 * @param skip - Number of records to skip (default: 0)
 * @param limit - Maximum number of records to return (default: 100)
 * @returns Promise with array of lists
 */
export async function getLists(skip: number = 0, limit: number = 100): Promise<List[]> {
  const queryString = buildQueryString({ skip, limit });
  return apiGet<List[]>(`/api/lists${queryString}`);
}

/**
 * Fetch a single list by its code
 * @param code - Unique list code
 * @returns Promise with list data
 */
export async function getList(code: string): Promise<List> {
  return apiGet<List>(`/api/lists/${encodeURIComponent(code)}`);
}
