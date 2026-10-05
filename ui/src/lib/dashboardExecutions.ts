/**
 * Dashboard Catalog + executions API service (`/ana/catalog`,
 * specs/007-dashboard-catalog). Consumer-facing: gated on ANA/CATALOG (read).
 *
 * A run is recorded in two steps — `startExecution` (the server validates and
 * always writes one row) then `finishExecution` once with the outcome only the
 * browser knows. A parameters window closed without running is
 * `recordCancelled`. Favorites reuse `setDashboardFavorite` (lib/dashboards).
 */
import { apiGet, apiPost, buildQueryString } from "./api";
import type {
  CatalogDashboard,
  ExecutionRead,
  ExecutionStarted,
  ExecutionStatus,
  LastValues,
  RunForm,
} from "@/types/api";

const enc = (v: number) => encodeURIComponent(String(v));

export async function getCatalog(skip = 0, limit = 500): Promise<CatalogDashboard[]> {
  return apiGet<CatalogDashboard[]>(`/api/dashboards/catalog${buildQueryString({ skip, limit })}`);
}

export async function getRunForm(id: number): Promise<RunForm> {
  return apiGet<RunForm>(`/api/dashboards/${enc(id)}/run-form`);
}

export async function startExecution(id: number, values: Record<string, string>): Promise<ExecutionStarted> {
  return apiPost<ExecutionStarted, { values: Record<string, string> }>(
    `/api/dashboards/${enc(id)}/executions`, { values });
}

export async function finishExecution(
  executionId: number, status: Exclude<ExecutionStatus, "UNAUTHORIZED">, errorMessage?: string,
): Promise<ExecutionRead> {
  return apiPost<ExecutionRead, { status: string; error_message: string | null }>(
    `/api/executions/${enc(executionId)}/finish`, { status, error_message: errorMessage ?? null });
}

export async function recordCancelled(
  id: number, values: Record<string, string>, durationMs: number,
): Promise<ExecutionRead> {
  return apiPost<ExecutionRead, { values: Record<string, string>; duration_ms: number }>(
    `/api/dashboards/${enc(id)}/executions/cancelled`,
    { values, duration_ms: Math.max(0, Math.round(durationMs)) });
}

export async function getLastValues(id: number): Promise<LastValues> {
  return apiGet<LastValues>(`/api/dashboards/${enc(id)}/executions/last-values`);
}
