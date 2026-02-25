/**
 * Assignments API Service
 * Handles all API calls related to assignments
 */

import { apiGet, apiPost, apiPut, apiDelete, buildQueryString } from './api';
import type { Assignment } from '../types/assignments';

/**
 * Fetch all assignments with optional pagination
 * @param skip - Number of records to skip (default: 0)
 * @param limit - Maximum number of records to return (default: 100)
 * @returns Promise with array of assignments
 */
export async function getAssignments(skip: number = 0, limit: number = 100): Promise<Assignment[]> {
  const queryString = buildQueryString({ skip, limit });
  return apiGet<Assignment[]>(`/api/assignments${queryString}`);
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
 */im
export async function getAssignment(id: number): Promise<Assignment> {
  return apiGet<Assignment>(`/api/assignments/${id}`);
}
