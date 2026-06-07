/**
 * Lists API Service
 * Handles all API calls related to lists
 */

import { apiGet, apiPost, apiPut, apiDelete, buildQueryString } from './api';
import type { List, ListCreate, ListUpdate } from '../types/api';

// Interface for select options with value and label
export interface ListSelectOption {
  value: string;
  label: string;
}

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
 * Fetch all lists optimized for select fields
 * Returns only code and name of active lists
 * @returns Promise with array of ListSelectOption objects
 */
export async function getListsSelect(): Promise<ListSelectOption[]> {
  return apiGet<ListSelectOption[]>(`/api/lists/select`);
}

/**
 * Fetch a single list by its code
 * @param code - Unique list code
 * @returns Promise with list data
 */
export async function getList(code: string): Promise<List> {
  return apiGet<List>(`/api/lists/${encodeURIComponent(code)}`);
}

/**
 * Fetch all list by type
 * @param list_type - list code
 * @param skip - Number of records to skip (default: 0)
 * @param limit - Maximum number of records to return (default: 100)
 * @returns Promise with array of lists
 */
export async function getListsbyType(list_type: string, skip: number = 0, limit: number = 100): Promise<List[]> {
  const queryString = buildQueryString({ skip, limit });
  return apiGet<List[]>(`/api/lists/type/${list_type}${queryString}`);
}

/**
 * Create a new list
 * @param data - List data to create
 * @returns Promise with created list
 */
export async function createList(data: ListCreate): Promise<List> {
  return apiPost<List, ListCreate>('/api/lists/', data);
}

/**
 * Update an existing list
 * @param code - List code to update
 * @param data - List data to update
 * @returns Promise with updated list
 */
export async function updateList(code: string, data: ListUpdate): Promise<List> {
  return apiPut<List, ListUpdate>(`/api/lists/${encodeURIComponent(code)}`, data);
}

/**
 * Delete a list by its code
 * @param code - List code to delete
 * @returns Promise with void
 */
export async function deleteList(code: string): Promise<void> {
  return apiDelete<void>(`/api/lists/${encodeURIComponent(code)}`);
}
