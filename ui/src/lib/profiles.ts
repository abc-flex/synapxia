/**
 * Profiles API Service
 * Handles all API calls related to profiles
 */

import { apiGet, apiPost, apiPut, apiDelete, buildQueryString } from './api';
import type { Profile, ProfileCreate, ProfileUpdate } from '../types/api';

// Interface for select options with value and label
export interface ProfileSelectOption {
  value: string;
  label: string;
}

/**
 * Fetch all profiles with optional pagination
 * @param skip - Number of records to skip (default: 0)
 * @param limit - Maximum number of records to return (default: 100)
 * @returns Promise with array of profiles
 */
export async function getProfiles(skip: number = 0, limit: number = 100): Promise<Profile[]> {
  const queryString = buildQueryString({ skip, limit });
  return apiGet<Profile[]>(`/api/profiles${queryString}`);
}

/**
 * Fetch all profiles optimized for select fields
 * Returns only code and name of active teams
 * @returns Promise with array of ProfileSelectOption objects
 */
export async function getProfilesSelect(): Promise<ProfileSelectOption[]> {
  return apiGet<ProfileSelectOption[]>(`/api/profiles/select`);
}

/**
 * Fetch a single profile by its code
 * @param code - Unique profile code
 * @returns Promise with profile data
 */
export async function getProfile(code: string): Promise<Profile> {
  return apiGet<Profile>(`/api/profiles/${encodeURIComponent(code)}`);
}

/**
 * Create a new profile
 * @param data - Profile data to create
 * @returns Promise with created profile
 */
export async function createProfile(data: ProfileCreate): Promise<Profile> {
  return apiPost<Profile, ProfileCreate>('/api/profiles/', data);
}

/**
 * Update an existing profile
 * @param code - Profile code to update
 * @param data - Profile data to update
 * @returns Promise with updated profile
 */
export async function updateProfile(code: string, data: ProfileUpdate): Promise<Profile> {
  return apiPut<Profile, ProfileUpdate>(`/api/profiles/${encodeURIComponent(code)}`, data);
}

/**
 * Delete a profile by its code
 * @param code - Profile code to delete
 * @returns Promise with void
 */
export async function deleteProfile(code: string): Promise<void> {
  return apiDelete<void>(`/api/profiles/${encodeURIComponent(code)}`);
}
