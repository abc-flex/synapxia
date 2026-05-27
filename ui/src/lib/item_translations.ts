/**
 * ItemTranslations API Service
 * Handles all API calls related to item_translations
 */

import { apiGet, apiPost, apiPut, apiDelete, buildQueryString } from './api';
import type { ItemTranslation, ItemTranslationCreate, ItemTranslationUpdate } from '../types/api';

/**
 * Fetch all item_translations with optional pagination
 * @param skip - Number of records to skip (default: 0)
 * @param limit - Maximum number of records to return (default: 100)
 * @returns Promise with array of item_translations
 */
export async function getItemTranslations(skip: number = 0, limit: number = 100): Promise<ItemTranslation[]> {
  const queryString = buildQueryString({ skip, limit });
  return apiGet<ItemTranslation[]>(`/api/item_translations${queryString}`);
}

/**
 * Fetch all item_translations by list with optional pagination
 * @param list_code - list code
 * @param skip - Number of records to skip (default: 0)
 * @param limit - Maximum number of records to return (default: 100)
 * @returns Promise with array of item_translations
 */
export async function getItemTranslationsbyList(list_code: string, skip: number = 0, limit: number = 100): Promise<ItemTranslation[]> {
  const queryString = buildQueryString({ skip, limit });
  return apiGet<ItemTranslation[]>(`/api/item_translations/list/${list_code}${queryString}`);
}

/**
 * Fetch a single item_translation by its code
 * @param code - Unique item_translation code
 * @returns Promise with item_translation data
 */
export async function getItemTranslation(code: string): Promise<ItemTranslation> {
  return apiGet<ItemTranslation>(`/api/item_translations/${encodeURIComponent(code)}`);
}


/**
 * Create a new list item
 * @param data - List item data to create
 * @returns Promise with created list item
 */
export async function createItemTranslation(data: ItemTranslationCreate): Promise<ItemTranslation> {
  return apiPost<ItemTranslation, ItemTranslationCreate>('/api/item_translations/', data);
}

/**
 * Update an existing list item
 * @param list_code - List code
 * @param value - List item value
 * @param data - List item data to update
 * @returns Promise with updated list item
 */
export async function updateItemTranslation(list_code: string, value: string, data: ItemTranslationUpdate): Promise<ItemTranslation> {
  return apiPut<ItemTranslation, ItemTranslationUpdate>(`/api/item_translations/${encodeURIComponent(list_code)}/${encodeURIComponent(value)}`, data);
}

/**
 * Delete a list item by its list, item and value
 * @param list_code - List code
 * @param value - List item value
 * @returns Promise with void
 */
export async function deleteItemTranslation(list_code: string, value: string): Promise<void> {
  return apiDelete<void>(`/api/item_translations/${encodeURIComponent(list_code)}/${encodeURIComponent(value)}`);
}
