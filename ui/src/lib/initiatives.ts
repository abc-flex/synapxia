/**
 * Initiatives API service.
 *
 * Read helpers back Asset Management's "Related Inits" tab; the rest back
 * Initiative Management (`/inits/initiatives`, specs/004). There is no create:
 * initiatives are only ever proposed, never created by hand.
 */
import { apiDelete, apiGet, apiPost, apiPut, buildQueryString } from "./api";
import type {
  DiagnosisForm,
  DiagnosticsResponse,
  Initiative,
  InitiativeAsset,
  InitiativeAssetCreate,
  InitiativeDiagnoseRequest,
  InitiativeExploreItem,
  InitiativeProposeRequest,
  InitiativeResubmitRequest,
  InitiativeUpdate,
  InitiativeWithAccess,
  LinkableAsset,
  ReviewerOption,
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

/** Mark (`on`) or clear the current user's favorite. */
export async function setInitiativeFavorite(id: number, on: boolean): Promise<{ init: number; is_favorite: boolean }> {
  const route = `/api/initiatives/${enc(id)}/favorite`;
  return on
    ? apiPut<{ init: number; is_favorite: boolean }, Record<string, never>>(route, {})
    : apiDelete<{ init: number; is_favorite: boolean }>(route);
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

// ── Contribution workflow (specs/005-explore-initiatives) ────────────────────

/** Explore Initiatives gallery: accessible Accepted / In Progress / Delivered
 *  initiatives with the card counters. */
export async function getInitiativesExplore(skip = 0, limit = 500): Promise<InitiativeExploreItem[]> {
  return apiGet<InitiativeExploreItem[]>(
    `/api/initiatives/explore${buildQueryString({ skip, limit })}`,
  );
}

/** Eligible reviewers — the caller is left out unless they are an admin. */
export async function getInitiativeReviewers(): Promise<ReviewerOption[]> {
  return apiGet<ReviewerOption[]>("/api/initiatives/reviewers");
}

/** Assets the caller can see, for the Propose wizard's Related Assets step. */
export async function getLinkableAssets(): Promise<LinkableAsset[]> {
  return apiGet<LinkableAsset[]>("/api/initiatives/linkable-assets");
}

export async function proposeInitiative(data: InitiativeProposeRequest): Promise<Initiative> {
  return apiPost<Initiative, InitiativeProposeRequest>("/api/initiatives/propose", data);
}

export async function diagnoseInitiative(id: number, data: InitiativeDiagnoseRequest): Promise<Initiative> {
  return apiPost<Initiative, InitiativeDiagnoseRequest>(`/api/initiatives/${enc(id)}/diagnose`, data);
}

export async function resubmitInitiative(id: number, data: InitiativeResubmitRequest): Promise<Initiative> {
  return apiPost<Initiative, InitiativeResubmitRequest>(`/api/initiatives/${enc(id)}/resubmit`, data);
}

/** The diagnosis questionnaire: active criteria (unanswered) + each scale's
 *  options in `lang`. Readable with INITS/EXPLORE alone. */
export async function getDiagnosisForm(lang = "en"): Promise<DiagnosisForm> {
  return apiGet<DiagnosisForm>(`/api/initiatives/diagnosis-form${buildQueryString({ lang })}`);
}
