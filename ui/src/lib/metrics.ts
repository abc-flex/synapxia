/**
 * Metrics API Service
 * Handles all API calls related to metrics
 */

import { apiGet, apiPost, apiPut, apiDelete, buildQueryString } from './api';
import type { Metric, MetricCreate, MetricUpdate } from '../types/api';

/**
 * Fetch all metrics with optional pagination
 * @param skip - Number of records to skip (default: 0)
 * @param limit - Maximum number of records to return (default: 100)
 * @returns Promise with array of metrics
 */
export async function getMetrics(skip: number = 0, limit: number = 100): Promise<Metric[]> {
  const queryString = buildQueryString({ skip, limit });
  return apiGet<Metric[]>(`/api/metrics/${queryString}`);
}

/**
 * Fetch a single metric by its ID
 * @param id - Unique metric ID
 * @returns Promise with metric data
 */
export async function getMetric(id: number): Promise<Metric> {
  return apiGet<Metric>(`/api/metrics/${id}`);
}

/**
 * Create a new metric
 * @param data - Metric data to create
 * @returns Promise with created metric
 */
export async function createMetric(data: MetricCreate): Promise<Metric> {
  return apiPost<Metric, MetricCreate>('/api/metrics/', data);
}

/**
 * Update an existing metric
 * @param id - Metric ID to update
 * @param data - Metric data to update
 * @returns Promise with updated metric
 */
export async function updateMetric(id: number, data: MetricUpdate): Promise<Metric> {
  return apiPut<Metric, MetricUpdate>(`/api/metrics/${id}`, data);
}

/**
 * Delete a metric by its ID (logical delete)
 * @param id - Metric ID to delete
 * @returns Promise with void
 */
export async function deleteMetric(id: number): Promise<void> {
  return apiDelete<void>(`/api/metrics/${id}`);
}
