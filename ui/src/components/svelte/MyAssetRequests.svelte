<script lang="ts">
  /**
   * MyAssetRequests — the durable record of everything the caller has taken part
   * in: requests directed at them AND assets they proposed, open and closed.
   *
   * Two things this page does that the header bell deliberately does not:
   *
   *   - It shows work waiting on SOMEBODY ELSE. An asset you proposed and are
   *     waiting on a reviewer for is listed here (marked as such) and is absent
   *     from the bell, because nothing is being asked of you. "Pending"
   *     describes the request, not an obligation on the viewer — which is why
   *     every row states whose turn it is.
   *   - It keeps history. Resolving something moves it to the Handled view; it
   *     is never erased.
   *
   * One row per asset, never one per workflow event: an asset you proposed and
   * whose outcome you later acknowledged must appear once, or this page would
   * reintroduce the very duplication the redesign exists to remove.
   *
   * It is an island rather than a server-rendered table because an SSR snapshot
   * is stale the moment anything changes — the exact defect being fixed.
   */
  import { onMount } from "svelte";
  import { subscribe, start, notifyChanged } from "@/lib/notificationsStore";
  import { acknowledgeNotification } from "@/lib/notifications";
  import { formatDate } from "@/lib/datatable";
  import { translate } from "@/utils/i18nClient";
  import { showToast } from "@/lib/toast";
  import type { AssetRequest } from "@/types/api";

  let pending = $state<AssetRequest[]>([]);
  let handled = $state<AssetRequest[]>([]);
  let loaded = $state(false);
  let langTick = $state(0);
  // The selected view is local state, so a background refresh never yanks the
  // user back to the other tab mid-read.
  let view = $state<"PENDING" | "HANDLED">("PENDING");
  let busy = $state<number | null>(null);

  const rows = $derived(view === "PENDING" ? pending : handled);

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

  const kindLabel = (r: AssetRequest): string => {
    if (r.pending_action_type) {
      return t(`notifications.type.${r.pending_action_type}`, r.pending_action_type);
    }
    if (r.roles.includes("PROPOSER")) {
      return t("my_asset_requests.role_proposer", "Proposed by me");
    }
    if (r.roles.includes("REVIEWER")) {
      return t("my_asset_requests.role_reviewer", "Reviewed by me");
    }
    return "—";
  };

  /** Only outcome notices can be acknowledged; a review is resolved by deciding
   *  it, which happens on the review screen. */
  const canAcknowledge = (r: AssetRequest): boolean =>
    r.awaited_party === "SELF" &&
    (r.pending_action_type === "PUBLICATION" || r.pending_action_type === "REJECTION");

  function hrefFor(r: AssetRequest): string | null {
    if (r.awaited_party !== "SELF" || r.pending_action_id == null) return null;
    const id = encodeURIComponent(String(r.pending_action_id));
    if (r.pending_action_type === "REVIEW") return `/lib/review?action=${id}`;
    if (r.pending_action_type === "MODIFICATION") return `/lib/modify?action=${id}`;
    return `/lib/show-action?action=${id}`;
  }

  async function acknowledge(r: AssetRequest): Promise<void> {
    if (r.pending_action_id == null || busy !== null) return;
    busy = r.pending_action_id;
    try {
      await acknowledgeNotification(r.pending_action_id);
      // One announcement updates this page and the header bell together.
      notifyChanged();
    } catch {
      showToast(
        t("my_asset_requests.acknowledge_error", "Could not acknowledge this notice"),
        "error",
      );
    } finally {
      busy = null;
    }
  }

  onMount(() => {
    const onLang = () => (langTick += 1);
    window.addEventListener("languageChanged", onLang);

    const unsubscribe = subscribe((s) => {
      pending = s.pending;
      handled = s.handled;
      loaded = s.loaded;
    });
    start();

    return () => {
      window.removeEventListener("languageChanged", onLang);
      unsubscribe();
    };
  });
</script>

<div class="mb-4 flex gap-1 border-b border-gray-200 dark:border-gray-800">
  {#each [["PENDING", "my_asset_requests.tab_pending", "Pending"], ["HANDLED", "my_asset_requests.tab_handled", "Handled"]] as [key, i18nKey, fallback] (key)}
    <button
      type="button"
      class="-mb-px border-b-2 px-4 py-2 text-sm font-medium transition
             {view === key
               ? 'border-indigo-600 text-indigo-600 dark:border-indigo-400 dark:text-indigo-400'
               : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'}"
      aria-current={view === key ? "page" : undefined}
      onclick={() => (view = key as "PENDING" | "HANDLED")}
    >
      {t(i18nKey, fallback)}
      <span class="ml-1 text-xs text-gray-400">
        ({key === "PENDING" ? pending.length : handled.length})
      </span>
    </button>
  {/each}
</div>

{#if !loaded}
  <p class="py-6 text-sm text-gray-400 dark:text-gray-500">
    {t("common.loading", "Loading…")}
  </p>
{:else if rows.length === 0}
  <div class="rounded-xl p-4">
    <p class="text-sm text-gray-500 dark:text-gray-400">
      {view === "PENDING"
        ? t("my_asset_requests.empty_pending", "You have no asset requests in progress.")
        : t("my_asset_requests.empty_handled", "Nothing has been handled yet.")}
    </p>
  </div>
{:else}
  <div class="overflow-x-auto rounded-xl border border-gray-200 dark:border-gray-800">
    <table class="w-full text-left text-sm">
      <thead class="border-b border-gray-300 bg-gray-100 text-xs uppercase text-gray-700 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300">
        <tr>
          <th class="px-4 py-2 font-semibold tracking-wide">{t("my_asset_requests.col_asset", "Asset")}</th>
          <th class="px-4 py-2 font-semibold tracking-wide">{t("my_asset_requests.col_kind", "Request")}</th>
          <th class="px-4 py-2 font-semibold tracking-wide">{t("my_asset_requests.col_status", "Asset status")}</th>
          {#if view === "PENDING"}
            <th class="px-4 py-2 font-semibold tracking-wide">{t("my_asset_requests.col_awaiting", "Waiting on")}</th>
          {/if}
          <th class="px-4 py-2 font-semibold tracking-wide">{t("my_asset_requests.col_updated", "Updated")}</th>
          <th class="px-4 py-2 font-semibold tracking-wide"></th>
        </tr>
      </thead>
      <tbody class="[&>tr:nth-child(even)]:bg-gray-50 [&>tr:hover]:bg-gray-100 dark:[&>tr:nth-child(even)]:bg-gray-800/40 dark:[&>tr:hover]:bg-gray-800/70">
        {#each rows as r (r.asset)}
          <tr class="border-b border-gray-200 dark:border-gray-800">
            <td class="px-4 py-2 font-medium text-gray-900 dark:text-white/90">
              {r.asset_name || `#${r.asset}`}
            </td>
            <td class="px-4 py-2 text-gray-600 dark:text-gray-300">{kindLabel(r)}</td>
            <td class="px-4 py-2 text-gray-600 dark:text-gray-300">
              {r.asset_status ? t(`asset_status.${r.asset_status}`, r.asset_status) : "—"}
            </td>
            {#if view === "PENDING"}
              <td class="px-4 py-2">
                <span
                  class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium
                         {r.awaited_party === 'SELF'
                           ? 'bg-amber-100 text-amber-800 dark:bg-amber-500/20 dark:text-amber-300'
                           : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300'}"
                >
                  {r.awaited_party === "SELF"
                    ? t("my_asset_requests.awaiting_you", "You")
                    : t("my_asset_requests.awaiting_other", "Someone else")}
                </span>
              </td>
            {/if}
            <td class="px-4 py-2 text-gray-500 dark:text-gray-400">
              {formatDate(r.last_change_at, locale())}
            </td>
            <td class="px-4 py-2 text-right whitespace-nowrap">
              {#if canAcknowledge(r)}
                <button
                  type="button"
                  class="inline-flex items-center rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
                  disabled={busy === r.pending_action_id}
                  onclick={() => acknowledge(r)}
                >
                  {t("my_asset_requests.acknowledge", "Got it")}
                </button>
              {:else if hrefFor(r)}
                <a
                  href={hrefFor(r)}
                  class="inline-flex items-center rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700"
                >
                  {t("my_asset_requests.open_action", "Open")}
                </a>
              {/if}
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
{/if}
