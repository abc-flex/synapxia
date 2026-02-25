/**
 * Categories API Service
 * Handles all API calls related to categories
 */

import { apiGet, apiPost, apiPut, apiDelete, buildQueryString } from './api';
import type { Category } from '../types/category';

/**
 * Fetch all categories with optional pagination
 * @param skip - Number of records to skip (default: 0)
 * @param limit - Maximum number of records to return (default: 100)
 * @returns Promise with array of categories
 */
export async function getCategories(skip: number = 0, limit: number = 100): Promise<Category[]> {
  const queryString = buildQueryString({ skip, limit });
  return apiGet<Category[]>(`/api/categories${queryString}`);
}

/**
 * Fetch a single category by its code
 * @param code - Unique category code
 * @returns Promise with category data
 */
export async function getCategory(code: string): Promise<Category> {
  return apiGet<Category>(`/api/categories/${encodeURIComponent(code)}`);
}
