/**
 * ListItems API Service
 * Handles all API calls related to list_items
 */

import { apiGet, apiPost, apiPut, apiDelete, buildQueryString } from './api';
import type { ListItem } from '../types/list_items';

/**
 * Fetch all list_items with optional pagination
 * @param skip - Number of records to skip (default: 0)
 * @param limit - Maximum number of records to return (default: 100)
 * @returns Promise with array of list_items
 */
export async function getListItems(skip: number = 0, limit: number = 100): Promise<ListItem[]> {
  const queryString = buildQueryString({ skip, limit });
  return apiGet<ListItem[]>(`/api/list_items${queryString}`);
}

/**
 * Fetch all list_items by list with optional pagination
 * @param list_code - list code
 * @param skip - Number of records to skip (default: 0)
 * @param limit - Maximum number of records to return (default: 100)
 * @returns Promise with array of list_items
 */
export async function getListItemsbyList(list_code: string, skip: number = 0, limit: number = 100): Promise<ListItem[]> {
  const queryString = buildQueryString({ skip, limit });
  return apiGet<ListItem[]>(`/api/list_items/${list_code}${queryString}`);
}

/**
 * Fetch a single list_item by its code
 * @param code - Unique list_item code
 * @returns Promise with list_item data
 */
export async function getListItem(code: string): Promise<ListItem> {
  return apiGet<ListItem>(`/api/list_items/${encodeURIComponent(code)}`);
}
