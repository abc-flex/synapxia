/**
 * modify — the asset resubmit service (HU-Modify). After a reviewer requests
 * changes, the proposer edits the asset + its characterizations and resubmits.
 * A single `POST /api/assets/{id}/resubmit` applies the edits, closes the
 * proposer's MODIFICATION assignment, flips the asset back to PROPOSED, and
 * re-arms the original reviewer (REVIEW/ASSIGNED). Backs the `/lib/modify` page.
 */
import { apiPost } from "./api";
import type { Asset, ModifyRequest } from "../types/api";

/** Resubmit an asset for re-review with the proposer's edits; returns the asset. */
export async function resubmitAsset(
  assetId: number,
  data: ModifyRequest,
): Promise<Asset> {
  return apiPost<Asset, ModifyRequest>(
    `/api/assets/${encodeURIComponent(String(assetId))}/resubmit`,
    data,
  );
}
