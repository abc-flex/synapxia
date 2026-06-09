/**
 * Projects API Service
 * Handles all API calls related to projects
 */

import { apiGet, apiPost, apiPut, apiDelete, buildQueryString } from './api';
import type { Project, ProjectCreate, ProjectUpdate } from '../types/api';

/**
 * Fetch all active projects with optional team filter and pagination
 * @param team - Optional team code to filter by
 * @param skip - Number of records to skip (default: 0)
 * @param limit - Maximum number of records to return (default: 100)
 * @returns Promise with array of projects
 */
export async function getProjects(team?: string, skip: number = 0, limit: number = 100): Promise<Project[]> {
  const queryString = buildQueryString({ ...(team ? { team } : {}), skip, limit });
  return apiGet<Project[]>(`/api/projects/${queryString}`);
}

/**
 * Fetch a single project by its code
 * @param code - Unique project code
 * @returns Promise with project data
 */
export async function getProject(code: string): Promise<Project> {
  return apiGet<Project>(`/api/projects/${encodeURIComponent(code)}`);
}

/**
 * Create a new project
 * @param data - Project data to create
 * @returns Promise with created project data
 */
export async function createProject(data: ProjectCreate): Promise<Project> {
  return apiPost<Project, ProjectCreate>('/api/projects/', data);
}

/**
 * Update an existing project
 * @param code - Project code to update
 * @param data - Updated project data (partial)
 * @returns Promise with updated project data
 */
export async function updateProject(code: string, data: ProjectUpdate): Promise<Project> {
  return apiPut<Project, ProjectUpdate>(`/api/projects/${encodeURIComponent(code)}`, data);
}

/**
 * Logically delete a project (sets is_active to false)
 * @param code - Project code to delete
 * @returns Promise with deletion result
 */
export async function deleteProject(code: string): Promise<void> {
  return apiDelete<void>(`/api/projects/${encodeURIComponent(code)}`);
}
