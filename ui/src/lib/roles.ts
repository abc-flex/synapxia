/**
 * Roles API Service
 * Handles all API calls related to roles
 */

import { apiGet, apiPost, apiPut, apiDelete, buildQueryString } from './api';
import type { Role } from '../types/role';

/**
 * Fetch all roles with optional pagination
 * @param skip - Number of records to skip (default: 0)
 * @param limit - Maximum number of records to return (default: 100)
 * @returns Promise with array of roles
 */
export async function getRoles(skip: number = 0, limit: number = 100): Promise<Role[]> {
  const queryString = buildQueryString({ skip, limit });
  return apiGet<Role[]>(`/api/roles${queryString}`);
}

/**
 * Fetch a single role by its code
 * @param code - Unique role code
 * @returns Promise with role data
 */
export async function getRole(code: string): Promise<Role> {
  return apiGet<Role>(`/api/roles/${encodeURIComponent(code)}`);
}
