/**
 * notifications — the data layer for asset workflow requests.
 *
 *   GET  /api/actions/requests                        → everything I took part in
 *   GET  /api/actions/notifications                   → just what awaits ME
 *   POST /api/actions/notifications/{id}/acknowledge  → I've read this outcome
 *
 * The current user comes from the JWT — no user id is sent. No new table.
 *
 * Two surfaces, two projections of the same data, never two copies:
 *   - `MyAssetRequests.svelte` (/lib/my_asset_requests) lists EVERY asset the
 *     caller took part in, open and closed, and says whose turn each one is.
 *   - `NotificationBell.svelte` shows the strict subset awaiting the caller.
 *
 * There is no "mark as seen" call. Opening something is not resolving it, and
 * read state is a per-device concern that never reaches the server — which is
 * why the bell can no longer show you something you have already dealt with,
 * and why nothing can be cleared without actually being resolved.
 *
 * Live refresh (polling, focus, bfcache) lives in `lib/notificationsStore.ts`;
 * this module stays a thin service layer.
 */
import { apiGet, apiPost } from "./api";
import type { AssetRequest, NotificationFeed } from "@/types/api";

/** Everything the current user has taken part in, one entry per asset.
 *  `state` selects the view: `PENDING` (still in motion) or `HANDLED`. */
export async function getAssetRequests(
  state: "PENDING" | "HANDLED" = "PENDING",
  skip = 0,
  limit = 50,
): Promise<AssetRequest[]> {
  const qs = new URLSearchParams({
    state,
    skip: String(skip),
    limit: String(limit),
  });
  return apiGet<AssetRequest[]>(`/api/actions/requests?${qs}`);
}

/** The requests still awaiting the current user, plus the outstanding total. */
export async function getNotifications(limit = 5): Promise<NotificationFeed> {
  return apiGet<NotificationFeed>(
    `/api/actions/notifications?limit=${encodeURIComponent(String(limit))}`);
}

/** Acknowledge an outcome notice — the caller has read it, so it is handled.
 *  Only PUBLICATION/REJECTION qualify; a REVIEW/MODIFICATION returns 400,
 *  because those are resolved by reviewing or resubmitting, not by reading. */
export async function acknowledgeNotification(id: number): Promise<unknown> {
  return apiPost<unknown, Record<string, never>>(
    `/api/actions/notifications/${encodeURIComponent(String(id))}/acknowledge`, {});
}
