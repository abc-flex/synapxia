/**
 * Modules API Service
 * Handles all API calls related to modules
 */

import { apiGet, apiPost, apiPut, apiDelete, buildQueryString } from './api';
import type { Module, ModuleCreate, ModuleUpdate } from '../types/api';

// Interface for select options with value and label
export interface ModuleSelectOption {
  value: string;
  label: string;
}

/**
 * Fetch all modules with optional pagination
 * @param skip - Number of records to skip (default: 0)
 * @param limit - Maximum number of records to return (default: 100)
 * @returns Promise with array of modules
 */
export async function getModules(skip: number = 0, limit: number = 100): Promise<Module[]> {
  const queryString = buildQueryString({ skip, limit });
  return apiGet<Module[]>(`/api/modules${queryString}`);
}

/**
 * Fetch all modules optimized for select fields
 * Returns only code and name of active modules
 * @returns Promise with array of ModuleSelectOption objects
 */
export async function getModulesSelect(): Promise<ModuleSelectOption[]> {
  return apiGet<ModuleSelectOption[]>(`/api/modules/select`);
}

/**
 * Fetch a single module by its code
 * @param code - Unique module code
 * @returns Promise with module data
 */
export async function getModule(code: string): Promise<Module> {
  return apiGet<Module>(`/api/modules/${encodeURIComponent(code)}`);
}

/**
 * Create a new module
 * @param data - Module data to create
 * @returns Promise with created module
 */
export async function createModule(data: ModuleCreate): Promise<Module> {
  return apiPost<Module, ModuleCreate>('/api/modules/', data);
}

/**
 * Update an existing module
 * @param code - Module code to update
 * @param data - Module data to update
 * @returns Promise with updated module
 */
export async function updateModule(code: string, data: ModuleUpdate): Promise<Module> {
  return apiPut<Module, ModuleUpdate>(`/api/modules/${encodeURIComponent(code)}`, data);
}

/**
 * Delete a module by its code
 * @param code - Module code to delete
 * @returns Promise with void
 */
export async function deleteModule(code: string): Promise<void> {
  return apiDelete<void>(`/api/modules/${encodeURIComponent(code)}`);
}
