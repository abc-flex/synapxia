<script lang="ts">
  /**
   * NotificationBell — the header attention feed.
   *
   * Shows ONLY what still awaits the caller. Anything waiting on somebody else
   * (an asset they proposed, say) is deliberately absent, because nothing is
   * being asked of them — that belongs on the requests page, which this panel
   * links to. The bell is a strict subset of that page, never a second copy of
   * it; showing the same list twice was the duplication this redesign removes.
   *
   * There is no dismiss control. An item leaves this list by being resolved —
   * a review decided, changes resubmitted, an outcome acknowledged — and by
   * nothing else. The old dismiss wrote the same terminal row that means
   * "already decided", so hiding an unresolved assignment silently revoked the
   * assignee's ability to act on it.
   *
   * State comes from the shared store, so the panel and the requests page can
   * never disagree, and both stay current without a manual reload.
   */
  import { onMount } from "svelte";
  import { subscribe, start } from "@/lib/notificationsStore";
  import { formatRelative } from "@/lib/datatable";
  import { translate } from "@/utils/i18nClient";
  import BellIcon from "@/images/icons/bell.svg?raw";
  import type { NotificationItem } from "@/types/api";

  /** How many entries the panel renders before deferring to "view all". */
  const MAX_SHOWN = 5;

  let items = $state<NotificationItem[]>([]);
  let total = $state(0);
  let detailsEl = $state<HTMLDetailsElement | undefined>(undefined);
  let langTick = $state(0); // bump on language switch → re-localize labels

  const hidden = $derived(Math.max(0, total - items.length));

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

  /** Every entry here awaits the caller, so each one has a screen to act on. */
  function hrefFor(it: NotificationItem): string {
    const id = encodeURIComponent(String(it.id));
    if (it.type === "REVIEW") return `/lib/review?action=${id}`;
    if (it.type === "MODIFICATION") return `/lib/modify?action=${id}`;
    // PUBLICATION / REJECTION are outcomes: read and acknowledge.
    return `/lib/show-action?action=${id}`;
  }

  function onItemClick(it: NotificationItem): void {
    window.location.href = hrefFor(it);
  }

  // Close on an outside click — a native <details> only closes via its own
  // summary or Esc (mirrors the account menu and SearchPalette).
  function onDocumentClick(e: MouseEvent): void {
    if (detailsEl?.open && !detailsEl.contains(e.target as Node)) {
      detailsEl.removeAttribute("open");
    }
  }

  onMount(() => {
    const onLang = () => (langTick += 1);
    window.addEventListener("languageChanged", onLang);
    document.addEventListener("mousedown", onDocumentClick);

    // This island only ever mounts inside BaseLayout, which the Astro
    // middleware already gates on the auth cookie — by the time we're here the
    // caller is authenticated, so no client-side auth check is needed.
    const unsubscribe = subscribe((s) => {
      items = s.feed.items.slice(0, MAX_SHOWN);
      total = s.feed.total;
    });
    start();

    return () => {
      window.removeEventListener("languageChanged", onLang);
      document.removeEventListener("mousedown", onDocumentClick);
      unsubscribe();
    };
  });
</script>

<details class="notification-menu relative" aria-label="Notifications" bind:this={detailsEl}>
  <summary class="notification-trigger group">
    {#if total > 0}
      <span class="notify-dot" aria-hidden="true"><span class="notify-ping"></span></span>
    {/if}
    {@html BellIcon}
  </summary>

  <div class="notification-dropdown">
    <div class="flex items-center justify-between pb-3">
      <h3 class="text-lg font-semibold text-gray-900 dark:text-white/90">
        <span>{t("notification_menu.title", "Notifications")}</span>
        {#if total > 0}
          <span class="ml-1 rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-semibold text-indigo-700 dark:bg-indigo-500/20 dark:text-indigo-300">{total}</span>
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
            <p class="notification-title font-semibold">
              {it.asset_name || `#${it.asset}`}
            </p>
            <p class="notification-meta">{typeLabel(it.type)} · {formatRelative(it.created_at, locale())}</p>
          </div>
        </div>
      {/each}
    </div>

    {#if total === 0}
      <p class="py-6 text-center text-sm text-gray-400 dark:text-gray-500">
        {t("notifications.empty", "You're all caught up.")}
      </p>
    {/if}

    <div class="mt-2 border-t border-gray-100 pt-2 dark:border-gray-800">
      {#if hidden > 0}
        <p class="px-1 pb-1 text-xs text-gray-400 dark:text-gray-500">
          {t("notifications.more_count", "and {n} more").replace("{n}", String(hidden))}
        </p>
      {/if}
      <a
        href="/lib/my_asset_requests"
        class="block rounded-lg px-1 py-1.5 text-sm font-medium text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 dark:hover:text-indigo-300"
      >
        {t("notifications.view_all", "View all my asset requests")} →
      </a>
    </div>
  </div>
</details>
