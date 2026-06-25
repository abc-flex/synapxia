/**
 * notifications — the workflow notifications feature (HU-LI11): the header bell
 * menu listing the current user's open assignments (REVIEW/MODIFICATION/
 * PUBLICATION/REJECTION), per docs/user-stories/lib-status.md.
 *
 * Backed by the read/transition side of the Asset Action Service:
 *   GET  /api/actions/notifications              → open items (newest first)
 *   POST /api/actions/notifications/{id}/notified → ASSIGNED → NOTIFIED (un-bold)
 *   POST /api/actions/notifications/{id}/dismiss  → insert FINISHED (remove)
 * The current user comes from the JWT — no user id is sent. No new table.
 *
 * Scope note: per the roadmap, the propose/review workflow that *generates*
 * assignments (HU-Review/Modify/Show-Action) isn't built yet, and those
 * destination views don't exist — so clicking an item marks it seen
 * (ASSIGNED→NOTIFIED) in place rather than navigating. Asset names are rendered
 * with `textContent` (XSS-safe), mirroring the foro/history renderers.
 */
import { apiGet, apiPost } from "./api";
import { formatRelative } from "./datatable";
import { translate } from "@/utils/i18nClient";
import type { NotificationItem } from "@/types/api";

// ── Service ──────────────────────────────────────────────────────────────────

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

// ── Controller (hydrates the header NotificationMenu) ─────────────────────────

const tr = (key: string, fallback: string): string => {
  try {
    const v = translate(key);
    if (v && v !== key) return v;
  } catch {
    /* non-fatal */
  }
  return fallback;
};

const locale = (): string =>
  (typeof localStorage !== "undefined" && localStorage.getItem("lang")) || "en";

const typeLabel = (type: string): string =>
  tr(`notifications.type.${type}`, type.charAt(0) + type.slice(1).toLowerCase());

/**
 * Mount the header notifications menu. Self-contained: finds its own elements by
 * `data-notif-*` hooks, fetches the current user's notifications, renders them,
 * and wires click (mark seen) + dismiss. Safe to call on every page — it no-ops
 * when the menu isn't present (e.g. unauthenticated layouts).
 */
export function mountNotifications(): void {
  if (typeof window === "undefined") return;

  const root = document.querySelector<HTMLElement>("[data-notif-root]");
  if (!root) return;

  const listEl = root.querySelector<HTMLElement>("[data-notif-list]");
  const emptyEl = root.querySelector<HTMLElement>("[data-notif-empty]");
  const dotEl = root.querySelector<HTMLElement>("[data-notif-dot]");
  const countEl = root.querySelector<HTMLElement>("[data-notif-count]");
  if (!listEl) return;

  let items: NotificationItem[] = [];

  function paintBadge() {
    const n = items.length;
    if (dotEl) dotEl.classList.toggle("hidden", n === 0);
    if (countEl) {
      countEl.textContent = n > 0 ? String(n) : "";
      countEl.classList.toggle("hidden", n === 0);
    }
  }

  function itemNode(it: NotificationItem): HTMLElement {
    const article = document.createElement("article");
    article.className = "notification-item";
    article.dataset.notifId = String(it.id);
    if (it.unread) article.dataset.unread = "1";

    const body = document.createElement("div");
    body.className = "notification-body";

    const title = document.createElement("p");
    title.className = it.unread ? "notification-title font-bold" : "notification-title";
    title.textContent = it.asset_name || `#${it.asset}`;

    const meta = document.createElement("p");
    meta.className = "notification-meta";
    meta.textContent = `${typeLabel(it.type)} · ${formatRelative(it.created_at, locale())}`;

    body.append(title, meta);
    article.appendChild(body);

    // Dismiss control — only for NOTIFIED (seen) items, per HU-Notifications.
    if (!it.unread) {
      const del = document.createElement("button");
      del.type = "button";
      del.dataset.notifDismiss = String(it.id);
      del.className =
        "ml-auto shrink-0 rounded-md px-2 py-1 text-xs font-medium text-gray-400 hover:text-red-600 dark:hover:text-red-400";
      del.textContent = tr("notifications.dismiss", "Dismiss");
      del.title = tr("notifications.dismiss", "Dismiss");
      article.appendChild(del);
    }
    return article;
  }

  function render() {
    if (!listEl) return;
    listEl.innerHTML = "";
    if (emptyEl) emptyEl.classList.toggle("hidden", items.length > 0);
    for (const it of items) listEl.appendChild(itemNode(it));
    paintBadge();
  }

  async function load() {
    try {
      items = await getNotifications();
    } catch {
      items = []; // unauthenticated / offline → show nothing rather than fake data
    }
    render();
  }

  // Click a row → mark seen (ASSIGNED→NOTIFIED) in place; dismiss button → remove.
  root.addEventListener("click", async (e) => {
    const target = e.target as HTMLElement;

    const dismissBtn = target.closest<HTMLElement>("[data-notif-dismiss]");
    if (dismissBtn) {
      e.preventDefault();
      e.stopPropagation();
      const id = Number(dismissBtn.dataset.notifDismiss);
      items = items.filter((i) => i.id !== id); // optimistic
      render();
      try {
        await dismissNotification(id);
      } catch {
        (window as any).showToast?.(
          tr("notifications.error", "Could not update the notification"), "error");
        await load(); // re-sync on failure
      }
      return;
    }

    const article = target.closest<HTMLElement>("[data-notif-id]");
    if (article && article.dataset.unread === "1") {
      const id = Number(article.dataset.notifId);
      try {
        await markNotified(id);
        await load(); // refresh (item un-bolds, gains a dismiss control)
      } catch {
        (window as any).showToast?.(
          tr("notifications.error", "Could not update the notification"), "error");
      }
    }
  });

  void load();
}
