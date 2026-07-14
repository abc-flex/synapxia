/**
 * Options API Service
 * Handles all API calls related to navigation options
 */

import { apiGet, apiPost, apiPut, apiDelete, buildQueryString } from './api';
import type { Option, OptionCreate, OptionUpdate } from '../types/api';

// Interface for select options with value and label
export interface OptionSelectOption {
  value: string;
  label: string;
}

/**
 * Fetch all options with optional pagination and filtering
 * @param module - Optional module code to filter by
 * @param skip - Number of records to skip (default: 0)
 * @param limit - Maximum number of records to return (default: 100)
 * @returns Promise with array of options
 */
export async function getOptions(module?: string, skip: number = 0, limit: number = 100): Promise<Option[]> {
  const params: Record<string, any> = { skip, limit };
  if (module) {
    params.module = module;
  }
  const queryString = buildQueryString(params);
  return apiGet<Option[]>(`/api/options/${queryString}`);
}

/**
 * Fetch all options optimized for select fields
 * Returns only code and name of active options
 * @returns Promise with array of OptionSelectOption objects
 */
export async function getOptionsSelect(): Promise<OptionSelectOption[]> {
  return apiGet<OptionSelectOption[]>(`/api/options/select`);
}

/**
 * Fetch a single option by its module and code
 * @param module - Module code
 * @param code - Option code
 * @returns Promise with option data
 */
export async function getOption(module: string, code: string): Promise<Option> {
  return apiGet<Option>(`/api/options/${encodeURIComponent(module)}/${encodeURIComponent(code)}`);
}

/**
 * Create a new option
 * @param data - Option data to create
 * @returns Promise with created option
 */
export async function createOption(data: OptionCreate): Promise<Option> {
  return apiPost<Option, OptionCreate>('/api/options/', data);
}

/**
 * Update an existing option
 * @param module - Module code
 * @param code - Option code to update
 * @param data - Option data to update
 * @returns Promise with updated option
 */
export async function updateOption(module: string, code: string, data: OptionUpdate): Promise<Option> {
  return apiPut<Option, OptionUpdate>(
    `/api/options/${encodeURIComponent(module)}/${encodeURIComponent(code)}`, 
    data
  );
}

/**
 * Delete an option by its module and code
 * @param module - Module code
 * @param code - Option code to delete
 * @returns Promise with void
 */
export async function deleteOption(module: string, code: string): Promise<void> {
  return apiDelete<void>(`/api/options/${encodeURIComponent(module)}/${encodeURIComponent(code)}`);
}
