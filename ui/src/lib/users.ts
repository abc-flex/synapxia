/**
 * Users API Service
 * Handles all API calls related to users
 */

import { apiGet, apiPost, apiPut, apiDelete, buildQueryString } from './api';
import type { User, UserCreate, UserUpdate } from '../types/api';

// Interface for select options with value and label
export interface UserSelectOption {
  value: string;
  label: string;
}

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
 * Fetch all users optimized for select fields
 * Returns only id and full name of active users
 * @returns Promise with array of UserSelectOption objects
 */
export async function getUsersSelect(): Promise<UserSelectOption[]> {
  return apiGet<UserSelectOption[]>(`/api/users/select`);
}

/**
 * Fetch all users by list with optional pagination
 * @param role_code - list code
 * @param skip - Number of records to skip (default: 0)
 * @param limit - Maximum number of records to return (default: 100)
 * @returns Promise with array of users
 */
export async function getUsersByRole(role_code: string, skip: number = 0, limit: number = 100): Promise<User[]> {
  const queryString = buildQueryString({ skip, limit });
  return apiGet<User[]>(`/api/users/role/${role_code}${queryString}`);
}

/**
 * Fetch a single user by its id
 * @param id - Unique user id
 * @returns Promise with user data
 */
export async function getUser(id: number): Promise<User> {
  return apiGet<User>(`/api/users/${encodeURIComponent(id)}`);
}

/**
 * Create a new user
 * @param data - User data to create
 * @returns Promise with created user
 */
export async function createUser(data: UserCreate): Promise<User> {
  return apiPost<User, UserCreate>('/api/users/', data);
}

/**
 * Update an existing user
 * @param id - User id to update
 * @param data - User data to update
 * @returns Promise with updated user
 */
export async function updateUser(id: number, data: UserUpdate): Promise<User> {
  return apiPut<User, UserUpdate>(`/api/users/${encodeURIComponent(id)}`, data);
}

/**
 * Delete a user by its id
 * @param id - User id to delete
 * @returns Promise with void
 */
export async function deleteUser(id: number): Promise<void> {
  return apiDelete<void>(`/api/users/${encodeURIComponent(id)}`);
}
