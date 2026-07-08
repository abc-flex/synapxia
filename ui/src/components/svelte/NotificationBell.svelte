<script lang="ts">
  /**
   * NotificationBell — the header workflow-notifications bell (HU-LI11) as a
   * Svelte island. Second Svelte migration after ShowAction. Keeps the native
   * `<details>` disclosure + the global `.notification-*` classes so the look is
   * unchanged; reuses the existing services (getNotifications / markNotified /
   * dismissNotification) and `translate()` i18n. Mounted manually (see
   * NotificationMenu.astro) — not the @astrojs/svelte island mechanism.
   */
  import { onMount } from "svelte";
  import { getNotifications, markNotified, dismissNotification } from "@/lib/notifications";
  import { formatRelative } from "@/lib/datatable";
  import { isAuthenticated } from "@/lib/auth";
  import { translate } from "@/utils/i18nClient";
  import { showToast } from "@/lib/toast";
  import BellIcon from "@/images/icons/bell.svg?raw";
  import type { NotificationItem } from "@/types/api";

  let items = $state<NotificationItem[]>([]);
  let detailsEl = $state<HTMLDetailsElement | undefined>(undefined);
  let langTick = $state(0); // bump on language switch → re-localize labels

  const count = $derived(items.length);

  const t = (key: string, fallback: string): string => {
    void langTick;
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
  const typeLabel = (ty: string): string =>
    t(`notifications.type.${ty}`, ty.charAt(0) + ty.slice(1).toLowerCase());

  async function load(): Promise<void> {
    // Only a real logged-in user's bell should hit the API (see lib/notifications).
    if (!isAuthenticated()) {
      items = [];
      return;
    }
    try {
      items = await getNotifications();
    } catch {
      items = [];
    }
  }

  // Click a row → open the matching user story (HU-Notifications).
  async function onItemClick(it: NotificationItem): Promise<void> {
    if (it.type === "PUBLICATION" || it.type === "REJECTION") {
      window.location.href = `/lib/show-action?action=${encodeURIComponent(String(it.id))}`;
      return;
    }
    if (it.type === "REVIEW") {
      // Reviewer's queue → the Review page (it marks the notification seen on open).
      window.location.href = `/lib/review?action=${encodeURIComponent(String(it.id))}`;
      return;
    }
    if (it.type === "MODIFICATION") {
      // Proposer's "edit after changes" flow (HU-Modify); the Modify page marks
      // the notification seen on open.
      window.location.href = `/lib/modify?action=${encodeURIComponent(String(it.id))}`;
      return;
    }
    // Unknown type → just mark it seen.
    if (it.unread) {
      try {
        await markNotified(it.id);
        await load();
      } catch {
        showToast(t("notifications.error", "Could not update the notification"), "error");
      }
    }
  }

  async function onDismiss(it: NotificationItem, e: Event): Promise<void> {
    e.preventDefault();
    e.stopPropagation();
    items = items.filter((i) => i.id !== it.id); // optimistic
    try {
      await dismissNotification(it.id);
    } catch {
      showToast(t("notifications.error", "Could not update the notification"), "error");
      await load(); // re-sync on failure
    }
  }

  onMount(() => {
    const onLang = () => (langTick += 1);
    window.addEventListener("languageChanged", onLang);
    void load();
    return () => window.removeEventListener("languageChanged", onLang);
  });
</script>

<details class="notification-menu relative" aria-label="Notifications" bind:this={detailsEl}>
  <summary class="notification-trigger group">
    {#if count > 0}
      <span class="notify-dot" aria-hidden="true"><span class="notify-ping"></span></span>
    {/if}
    {@html BellIcon}
  </summary>

  <div class="notification-dropdown">
    <div class="flex items-center justify-between pb-3">
      <h3 class="text-lg font-semibold text-gray-900 dark:text-white/90">
        <span>{t("notification_menu.title", "Notifications")}</span>
        {#if count > 0}
          <span class="ml-1 rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-semibold text-indigo-700 dark:bg-indigo-500/20 dark:text-indigo-300">{count}</span>
        {/if}
      </h3>
      <button
        class="text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
        type="button"
        onclick={() => detailsEl?.removeAttribute("open")}
      >✕</button>
    </div>

    <div class="notification-list custom-scrollbar">
      {#each items as it (it.id)}
        <div
          class="notification-item cursor-pointer"
          role="button"
          tabindex="0"
          onclick={() => onItemClick(it)}
          onkeydown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onItemClick(it); } }}
        >
          <div class="notification-body">
            <p class={it.unread ? "notification-title font-bold" : "notification-title"}>
              {it.asset_name || `#${it.asset}`}
            </p>
            <p class="notification-meta">{typeLabel(it.type)} · {formatRelative(it.created_at, locale())}</p>
          </div>
          {#if !it.unread && (it.type === "PUBLICATION" || it.type === "REJECTION")}
            <!-- Only informational types can be dismissed. REVIEW/MODIFICATION
                 must be resolved via review/resubmit — dismissing them would
                 insert the same FINISHED row that marks the assignment as
                 already decided, permanently blocking the assignee from
                 acting on it. Those stay reachable via the "Review Requests" /
                 "My Modifications" pages instead. -->
            <button
              type="button"
              class="ml-auto shrink-0 rounded-md px-2 py-1 text-xs font-medium text-gray-400 hover:text-red-600 dark:hover:text-red-400"
              title={t("notifications.dismiss", "Dismiss")}
              onclick={(e) => onDismiss(it, e)}
            >{t("notifications.dismiss", "Dismiss")}</button>
          {/if}
        </div>
      {/each}
    </div>

    {#if count === 0}
      <p class="py-6 text-center text-sm text-gray-400 dark:text-gray-500">
        {t("notifications.empty", "You're all caught up.")}
      </p>
    {/if}
  </div>
</details>
