/**
 * review — the asset review service (HU-Review). A reviewer's decision on a
 * PROPOSED asset posts to `POST /api/assets/{id}/review`, which in one
 * transaction closes the reviewer's REVIEW assignment, sets the asset status
 * (PUBLISHED / REJECTED / FEEDBACK), and notifies the proposer
 * (PUBLICATION / REJECTION / MODIFICATION) with the feedback. Backs the
 * `/lib/review` page.
 */
import { apiPost } from "./api";
import type { Asset, ReviewDecision, ReviewRequest } from "../types/api";

/** Record a reviewer's decision on an asset; returns the updated asset. */
export async function reviewAsset(
  assetId: number,
  decision: ReviewDecision,
  feedback?: string,
): Promise<Asset> {
  return apiPost<Asset, ReviewRequest>(
    `/api/assets/${encodeURIComponent(String(assetId))}/review`,
    { decision, feedback: feedback || undefined },
  );
}
