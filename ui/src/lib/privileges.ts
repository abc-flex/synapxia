/**
 * Privileges API Service
 * Handles all API calls related to privileges
 */

import { apiGet, apiPost, apiPut, apiDelete, buildQueryString } from './api';
import type { Privilege } from '../types/privileges';

/**
 * Fetch all privileges with optional pagination
 * @param skip - Number of records to skip (default: 0)
 * @param limit - Maximum number of records to return (default: 100)
 * @returns Promise with array of privileges
 */
export async function getPrivileges(skip: number = 0, limit: number = 100): Promise<Privilege[]> {
  const queryString = buildQueryString({ skip, limit });
  return apiGet<Privilege[]>(`/api/privileges${queryString}`);
}

/**
 * Fetch all privileges by role with optional pagination
 * @param list_code - role code
 * @param skip - Number of records to skip (default: 0)
 * @param limit - Maximum number of records to return (default: 100)
 * @returns Promise with array of privileges
 */
export async function getPrivilegesbyRole(role_code: string, skip: number = 0, limit: number = 100): Promise<Privilege[]> {
  const queryString = buildQueryString({ skip, limit });
  return apiGet<Privilege[]>(`/api/privileges/${role_code}${queryString}`);
}

/**
 * Fetch a single privilege by its code
 * @param role_code - Unique privilege code
 * @param module_code - Unique privilege code
 * @param option_code - Unique privilege code
 * @returns Promise with privilege data
 */
export async function getPrivilege(role_code: string, module_code: string, option_code: string): Promise<Privilege> {
  return apiGet<Privilege>(`/api/privileges/${encodeURIComponent(role_code)}/${encodeURIComponent(module_code)}/${encodeURIComponent(option_code)}`);
}
