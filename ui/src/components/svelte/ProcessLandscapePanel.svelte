<script lang="ts">
  /**
   * ProcessLandscapePanel — the read-only process detail shared by the Value
   * Chain and the Process Map (specs/010-process-landscape-views, US3,
   * FR-014–FR-016).
   *
   * Compact layout (2026-10-25): a small title with an arrow to close, the
   * core fields, then Outgoing / Incoming relations, Linked assets and Linked
   * initiatives as tabs — only the tab body scrolls — and the jumps to the
   * other view and to Process Management at the bottom, each offered only
   * when the caller holds that option (`can_*` from the landscape).
   */
  import { apiErrorDetail } from "@/lib/api";
  import { listLabel } from "@/lib/listLang";
  import {
    byCode, getLandscapeDetail, landscapeText, topLevelOf, type LandscapeLists,
  } from "@/lib/processLandscape";
  import type { LandscapeProcessDetail, ProcessLandscape } from "@/types/api";

  interface Props {
    code: string;
    from: "chain" | "map";
    landscape: ProcessLandscape;
    lists: LandscapeLists;
    langTick: number;
    onClose: () => void;
  }
  let { code, from, landscape, lists, langTick, onClose }: Props = $props();

  type Tab = "outgoing" | "incoming" | "assets" | "inits";

  const t = (key: string, fallback: string, vars?: Record<string, string | number>) => {
    void langTick;
    return landscapeText("process_landscape", key, fallback, vars);
  };
  const label = (kind: keyof LandscapeLists, value: string | null | undefined) => {
    void langTick;
    return value ? listLabel(lists[kind], value) || value : "—";
  };

  let detail = $state<LandscapeProcessDetail | null>(null);
  let error = $state("");
  let loading = $state(false);
  let tab = $state<Tab>("outgoing");
  let seq = 0;

  $effect(() => {
    const wanted = code;
    const mine = ++seq;
    loading = true;
    error = "";
    getLandscapeDetail(wanted)
      .then((d) => { if (mine === seq) detail = d; })
      .catch((err) => { if (mine === seq) { detail = null; error = apiErrorDetail(err, t("detail_error", "The process details could not be loaded.")); } })
      .finally(() => { if (mine === seq) loading = false; });
  });

  const index = $derived(byCode(landscape));
  const tabs = $derived.by((): { key: Tab; short: string; full: string; count: number }[] => {
    void langTick;
    return [
      { key: "outgoing", short: t("tab_outgoing", "Outgoing"), full: t("outgoing", "Outgoing relations"), count: detail?.outgoing.length ?? 0 },
      { key: "incoming", short: t("tab_incoming", "Incoming"), full: t("incoming", "Incoming relations"), count: detail?.incoming.length ?? 0 },
      { key: "assets", short: t("tab_assets", "Assets"), full: t("linked_assets", "Linked assets"), count: detail?.assets.length ?? 0 },
      { key: "inits", short: t("tab_inits", "Initiatives"), full: t("linked_inits", "Linked initiatives"), count: detail?.inits.length ?? 0 },
    ];
  });
  const subAssets = $derived(detail ? detail.assets.filter((a) => a.via).length : 0);
  const subInits = $derived(detail ? detail.inits.filter((i) => i.via).length : 0);
  const relations = $derived(detail ? (tab === "incoming" ? detail.incoming : detail.outgoing) : []);
  const mapHref = $derived(`/proc/process_map?focus=${encodeURIComponent(code)}`);
  const chainHref = $derived(`/proc/value_chain?focus=${encodeURIComponent(topLevelOf(code, index))}`);
  const manageHref = $derived(`/proc/processes?open=${encodeURIComponent(code)}`);
  // Each linked asset / initiative opens its own read-only detail in its
  // Explore page (`?asset=` / `?initiative=`, handled by those pages).
  const assetHref = (asset: number, category?: string | null) =>
    category ? `/lib/explore?code=${encodeURIComponent(category)}&asset=${asset}` : null;
  const initHref = (init: number) => `/inits/explore?initiative=${init}`;
  const linkClass = "inline-flex items-center gap-1 font-semibold text-indigo-700 hover:underline dark:text-indigo-300";
  const showChainLink = $derived(from === "map" && landscape.can_value_chain);
  const showMapLink = $derived(from === "chain" && landscape.can_map);

  function onKey(e: KeyboardEvent) {
    if (e.key === "Escape") onClose();
  }

  function onTabKey(e: KeyboardEvent) {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    const keys = tabs.map((x) => x.key);
    const i = keys.indexOf(tab) + (e.key === "ArrowRight" ? 1 : -1);
    tab = keys[(i + keys.length) % keys.length];
    (e.currentTarget as HTMLElement).querySelector<HTMLElement>(`[data-tab="${tab}"]`)?.focus();
  }
</script>

<svelte:window onkeydown={onKey} />

<aside
  class="fixed inset-y-0 right-0 z-[60] flex w-full flex-col border-l border-gray-200 bg-white shadow-xl sm:w-[24rem] dark:border-gray-700 dark:bg-gray-900"
  aria-label={t("details", "Process details")}
>
  <!-- Title: code + process name, and an "x" to close -->
  <header class="flex items-center gap-2 border-b border-gray-200 py-3.5 pl-4 pr-3 dark:border-gray-700">
    <h2 class="flex min-w-0 flex-1 items-baseline gap-2 text-base text-gray-900 dark:text-white" title={`${code} · ${detail?.name ?? index.get(code)?.name ?? code}`}>
      <span class="shrink-0 font-mono text-sm font-bold text-indigo-600 dark:text-indigo-400">{code}</span>
      <span class="truncate font-semibold">{detail?.name ?? index.get(code)?.name ?? ""}</span>
    </h2>
    <button
      type="button"
      class="shrink-0 rounded-md p-1 text-gray-500 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-white"
      title={t("close", "Close")}
      aria-label={t("close", "Close")}
      onclick={onClose}
    >
      <svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" /></svg>
    </button>
  </header>

  {#if loading && !detail}
    <p class="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">{t("loading", "Loading…")}</p>
  {:else if error}
    <p class="px-4 py-3 text-sm text-red-600 dark:text-red-400">{error}</p>
  {:else if detail}
    <!-- Properties -->
    <section class="space-y-3 border-b border-gray-200 px-4 py-4 text-sm dark:border-gray-700">
      <dl class="grid grid-cols-[auto,1fr] gap-x-4 gap-y-2">
        <dt class="text-gray-500 dark:text-gray-400">{t("type", "Type")}</dt>
        <dd class="truncate text-gray-900 dark:text-gray-100">{label("type", detail.type)}</dd>
        <dt class="text-gray-500 dark:text-gray-400">{t("status", "Status")}</dt>
        <dd class="truncate text-gray-900 dark:text-gray-100">{label("status", detail.status)}</dd>
        <dt class="text-gray-500 dark:text-gray-400">{t("parent", "Parent process")}</dt>
        <dd class="truncate text-gray-900 dark:text-gray-100">{detail.parent ? `${detail.parent_name ?? ""} (${detail.parent})` : "—"}</dd>
        <dt class="text-gray-500 dark:text-gray-400">{t("unit", "Business unit")}</dt>
        <dd class="truncate text-gray-900 dark:text-gray-100">{detail.unit_name ?? detail.unit ?? "—"}</dd>
        <dt class="text-gray-500 dark:text-gray-400">{t("owner", "Owner")}</dt>
        <dd class="truncate text-gray-900 dark:text-gray-100">{detail.owner_name ?? "—"}</dd>
        {#if detail.reference}
          <dt class="text-gray-500 dark:text-gray-400">{t("reference", "Reference")}</dt>
          <dd class="truncate text-gray-900 dark:text-gray-100" title={detail.reference}>{detail.reference}</dd>
        {/if}
      </dl>
      {#if detail.description}
        <p class="line-clamp-5 leading-relaxed text-gray-600 dark:text-gray-300" title={detail.description}>{detail.description}</p>
      {/if}
      {#if detail.tags?.length}
        <div class="flex flex-wrap gap-1">
          {#each detail.tags as tag}
            <span class="rounded bg-gray-100 px-1.5 py-0.5 text-[11px] text-gray-700 dark:bg-gray-800 dark:text-gray-300">#{tag}</span>
          {/each}
        </div>
      {/if}
    </section>

    <!-- Tabs: only the body scrolls -->
    <div class="flex border-b border-gray-200 px-2 dark:border-gray-700" role="tablist" tabindex="-1" onkeydown={onTabKey}>
      {#each tabs as x (x.key)}
        <button
          type="button"
          role="tab"
          data-tab={x.key}
          aria-selected={tab === x.key}
          tabindex={tab === x.key ? 0 : -1}
          title={x.full}
          class={`-mb-px flex-1 truncate border-b-2 px-1.5 py-3 text-xs font-medium transition ${tab === x.key ? "border-indigo-600 text-indigo-600 dark:border-indigo-400 dark:text-indigo-400" : "border-transparent text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200"}`}
          onclick={() => (tab = x.key)}
        >
          {x.short} <span class="text-[10px] opacity-70">({x.count})</span>
        </button>
      {/each}
    </div>

    <div class="min-h-0 flex-1 overflow-y-auto px-4 py-4 text-sm" role="tabpanel">
      {#if tab === "outgoing" || tab === "incoming"}
        {#if !relations.length}
          <p class="text-xs text-gray-400 dark:text-gray-500">{t("none", "None")}</p>
        {:else}
          <ul class="space-y-2.5">
            {#each relations as r (r.type + r.other)}
              <li class="rounded-lg border border-gray-200 px-3 py-2.5 dark:border-gray-700">
                <div class="flex flex-wrap items-baseline gap-x-2 text-sm">
                  <span class="font-semibold text-gray-800 dark:text-gray-100">{label("relation", r.type)}</span>
                  {#if !r.directed}<span class="text-gray-500">({t("undirected", "both ways")})</span>{/if}
                  <span class="text-gray-700 dark:text-gray-300">{r.other_name ?? r.other}</span>
                  <span class="font-mono text-[10px] text-gray-400">{r.other}</span>
                </div>
                {#if r.rationale}<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">{r.rationale}</p>{/if}
              </li>
            {/each}
          </ul>
        {/if}
      {:else if tab === "assets"}
        {#if subAssets}<p class="mb-2 text-[11px] text-gray-500 dark:text-gray-400">{t("from_subprocesses", "{n} from sub-processes", { n: subAssets })}</p>{/if}
        {#if !detail.assets.length}
          <p class="text-xs text-gray-400 dark:text-gray-500">{t("none", "None")}</p>
        {:else}
          <ul class="space-y-2.5">
            {#each detail.assets as a (`${a.asset}-${a.type}-${a.via ?? ""}`)}
              <li class="rounded-lg border border-gray-200 px-3 py-2.5 dark:border-gray-700">
                <div class="flex flex-wrap items-baseline gap-x-2 text-sm">
                  {#if assetHref(a.asset, a.category)}
                    <a href={assetHref(a.asset, a.category)} class={linkClass} title={t("open_asset", "Open this asset in the AI Library")}>
                      {a.asset_name ?? a.asset}
                      <svg class="h-3 w-3 shrink-0" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M11 3a1 1 0 100 2h2.59l-6.3 6.3a1 1 0 101.42 1.4L15 6.42V9a1 1 0 102 0V4a1 1 0 00-1-1h-5zM5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" /></svg>
                    </a>
                  {:else}
                    <span class="font-semibold text-gray-800 dark:text-gray-100">{a.asset_name ?? a.asset}</span>
                  {/if}
                  {#if a.category}<span class="text-gray-500">{a.category}</span>{/if}
                  <span class="text-xs text-gray-500 dark:text-gray-400">{label("link", a.type)}</span>
                  {#if a.via}<span class="text-gray-400">{t("via", "via {code}", { code: a.via })}</span>{/if}
                </div>
                {#if a.rationale}<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">{a.rationale}</p>{/if}
              </li>
            {/each}
          </ul>
        {/if}
      {:else}
        {#if subInits}<p class="mb-2 text-[11px] text-gray-500 dark:text-gray-400">{t("from_subprocesses", "{n} from sub-processes", { n: subInits })}</p>{/if}
        {#if !detail.inits.length}
          <p class="text-xs text-gray-400 dark:text-gray-500">{t("none", "None")}</p>
        {:else}
          <ul class="space-y-2.5">
            {#each detail.inits as i (`${i.init}-${i.type}-${i.via ?? ""}`)}
              <li class="rounded-lg border border-gray-200 px-3 py-2.5 dark:border-gray-700">
                <div class="flex flex-wrap items-baseline gap-x-2 text-sm">
                  <a href={initHref(i.init)} class={linkClass} title={t("open_initiative", "Open this initiative in Explore Initiatives")}>
                    {i.init_name ?? i.init}
                    <svg class="h-3 w-3 shrink-0" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M11 3a1 1 0 100 2h2.59l-6.3 6.3a1 1 0 101.42 1.4L15 6.42V9a1 1 0 102 0V4a1 1 0 00-1-1h-5zM5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" /></svg>
                  </a>
                  <span class="text-xs text-gray-500 dark:text-gray-400">{label("link", i.type)}</span>
                  {#if i.via}<span class="text-gray-400">{t("via", "via {code}", { code: i.via })}</span>{/if}
                </div>
                {#if i.rationale}<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">{i.rationale}</p>{/if}
              </li>
            {/each}
          </ul>
        {/if}
      {/if}
    </div>
  {:else}
    <div class="flex-1"></div>
  {/if}

  <!-- Actions at the bottom -->
  {#if showMapLink || showChainLink || landscape.can_manage}
    <footer class="flex flex-nowrap justify-end gap-2 border-t border-gray-200 px-4 py-3.5 dark:border-gray-700">
      {#if landscape.can_manage}
        <a href={manageHref} class="whitespace-nowrap rounded-lg border border-gray-300 px-2.5 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-100 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800">{t("open_in_management", "Open in Process Management")}</a>
      {/if}
      {#if showMapLink}
        <a href={mapHref} class="whitespace-nowrap rounded-lg bg-indigo-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-indigo-700">{t("show_in_map", "Show in Process Map")}</a>
      {/if}
      {#if showChainLink}
        <a href={chainHref} class="whitespace-nowrap rounded-lg bg-indigo-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-indigo-700">{t("show_in_chain", "Show in Value Chain")}</a>
      {/if}
    </footer>
  {/if}
</aside>
