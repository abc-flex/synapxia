/**
 * notifications — workflow-notifications service (HU-LI11): the read/transition
 * side of the header bell (REVIEW/MODIFICATION/PUBLICATION/REJECTION).
 *
 *   GET  /api/actions/notifications               → open items (newest first)
 *   GET  /api/actions/reviews                      → open REVIEW items only
 *   GET  /api/actions/modifications                → open MODIFICATION items only
 *   POST /api/actions/notifications/{id}/notified → ASSIGNED → NOTIFIED (un-bold)
 *   POST /api/actions/notifications/{id}/dismiss  → insert FINISHED (remove;
 *     REVIEW/MODIFICATION reject this — they must be resolved, not dismissed)
 * The current user comes from the JWT — no user id is sent. No new table.
 *
 * The bell UI (list/click/dismiss/badge) lives in the Svelte island
 * `components/svelte/NotificationBell.svelte` (mounted from NotificationMenu.astro).
 * The persistent queue pages (`/lib/review_requests`, `/lib/modifications`) use the
 * `getReviewRequests`/`getPendingModifications` variants below so a reviewer's/
 * proposer's open work stays reachable even after the matching bell entry is gone.
 */
import { apiGet, apiPost } from "./api";
import type { NotificationItem } from "@/types/api";

/** The current user's open workflow notifications (newest first, all types). */
export async function getNotifications(): Promise<NotificationItem[]> {
  return apiGet<NotificationItem[]>("/api/actions/notifications");
}

/** The current user's open REVIEW assignments (newest first). */
export async function getReviewRequests(): Promise<NotificationItem[]> {
  return apiGet<NotificationItem[]>("/api/actions/reviews");
}

/** The current user's open MODIFICATION assignments (newest first). */
export async function getPendingModifications(): Promise<NotificationItem[]> {
  return apiGet<NotificationItem[]>("/api/actions/modifications");
}

/** Mark an ASSIGNED notification as seen (NOTIFIED). */
export async function markNotified(id: number): Promise<unknown> {
  return apiPost<unknown, Record<string, never>>(
    `/api/actions/notifications/${encodeURIComponent(String(id))}/notified`, {});
}

/** Dismiss a notification (insert FINISHED → removed from the list). */
export async function dismissNotification(id: number): Promise<unknown> {
  return apiPost<unknown, Record<string, never>>(
    `/api/actions/notifications/${encodeURIComponent(String(id))}/dismiss`, {});
}
