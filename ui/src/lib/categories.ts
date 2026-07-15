/**
 * Business_Units API Service
 * Handles all API calls related to categories
 */

import { apiGet, apiPost, apiPut, apiDelete, buildQueryString } from './api';
import type { Category, CategoryCreate, CategoryUpdate } from '../types/api';

// Interface for select categories with value and label
export interface CategorySelectOption {
  value: string;
  label: string;
}

// Interface for categories with assets count
export interface CategoryWithAssets {
  code: string;
  name: string;
  description: string | null;
  parent: string | null;
  option: string | null;
  assets_count: number;
}

/**
 * Fetch all categories with optional pagination
 * @param skip - Number of records to skip (default: 0)
 * @param limit - Maximum number of records to return (default: 100)
 * @returns Promise with array of categories
 */
export async function getCategories(skip: number = 0, limit: number = 100): Promise<Category[]> {
  const queryString = buildQueryString({ skip, limit });
  return apiGet<Category[]>(`/api/categories/${queryString}`);
}

/**
 * Fetch all categories optimized for select fields
 * Returns only code and name of active categories
 * @returns Promise with array of CategorySelectOption objects
 */
export async function getCategoriesSelect(): Promise<CategorySelectOption[]> {
  return apiGet<CategorySelectOption[]>(`/api/categories/select`);
}

/**
 * Fetch all categories with assets count optimized for treeview controls
 * Returns values of active categories
 * @returns Promise with array of CategoryWithAssets objects
 */
export async function getCategoriesWithAssetsCount(skip: number = 0, limit: number = 100): Promise<CategoryWithAssets[]> {
  const queryString = buildQueryString({ skip, limit });
  return apiGet<CategoryWithAssets[]>(`/api/categories/assets${queryString}`);
}

/**
 * Fetch a single category by its code
 * @param code - Unique category code
 * @returns Promise with category data
 */
export async function getCategory(code: string): Promise<Category> {
  return apiGet<Category>(`/api/categories/${encodeURIComponent(code)}`);
}

/**
 * Create a new category
 * @param data - Business unit data to create
 * @returns Promise with created category
 */
export async function createCategory(data: CategoryCreate): Promise<Category> {
  return apiPost<Category, CategoryCreate>('/api/categories/', data);
}

/**
 * Update an existing category
 * @param code - Business unit code to update
 * @param data - Business unit data to update
 * @returns Promise with updated category
 */
export async function updateCategory(code: string, data: CategoryUpdate): Promise<Category> {
  return apiPut<Category, CategoryUpdate>(`/api/categories/${encodeURIComponent(code)}`, data);
}

/**
 * Delete a category by its code
 * @param code - Business unit code to delete
 * @returns Promise with void
 */
export async function deleteCategory(code: string): Promise<void> {
  return apiDelete<void>(`/api/categories/${encodeURIComponent(code)}`);
}
