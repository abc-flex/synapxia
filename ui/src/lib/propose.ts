/**
 * propose — the asset proposal service (HU-Propose), the entry point of the
 * review workflow. Submitting a proposal creates the asset (PROPOSED) plus its
 * workflow records server-side in one transaction (`POST /api/assets/propose`),
 * including the REVIEW assignment that the reviewer then sees in their
 * notifications (HU-LI11). `getReviewers` backs the form's reviewer dropdown.
 */
import { apiGet, apiPost } from "./api";
import type { Asset, ProposeRequest, ReviewerOption } from "../types/api";

/** Eligible reviewers (active ADMINISTRATIVE users) for the propose form. */
export async function getReviewers(): Promise<ReviewerOption[]> {
  return apiGet<ReviewerOption[]>("/api/assets/reviewers");
}

/** Propose an asset for review. Returns the created (PROPOSED) asset. */
export async function proposeAsset(data: ProposeRequest): Promise<Asset> {
  return apiPost<Asset, ProposeRequest>("/api/assets/propose", data);
}
