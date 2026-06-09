/**
 * Assignments API Service
 * Handles all API calls related to assignments
 */

import { apiGet, apiPost, apiPut, apiDelete, buildQueryString } from './api';
import type { Assignment, AssignmentCreate, AssignmentUpdate } from '../types/api';

/**
 * Fetch all assignments with optional pagination
 * @param skip - Number of records to skip (default: 0)
 * @param limit - Maximum number of records to return (default: 100)
 * @returns Promise with array of assignments
 */
export async function getAssignments(skip: number = 0, limit: number = 100): Promise<Assignment[]> {
  const queryString = buildQueryString({ skip, limit });
  return apiGet<Assignment[]>(`/api/assignments/${queryString}`);
}

/**
 * Fetch all assignments by list with optional pagination
 * @param list_code - list code
 * @param skip - Number of records to skip (default: 0)
 * @param limit - Maximum number of records to return (default: 100)
 * @returns Promise with array of assignments
 */
export async function getAssignmentsbyList(list_code: string, skip: number = 0, limit: number = 100): Promise<Assignment[]> {
  const queryString = buildQueryString({ skip, limit });
  return apiGet<Assignment[]>(`/api/assignments/${list_code}${queryString}`);
}

/**
 * Fetch a single assignment by its id
 * @param id - Unique assignment id
 * @returns Promise with assignment data
 */
export async function getAssignment(id: number): Promise<Assignment> {
  return apiGet<Assignment>(`/api/assignments/${id}`);
}

/**
 * Create a new assignment
 * @param data - Assignment data to create
 * @returns Promise with created assignment data
 */
export async function createAssignment(data: AssignmentCreate): Promise<Assignment> {
  return apiPost<Assignment, AssignmentCreate>('/api/assignments/', data);
}

/**
 * Update an existing assignment
 * @param code - Assignment code to update
 * @param data - Updated assignment data (partial)
 * @returns Promise with updated assignment data
 */
export async function updateAssignment(code: string, data: AssignmentUpdate): Promise<Assignment> {
  return apiPut<Assignment, AssignmentUpdate>(`/api/assignments/${encodeURIComponent(code)}`, data);
}

/**
 * Logically delete a assignment (sets is_active to false)
 * @param code - Assignment code to delete
 * @returns Promise with deletion result
 */
export async function deleteAssignment(code: string): Promise<void> {
  return apiDelete<void>(`/api/assignments/${encodeURIComponent(code)}`);
}
