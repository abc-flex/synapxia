/**
 * Initiatives API service — read-only (the API only exposes GET routes today,
 * see api/app/inits/internal/models.py). Used by Asset Management's
 * "Related Inits" tab to populate the target-initiative dropdown.
 */
import { apiGet, buildQueryString } from "./api";
import type { Initiative } from "@/types/api";

export interface InitiativeSelectOption {
  value: string;
  label: string;
}

export async function getInitiatives(skip = 0, limit = 100): Promise<Initiative[]> {
  return apiGet<Initiative[]>(`/api/initiatives/${buildQueryString({ skip, limit })}`);
}

export async function getInitiativesSelect(): Promise<InitiativeSelectOption[]> {
  return apiGet<InitiativeSelectOption[]>("/api/initiatives/select");
}

export async function getInitiative(id: number): Promise<Initiative> {
  return apiGet<Initiative>(`/api/initiatives/${encodeURIComponent(String(id))}`);
}
