/**
 * Processes API service — Process Management (`/proc/processes`,
 * specs/009-process-management). A new process starts in DRAFT; each Related
 * tab saves through one call that replaces the tab's whole set atomically.
 */
import { apiDelete, apiGet, apiPost, apiPut, buildQueryString } from "./api";
import type {
  Process,
  ProcessAssetItem,
  ProcessAssetLink,
  ProcessCreate,
  ProcessDetail,
  ProcessFormOptions,
  ProcessInitItem,
  ProcessInitLink,
  ProcessRelation,
  ProcessRelationItem,
  ProcessUpdate,
} from "@/types/api";

const enc = (v: string) => encodeURIComponent(v);
const PAGE = 500;

export interface ProcessFilters {
  type?: string;
  status?: string;
  unit?: string;
  q?: string;
}

export async function getProcesses(skip = 0, limit = PAGE, filters: ProcessFilters = {}): Promise<Process[]> {
  return apiGet<Process[]>(`/api/processes/${buildQueryString({ skip, limit, ...filters })}`);
}

export async function getProcess(code: string): Promise<ProcessDetail> {
  return apiGet<ProcessDetail>(`/api/processes/${enc(code)}`);
}

export async function getProcessFormOptions(): Promise<ProcessFormOptions> {
  return apiGet<ProcessFormOptions>("/api/processes/form-options");
}

/** All-or-nothing: the process and every staged link, in one transaction. */
export async function createProcess(data: ProcessCreate): Promise<ProcessDetail> {
  return apiPost<ProcessDetail, ProcessCreate>("/api/processes/", data);
}

export async function updateProcess(code: string, data: ProcessUpdate): Promise<ProcessDetail> {
  return apiPut<ProcessDetail, ProcessUpdate>(`/api/processes/${enc(code)}`, data);
}

/** Logical removal; refused (409) while the process has active children. */
export async function deleteProcess(code: string): Promise<Process> {
  return apiDelete<Process>(`/api/processes/${enc(code)}`);
}

export async function getProcessRelations(code: string): Promise<ProcessRelation[]> {
  return apiGet<ProcessRelation[]>(`/api/processes/${enc(code)}/relations`);
}

export async function saveProcessRelations(code: string, relations: ProcessRelationItem[]): Promise<ProcessRelation[]> {
  return apiPut<ProcessRelation[], { relations: ProcessRelationItem[] }>(
    `/api/processes/${enc(code)}/relations`, { relations });
}

export async function getProcessAssets(code: string): Promise<ProcessAssetLink[]> {
  return apiGet<ProcessAssetLink[]>(`/api/processes/${enc(code)}/assets`);
}

export async function saveProcessAssets(code: string, assets: ProcessAssetItem[]): Promise<ProcessAssetLink[]> {
  return apiPut<ProcessAssetLink[], { assets: ProcessAssetItem[] }>(
    `/api/processes/${enc(code)}/assets`, { assets });
}

export async function getProcessInits(code: string): Promise<ProcessInitLink[]> {
  return apiGet<ProcessInitLink[]>(`/api/processes/${enc(code)}/inits`);
}

export async function saveProcessInits(code: string, inits: ProcessInitItem[]): Promise<ProcessInitLink[]> {
  return apiPut<ProcessInitLink[], { inits: ProcessInitItem[] }>(
    `/api/processes/${enc(code)}/inits`, { inits });
}
