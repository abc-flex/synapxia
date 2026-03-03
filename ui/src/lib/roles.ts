/**
 * Roles API Service
 * Handles all API calls related to roles
 */

import { apiGet, apiPost, apiPut, apiDelete, buildQueryString } from './api';
import type { Role, RoleCreate, RoleUpdate } from '../types/api';

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

/**
 * Create a new role
 * @param data - Role data to create
 * @returns Promise with created role
 */
export async function createRole(data: RoleCreate): Promise<Role> {
  return apiPost<Role, RoleCreate>('/api/roles/', data);
}

/**
 * Update an existing role
 * @param code - Role code to update
 * @param data - Role data to update
 * @returns Promise with updated role
 */
export async function updateRole(code: string, data: RoleUpdate): Promise<Role> {
  return apiPut<Role, RoleUpdate>(`/api/roles/${encodeURIComponent(code)}`, data);
}

/**
 * Delete a role by its code
 * @param code - Role code to delete
 * @returns Promise with void
 */
export async function deleteRole(code: string): Promise<void> {
  return apiDelete<void>(`/api/roles/${encodeURIComponent(code)}`);
}
