/**
 * ListItems API Service
 * Handles all API calls related to list_items
 */

import { apiGet, apiPost, apiPut, apiDelete, buildQueryString } from './api';
import type { ListItem, ListItemCreate, ListItemUpdate } from '../types/api';

/**
 * Fetch all list_items with optional pagination
 * @param skip - Number of records to skip (default: 0)
 * @param limit - Maximum number of records to return (default: 100)
 * @returns Promise with array of list_items
 */
export async function getListItems(skip: number = 0, limit: number = 100): Promise<ListItem[]> {
  const queryString = buildQueryString({ skip, limit });
  return apiGet<ListItem[]>(`/api/list_items/${queryString}`);
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
  return apiGet<ListItem[]>(`/api/list_items/list/${list_code}${queryString}`);
}

/**
 * Fetch a single list_item by its code
 * @param code - Unique list_item code
 * @returns Promise with list_item data
 */
export async function getListItem(code: string): Promise<ListItem> {
  return apiGet<ListItem>(`/api/list_items/${encodeURIComponent(code)}`);
}


/**
 * Create a new list item
 * @param data - List item data to create
 * @returns Promise with created list item
 */
export async function createListItem(data: ListItemCreate): Promise<ListItem> {
  return apiPost<ListItem, ListItemCreate>('/api/list_items/', data);
}

/**
 * Update an existing list item
 * @param list_code - List code
 * @param lang - Language code
 * @param value - List item value
 * @param data - List item data to update
 * @returns Promise with updated list item
 */
export async function updateListItem(list_code: string, lang: string, value: string, data: ListItemUpdate): Promise<ListItem> {
  return apiPut<ListItem, ListItemUpdate>(`/api/list_items/${encodeURIComponent(list_code)}/${encodeURIComponent(lang)}/${encodeURIComponent(value)}`, data);
}

/**
 * Delete a list item by its list and value
 * @param list_code - List code
 * @param lang - Language code
 * @param value - List item value
 * @returns Promise with void
 */
export async function deleteListItem(list_code: string, lang: string, value: string): Promise<void> {
  return apiDelete<void>(`/api/list_items/${encodeURIComponent(list_code)}/${encodeURIComponent(lang)}/${encodeURIComponent(value)}`);
}
