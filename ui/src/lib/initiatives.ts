/**
 * Initiatives API service.
 *
 * Read helpers back Asset Management's "Related Inits" tab; the rest back
 * Initiative Management (`/inits/initiatives`, specs/004). There is no create:
 * initiatives are only ever proposed, never created by hand.
 */
import { apiDelete, apiGet, apiPost, apiPut, buildQueryString } from "./api";
import type {
  DiagnosticsResponse,
  Initiative,
  InitiativeAsset,
  InitiativeAssetCreate,
  InitiativeUpdate,
  InitiativeWithAccess,
} from "@/types/api";

export interface InitiativeSelectOption {
  value: string;
  label: string;
}

const enc = (v: number | string) => encodeURIComponent(String(v));

export async function getInitiatives(skip = 0, limit = 100): Promise<Initiative[]> {
  return apiGet<Initiative[]>(`/api/initiatives/${buildQueryString({ skip, limit })}`);
}

export async function getInitiativesSelect(): Promise<InitiativeSelectOption[]> {
  return apiGet<InitiativeSelectOption[]>("/api/initiatives/select");
}

export async function getInitiative(id: number): Promise<Initiative> {
  return apiGet<Initiative>(`/api/initiatives/${enc(id)}`);
}

/** Initiatives the caller can access, with `my_access`, `is_favorite` and
 *  `allowed_statuses`. The portfolio is small; 500 is the API's upper bound. */
export async function getInitiativesWithAccess(skip = 0, limit = 500): Promise<InitiativeWithAccess[]> {
  return apiGet<InitiativeWithAccess[]>(
    `/api/initiatives/with-access${buildQueryString({ skip, limit })}`,
  );
}

export async function updateInitiative(id: number, data: InitiativeUpdate): Promise<InitiativeWithAccess> {
  return apiPut<InitiativeWithAccess, InitiativeUpdate>(`/api/initiatives/${enc(id)}`, data);
}

export async function deleteInitiative(id: number): Promise<Initiative> {
  return apiDelete<Initiative>(`/api/initiatives/${enc(id)}`);
}

export async function getInitiativeDiagnostics(id: number, lang = "en"): Promise<DiagnosticsResponse> {
  return apiGet<DiagnosticsResponse>(
    `/api/initiatives/${enc(id)}/diagnostics${buildQueryString({ lang })}`,
  );
}

export async function getInitiativeAssets(id: number): Promise<InitiativeAsset[]> {
  return apiGet<InitiativeAsset[]>(`/api/initiatives/${enc(id)}/assets`);
}

export async function addInitiativeAsset(id: number, data: InitiativeAssetCreate): Promise<InitiativeAsset> {
  return apiPost<InitiativeAsset, InitiativeAssetCreate>(`/api/initiatives/${enc(id)}/assets`, data);
}

/** Remove one link — the same asset may be linked once per relation type. */
export async function removeInitiativeAsset(id: number, assetId: number, type: string): Promise<void> {
  await apiDelete(`/api/initiatives/${enc(id)}/assets/${enc(assetId)}/${enc(type)}`);
}
