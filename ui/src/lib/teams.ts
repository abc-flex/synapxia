/**
 * Teams API Service
 * Handles all API calls related to teams
 */

import { apiGet, apiPost, apiPut, apiDelete, buildQueryString } from './api';
import type { Team } from '../types/team';

// Interface for select options with value and label
export interface TeamSelectOption {
  value: string;
  label: string;
}

/**
 * Fetch all teams with optional pagination
 * @param skip - Number of records to skip (default: 0)
 * @param limit - Maximum number of records to return (default: 100)
 * @returns Promise with array of teams
 */
export async function getTeams(skip: number = 0, limit: number = 100): Promise<Team[]> {
  const queryString = buildQueryString({ skip, limit });
  return apiGet<Team[]>(`/api/teams${queryString}`);
}

/**
 * Fetch all teams optimized for select fields
 * Returns only code and name of active teams
 * @returns Promise with array of TeamSelectOption objects
 */
export async function getTeamsSelect(): Promise<TeamSelectOption[]> {
  return apiGet<TeamSelectOption[]>(`/api/teams/select`);
}

/**
 * Fetch a single team by its code
 * @param code - Unique team code
 * @returns Promise with team data
 */
export async function getTeam(code: string): Promise<Team> {
  return apiGet<Team>(`/api/teams/${encodeURIComponent(code)}`);
}

/**
 * Create a new team
 * @param teamData - Team data to create
 * @returns Promise with created team data
 */
export async function createTeam(teamData: Partial<Team>): Promise<Team> {
  return apiPost<Team, Partial<Team>>('/api/teams', teamData);
}

/**
 * Update an existing team
 * @param code - Team code to update
 * @param teamData - Updated team data
 * @returns Promise with updated team data
 */
export async function updateTeam(code: string, teamData: Partial<Team>): Promise<Team> {
  return apiPut<Team, Partial<Team>>(`/api/teams/${encodeURIComponent(code)}`, teamData);
}

/**
 * Delete a team
 * @param code - Team code to delete
 * @returns Promise with deletion result
 */
export async function deleteTeam(code: string): Promise<void> {
  return apiDelete<void>(`/api/teams/${encodeURIComponent(code)}`);
}
