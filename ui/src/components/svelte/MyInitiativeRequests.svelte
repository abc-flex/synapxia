<script lang="ts">
  /**
   * MyInitiativeRequests — the durable record of every initiative the caller
   * has taken part in (HU-IN14, specs/005-explore-initiatives): diagnoses and
   * change requests directed at them AND initiatives they proposed, open and
   * closed. The structural twin of MyAssetRequests.svelte over
   * `collaborations`.
   *
   * One row per initiative; every in-motion row states whose turn it is. The
   * header bell's Initiatives tab is a strict subset (only rows awaiting the
   * caller). State comes from the shared notifications store.
   */
  import { onMount } from "svelte";
  import { subscribe, start, notifyChanged } from "@/lib/notificationsStore";
  import { acknowledgeCollaboration } from "@/lib/collaborations";
  import { getListItemsbyList } from "@/lib/list_items";
  import { formatDate } from "@/lib/datatable";
  import { translate } from "@/utils/i18nClient";
  import { showToast } from "@/lib/toast";
  import type { InitiativeRequest } from "@/types/api";

  let pending = $state<InitiativeRequest[]>([]);
  let handled = $state<InitiativeRequest[]>([]);
  let loaded = $state(false);
  let langTick = $state(0);
  let view = $state<"PENDING" | "HANDLED">("PENDING");
  let busy = $state<number | null>(null);
  let statusItems = $state<{ lang: string; value: string; label: string }[]>([]);

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

  const statusLabel = (value?: string | null): string => {
    void langTick;
    if (!value) return "—";
    const lang = locale().startsWith("es") ? "es" : "en";
    return (
      statusItems.find((i) => i.value === value && i.lang === lang)?.label ??
      statusItems.find((i) => i.value === value && i.lang === "en")?.label ??
      value
    );
  };

  const kindLabel = (r: InitiativeRequest): string => {
    if (r.pending_collab_type) {
      return t(`inits_notifications.type.${r.pending_collab_type}`, r.pending_collab_type);
    }
    if (r.roles.includes("PROPOSER")) return t("my_initiative_requests.role_proposer", "Proposed by me");
    if (r.roles.includes("REVIEWER")) return t("my_initiative_requests.role_reviewer", "Diagnosed by me");
    return "—";
  };

  /** Whose turn, when it is somebody else's: the stage the initiative is in. */
  const stageLabel = (r: InitiativeRequest): string => {
    if (r.init_status === "ACTIVATED") return t("my_initiative_requests.stage_diagnosis", "Waiting for diagnosis");
    if (r.init_status === "FEEDBACK") return t("my_initiative_requests.stage_modification", "Waiting for changes");
    return "";
  };

  /** Only outcome notices can be acknowledged; a diagnosis or change request
   *  is resolved on its own page. */
  const canAcknowledge = (r: InitiativeRequest): boolean =>
    r.awaited_party === "SELF" &&
    (r.pending_collab_type === "ACCEPTANCE" || r.pending_collab_type === "REJECTION");

  function hrefFor(r: InitiativeRequest): string | null {
    if (r.awaited_party !== "SELF" || r.pending_collab_id == null) return null;
    const id = encodeURIComponent(String(r.pending_collab_id));
    if (r.pending_collab_type === "DIAGNOSIS") return `/inits/diagnose?collab=${id}`;
    if (r.pending_collab_type === "MODIFICATION") return `/inits/modify?collab=${id}`;
    return `/inits/show-collab?collab=${id}`;
  }

  async function acknowledge(r: InitiativeRequest): Promise<void> {
    if (r.pending_collab_id == null || busy !== null) return;
    busy = r.pending_collab_id;
    try {
      await acknowledgeCollaboration(r.pending_collab_id);
      notifyChanged(); // updates this page and the header bell together
    } catch {
      showToast(t("my_initiative_requests.acknowledge_error", "Could not acknowledge this notice"), "error");
    } finally {
      busy = null;
    }
  }

  onMount(() => {
    const onLang = () => (langTick += 1);
    window.addEventListener("languageChanged", onLang);
    getListItemsbyList("INITIATIVE_STATUS", 0, 100)
      .then((items) => (statusItems = items as any))
      .catch(() => {});

    const unsubscribe = subscribe((s) => {
      pending = s.initPending;
      handled = s.initHandled;
      loaded = s.initLoaded;
    });
    start();

    return () => {
      window.removeEventListener("languageChanged", onLang);
      unsubscribe();
    };
  });
</script>

<div class="mb-4 flex gap-1 border-b border-gray-200 dark:border-gray-800">
  {#each [["PENDING", "my_initiative_requests.tab_pending", "Pending"], ["HANDLED", "my_initiative_requests.tab_handled", "Handled"]] as [key, i18nKey, fallback] (key)}
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
  <p class="py-6 text-sm text-gray-400 dark:text-gray-500">{t("common.loading", "Loading…")}</p>
{:else if rows.length === 0}
  <div class="rounded-xl p-4">
    <p class="text-sm text-gray-500 dark:text-gray-400">
      {view === "PENDING"
        ? t("my_initiative_requests.empty_pending", "You have no initiative requests in progress.")
        : t("my_initiative_requests.empty_handled", "Nothing has been handled yet.")}
    </p>
  </div>
{:else}
  <div class="overflow-x-auto rounded-xl border border-gray-200 dark:border-gray-800">
    <table class="w-full text-left text-sm">
      <thead class="border-b border-gray-300 bg-gray-100 text-xs uppercase text-gray-700 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300">
        <tr>
          <th class="px-4 py-2 font-semibold tracking-wide">{t("my_initiative_requests.col_initiative", "Initiative")}</th>
          <th class="px-4 py-2 font-semibold tracking-wide">{t("my_initiative_requests.col_kind", "Request")}</th>
          <th class="px-4 py-2 font-semibold tracking-wide">{t("my_initiative_requests.col_status", "Initiative status")}</th>
          {#if view === "PENDING"}
            <th class="px-4 py-2 font-semibold tracking-wide">{t("my_initiative_requests.col_awaiting", "Waiting on")}</th>
          {/if}
          <th class="px-4 py-2 font-semibold tracking-wide">{t("my_initiative_requests.col_updated", "Updated")}</th>
          <th class="px-4 py-2 font-semibold tracking-wide"></th>
        </tr>
      </thead>
      <tbody class="[&>tr:nth-child(even)]:bg-gray-50 [&>tr:hover]:bg-gray-100 dark:[&>tr:nth-child(even)]:bg-gray-800/40 dark:[&>tr:hover]:bg-gray-800/70">
        {#each rows as r (r.init)}
          <tr class="border-b border-gray-200 dark:border-gray-800">
            <td class="px-4 py-2 font-medium text-gray-900 dark:text-white/90">{r.init_name || `#${r.init}`}</td>
            <td class="px-4 py-2 text-gray-600 dark:text-gray-300">{kindLabel(r)}</td>
            <td class="px-4 py-2 text-gray-600 dark:text-gray-300">{statusLabel(r.init_status)}</td>
            {#if view === "PENDING"}
              <td class="px-4 py-2">
                <span
                  class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium
                         {r.awaited_party === 'SELF'
                           ? 'bg-amber-100 text-amber-800 dark:bg-amber-500/20 dark:text-amber-300'
                           : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300'}"
                >
                  {r.awaited_party === "SELF"
                    ? t("my_initiative_requests.awaiting_you", "You")
                    : t("my_initiative_requests.awaiting_other", "Someone else")}
                </span>
                {#if r.awaited_party !== "SELF" && stageLabel(r)}
                  <span class="ml-1 text-xs text-gray-500 dark:text-gray-400">· {stageLabel(r)}</span>
                {/if}
              </td>
            {/if}
            <td class="px-4 py-2 text-gray-500 dark:text-gray-400">{formatDate(r.last_change_at, locale())}</td>
            <td class="px-4 py-2 text-right whitespace-nowrap">
              {#if canAcknowledge(r)}
                <button
                  type="button"
                  class="inline-flex items-center rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
                  disabled={busy === r.pending_collab_id}
                  onclick={() => acknowledge(r)}
                >
                  {t("my_initiative_requests.acknowledge", "Got it")}
                </button>
              {:else if hrefFor(r)}
                <a
                  href={hrefFor(r)}
                  class="inline-flex items-center rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700"
                >
                  {t("my_initiative_requests.open_action", "Open")}
                </a>
              {/if}
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
{/if}
