/**
 * Lists API Service
 * Handles all API calls related to lists
 */

import { apiGet } from './api';
import type { List } from '../types/list';

/**
 * Fetch all list records from the API
 * @returns Array of List objects
 * @throws Error if the API request fails
 */
export async function getAllLists(): Promise<List[]> {
  return await apiGet<List[]>('/api/lists');
}
