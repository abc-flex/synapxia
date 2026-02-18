/**
 * Modules API Service
 * Handles all API calls related to modules
 */

import { apiGet, apiPost, apiPut, apiDelete, buildQueryString } from './api';
import type { Module } from '../types/module';

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
 * Fetch a single module by its code
 * @param code - Unique module code
 * @returns Promise with module data
 */
export async function getModule(code: string): Promise<Module> {
  return apiGet<Module>(`/api/modules/${encodeURIComponent(code)}`);
}
