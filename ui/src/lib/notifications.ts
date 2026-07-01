/**
 * notifications — workflow-notifications service (HU-LI11): the read/transition
 * side of the header bell (REVIEW/MODIFICATION/PUBLICATION/REJECTION).
 *
 *   GET  /api/actions/notifications               → open items (newest first)
 *   POST /api/actions/notifications/{id}/notified → ASSIGNED → NOTIFIED (un-bold)
 *   POST /api/actions/notifications/{id}/dismiss  → insert FINISHED (remove)
 * The current user comes from the JWT — no user id is sent. No new table.
 *
 * The bell UI (list/click/dismiss/badge) now lives in the Svelte island
 * `components/svelte/NotificationBell.svelte` (mounted from NotificationMenu.astro);
 * this module is just the data layer it consumes.
 */
import { apiGet, apiPost } from "./api";
import type { NotificationItem } from "@/types/api";

/** The current user's open workflow notifications (newest first). */
export async function getNotifications(): Promise<NotificationItem[]> {
  return apiGet<NotificationItem[]>("/api/actions/notifications");
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
