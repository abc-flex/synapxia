/**
 * Privileges API Service
 * Handles all API calls related to privileges
 */

import { apiGet, apiPost, apiPut, apiDelete, buildQueryString } from './api';
import type {
  Privilege, PrivilegeCreate, PrivilegeUpdate, PrivilegeMatrix, PrivilegeMatrixEntry,
} from '../types/api';

/**
 * Fetch a profile's privilege matrix: every active option of every active
 * module, each marked with the profile's access.
 * @param profile_code - Profile code
 */
export async function getPrivilegeMatrix(profile_code: string): Promise<PrivilegeMatrix> {
  return apiGet<PrivilegeMatrix>(`/api/privileges/profile/${encodeURIComponent(profile_code)}/matrix`);
}

/**
 * Save a profile's privilege matrix in one transaction.
 * @param profile_code - Profile code
 * @param privileges - The FULL set of granted options; anything left out is revoked
 */
export async function savePrivilegeMatrix(profile_code: string, privileges: PrivilegeMatrixEntry[]): Promise<PrivilegeMatrix> {
  return apiPut<PrivilegeMatrix>(`/api/privileges/profile/${encodeURIComponent(profile_code)}/matrix`, { privileges });
}

/**
 * Fetch all privileges with optional pagination
 * @param skip - Number of records to skip (default: 0)
 * @param limit - Maximum number of records to return (default: 100)
 * @returns Promise with array of privileges
 */
export async function getPrivileges(skip: number = 0, limit: number = 100): Promise<Privilege[]> {
  const queryString = buildQueryString({ skip, limit });
  return apiGet<Privilege[]>(`/api/privileges/${queryString}`);
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
  return apiGet<Privilege[]>(`/api/privileges/role/${role_code}${queryString}`);
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

/**
 * Create a new privilege
 * @param data - Privilege data to create
 * @returns Promise with created privilege
 */
export async function createPrivilege(data: PrivilegeCreate): Promise<Privilege> {
  return apiPost<Privilege, PrivilegeCreate>('/api/privileges/', data);
}

/**
 * Update an existing privilege
 * @param role_code - Role code of the privilege
 * @param module_code - Module code of the privilege
 * @param option_code - Option code of the privilege
 * @param data - Privilege data to update
 * @returns Promise with updated privilege
 */
export async function updatePrivilege(role_code: string, module_code: string, option_code: string, data: PrivilegeUpdate): Promise<Privilege> {
  return apiPut<Privilege, PrivilegeUpdate>(`/api/privileges/${encodeURIComponent(role_code)}/${encodeURIComponent(module_code)}/${encodeURIComponent(option_code)}`, data);
}

/**
 * Delete a privilege by its code
 * @param role_code - Role code of the privilege
 * @param module_code - Module code of the privilege
 * @param option_code - Option code of the privilege
 * @returns Promise with void
 */
export async function deletePrivilege(role_code: string, module_code: string, option_code: string): Promise<void> {
  return apiDelete<void>(`/api/privileges/${encodeURIComponent(role_code)}/${encodeURIComponent(module_code)}/${encodeURIComponent(option_code)}`);
}
