/**
 * Users API Service
 * Handles all API calls related to users
 */

import { apiGet, apiPost, apiPut, apiDelete, buildQueryString } from './api';
import type { User } from '../types/users';

/**
 * Fetch all users with optional pagination
 * @param skip - Number of records to skip (default: 0)
 * @param limit - Maximum number of records to return (default: 100)
 * @returns Promise with array of users
 */
export async function getUsers(skip: number = 0, limit: number = 100): Promise<User[]> {
  const queryString = buildQueryString({ skip, limit });
  return apiGet<User[]>(`/api/users${queryString}`);
}

/**
 * Fetch all users by list with optional pagination
 * @param role_code - list code
 * @param skip - Number of records to skip (default: 0)
 * @param limit - Maximum number of records to return (default: 100)
 * @returns Promise with array of users
 */
export async function getUsersbyRole(role_code: string, skip: number = 0, limit: number = 100): Promise<User[]> {
  const queryString = buildQueryString({ skip, limit });
  return apiGet<User[]>(`/api/users/${role_code}${queryString}`);
}

/**
 * Fetch a single user by its id
 * @param id - Unique user id
 * @returns Promise with user data
 */
export async function getUser(id: number): Promise<User> {
  return apiGet<User>(`/api/users/${encodeURIComponent(id)}`);
}
