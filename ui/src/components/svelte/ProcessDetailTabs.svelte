<script lang="ts">
  /**
   * ProcessDetailTabs — the tabs of Process Management's dialog
   * (specs/009-process-management), in this order: Core Fields, Related
   * processes, Related assets, Related inits.
   *
   * Mounted manually by ProcessDetailModal.astro, which drives it through the
   * exported controller methods (Svelte 5 `mount()` returns them).
   *
   * - Core Fields is an empty shell the parent re-parents its own <section> into.
   * - The three Related tabs are the shared RelatedLinksTab; they only stage.
   *   In edit mode the parent saves one tab at a time with that tab's whole set;
   *   in create mode it sends every tab with the new process in one request.
   * - The Related processes picker follows the SUPPORTS / PRECEDES rules the
   *   API publishes in form-options (`relation_rules`), never a local copy.
   */
  import { onMount } from "svelte";
  import { getListItemsbyList } from "@/lib/list_items";
  import { toListOptions } from "@/lib/listLang";
  import { translate } from "@/utils/i18nClient";
  import RelatedLinksTab, { type LinkOption, type LinkRow } from "@/components/svelte/RelatedLinksTab.svelte";
  import type {
    ProcessAssetLink, ProcessFormOptions, ProcessInitLink, ProcessRelation,
  } from "@/types/api";

  type TabName = "core" | "related_processes" | "related_assets" | "related_inits";

  let {
    idPrefix,
    onTabChange,
  }: {
    idPrefix: string;
    onTabChange?: (name: TabName) => void;
  } = $props();

  const P = "process_detail_modal";

  // ── i18n ──────────────────────────────────────────────────────────────
  let langTick = $state(0);
  const t = (key: string, fallback: string): string => {
    void langTick;
    try {
      const v = translate(`${P}.${key}`);
      if (v && v !== `${P}.${key}`) return v;
    } catch {
      /* non-fatal */
    }
    return fallback;
  };
  const currentLang = (): string =>
    (typeof localStorage !== "undefined" && localStorage.getItem("lang")) === "es" ? "es" : "en";

  let listRaw = $state<Record<string, any[]>>({});
  const listOpts = (code: string): LinkOption[] => {
    void langTick;
    return toListOptions(listRaw[code] ?? [], currentLang());
  };
  async function ensureList(code: string): Promise<void> {
    if (listRaw[code]) return;
    let items: any[] = [];
    try {
      items = await getListItemsbyList(code);
    } catch {
      items = [];
    }
    listRaw = { ...listRaw, [code]: items };
  }

  // ── State ─────────────────────────────────────────────────────────────
  let rootEl = $state<HTMLElement | undefined>(undefined);
  let activeTab = $state<TabName>("core");
  let readonly = $state(false);
  let coreDirty = $state(false);
  let currentCode = $state<string | null>(null);
  let processType = $state("");
  let options = $state<ProcessFormOptions | null>(null);

  let relTab = $state<any>(undefined);
  let assetTab = $state<any>(undefined);
  let initTab = $state<any>(undefined);
  // Re-read the children's dirty/count after they stage something.
  let stageTick = $state(0);

  $effect(() => {
    onTabChange?.(activeTab);
  });

  const processOptions = $derived<LinkOption[]>(
    (options?.processes ?? [])
      .filter((p) => p.code !== currentCode)
      .map((p) => ({ value: p.code, label: `${p.code} · ${p.name}` })),
  );
  const processTypeOf = $derived(new Map((options?.processes ?? []).map((p) => [p.code, p.type])));
  const assetOptions = $derived<LinkOption[]>(
    (options?.assets ?? []).map((a) => ({
      value: String(a.id),
      label: a.category ? `${a.name} · ${a.category}` : a.name,
    })),
  );
  const initOptions = $derived<LinkOption[]>(
    (options?.initiatives ?? []).map((i) => ({ value: String(i.id), label: i.name })),
  );

  /** The relation rules from the API, applied to this process as the source. */
  function processFilter(type: string, option: LinkOption): boolean {
    const rule = options?.relation_rules?.[type];
    if (!rule) return true;
    const targetType = processTypeOf.get(option.value) ?? "";
    if (rule.same_type && processType && targetType !== processType) return false;
    if (rule.source && processType && !rule.source.includes(processType)) return false;
    if (rule.target && !rule.target.includes(targetType)) return false;
    return true;
  }
  function processIncompatible(type: string): string {
    return type === "SUPPORTS"
      ? t("incompatible_supports", "Supports goes only from a Support process to a Primary process.")
      : t("incompatible_precedes", "Precedes links two processes of the same type.");
  }

  // ── Controller API ────────────────────────────────────────────────────
  export function setOptions(next: ProcessFormOptions): void {
    options = next;
  }

  /** The Core Fields type drives the Related processes rules (create mode too). */
  export function setProcessType(type: string): void {
    processType = type;
  }

  export function setCoreDirty(dirty: boolean): void {
    coreDirty = dirty;
  }

  export function activateTab(name: TabName): void {
    activeTab = name;
  }

  export function setContext(code: string | null, isReadonly: boolean): void {
    currentCode = code;
    readonly = isReadonly;
  }

  export function applyRelations(rows: ProcessRelation[]): void {
    relTab?.hydrate(rows.map<LinkRow>((r) => ({
      target: r.target,
      targetLabel: r.target_name ? `${r.target} · ${r.target_name}` : r.target,
      type: r.type,
      rationale: r.rationale ?? "",
      inactive: !r.target_active,
      incoming: r.direction === "incoming",
    })));
    stageTick += 1;
  }

  export function applyAssets(rows: ProcessAssetLink[]): void {
    assetTab?.hydrate(rows.map<LinkRow>((r) => ({
      target: String(r.asset),
      targetLabel: r.asset_name ? (r.category ? `${r.asset_name} · ${r.category}` : r.asset_name) : `#${r.asset}`,
      type: r.type,
      rationale: r.rationale ?? "",
      inactive: !r.asset_active,
    })));
    stageTick += 1;
  }

  export function applyInits(rows: ProcessInitLink[]): void {
    initTab?.hydrate(rows.map<LinkRow>((r) => ({
      target: String(r.init),
      targetLabel: r.init_name ?? `#${r.init}`,
      type: r.type,
      rationale: r.rationale ?? "",
      inactive: !r.init_active,
    })));
    stageTick += 1;
  }

  export function relationsStaged() {
    return (relTab?.staged() ?? []).map((r: any) => ({ target: r.target, type: r.type, rationale: r.rationale }));
  }
  export function assetsStaged() {
    return (assetTab?.staged() ?? []).map((r: any) => ({ asset: Number(r.target), type: r.type, rationale: r.rationale }));
  }
  export function initsStaged() {
    return (initTab?.staged() ?? []).map((r: any) => ({ init: Number(r.target), type: r.type, rationale: r.rationale }));
  }

  export function relationsDirty(): boolean {
    return relTab?.dirty() ?? false;
  }
  export function assetsDirty(): boolean {
    return assetTab?.dirty() ?? false;
  }
  export function initsDirty(): boolean {
    return initTab?.dirty() ?? false;
  }

  export function focusFirstPending(): void {
    rootEl
      ?.querySelector<HTMLElement>(`[data-tabpanel="${activeTab}"] [data-pending="1"]`)
      ?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  export function reset(): void {
    activeTab = "core";
    readonly = false;
    coreDirty = false;
    currentCode = null;
    processType = "";
    relTab?.reset();
    assetTab?.reset();
    initTab?.reset();
    stageTick += 1;
  }

  // Children stage through their own clicks; poll their state on any click or
  // input inside the tabs so the dot and counts stay current.
  function bump(): void {
    stageTick += 1;
  }

  // ── Tabs ──────────────────────────────────────────────────────────────
  const tabOrder: TabName[] = ["core", "related_processes", "related_assets", "related_inits"];
  const tabLabel = (name: TabName): string => {
    const keys: Record<TabName, [string, string]> = {
      core: ["tab_core", "Core Fields"],
      related_processes: ["tab_related_processes", "Related processes"],
      related_assets: ["tab_related_assets", "Related assets"],
      related_inits: ["tab_related_inits", "Related inits"],
    };
    return t(keys[name][0], keys[name][1]);
  };
  const tabCount = (name: TabName): number | null => {
    void stageTick;
    if (name === "related_processes") return relTab?.count() ?? 0;
    if (name === "related_assets") return assetTab?.count() ?? 0;
    if (name === "related_inits") return initTab?.count() ?? 0;
    return null;
  };
  const tabDirty = (name: TabName): boolean => {
    void stageTick;
    if (readonly) return false;
    if (name === "core") return coreDirty;
    if (name === "related_processes") return relationsDirty();
    if (name === "related_assets") return assetsDirty();
    return initsDirty();
  };
  const tabClass = (name: TabName): string =>
    "whitespace-nowrap border-b-2 px-1 pb-3 " +
    (activeTab === name
      ? "border-indigo-600 text-indigo-600 dark:text-indigo-400"
      : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200");

  function onTabKeydown(e: KeyboardEvent): void {
    const idx = tabOrder.indexOf(activeTab);
    let next = -1;
    if (e.key === "ArrowRight") next = (idx + 1) % tabOrder.length;
    else if (e.key === "ArrowLeft") next = (idx - 1 + tabOrder.length) % tabOrder.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = tabOrder.length - 1;
    if (next >= 0) {
      e.preventDefault();
      activeTab = tabOrder[next];
      rootEl?.querySelector<HTMLButtonElement>(`[data-tab="${tabOrder[next]}"]`)?.focus();
    }
  }

  onMount(() => {
    void ensureList("PROCESS_RELATION_TYPE");
    void ensureList("RELATION_TYPE");
    const onLang = () => {
      langTick += 1;
    };
    window.addEventListener("languageChanged", onLang);
    document.addEventListener("synapxia:locale-changed", onLang);
    return () => {
      window.removeEventListener("languageChanged", onLang);
      document.removeEventListener("synapxia:locale-changed", onLang);
    };
  });
</script>

<div bind:this={rootEl} onclick={bump} oninput={bump} onchange={bump} role="presentation">
  {#snippet pendingDot()}
    <span
      class="ml-1 inline-block h-1.5 w-1.5 rounded-full bg-amber-500"
      title={t("unsaved_indicator", "Unsaved changes")}
      aria-hidden="true"
    ></span>
  {/snippet}

  <div class="border-b border-gray-200 dark:border-gray-800">
    <div role="tablist" aria-label="Process detail sections" class="-mb-px flex flex-nowrap gap-4 overflow-x-auto no-scrollbar text-sm font-medium sm:gap-6">
      {#each tabOrder as name (name)}
        <button
          type="button"
          role="tab"
          data-tab={name}
          aria-selected={activeTab === name}
          tabindex={activeTab === name ? 0 : -1}
          class={tabClass(name)}
          onclick={() => activateTab(name)}
          onkeydown={(e) => onTabKeydown(e)}
        >
          <span>{tabLabel(name)}</span>
          {#if tabCount(name)}
            <span class="ml-1 rounded-full bg-indigo-100 px-1.5 py-0.5 text-[10px] font-semibold text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300">{tabCount(name)}</span>
          {/if}
          {#if tabDirty(name)}{@render pendingDot()}{/if}
        </button>
      {/each}
    </div>
  </div>

  <!-- Core Fields (empty shell — the parent re-parents its <section> here) -->
  <div data-tabpanel="core" role="tabpanel" class="pt-4" class:hidden={activeTab !== "core"}>
    <section id={`${idPrefix}-core`}></section>
  </div>

  <div data-tabpanel="related_processes" role="tabpanel" class="pt-4" class:hidden={activeTab !== "related_processes"}>
    <RelatedLinksTab
      bind:this={relTab}
      {idPrefix}
      kind="process"
      targetOptions={processOptions}
      typeOptions={listOpts("PROCESS_RELATION_TYPE")}
      filterTarget={processFilter}
      incompatibleMessage={processIncompatible}
      {readonly}
      highlight={currentCode != null}
    />
  </div>

  <div data-tabpanel="related_assets" role="tabpanel" class="pt-4" class:hidden={activeTab !== "related_assets"}>
    <RelatedLinksTab
      bind:this={assetTab}
      {idPrefix}
      kind="asset"
      targetOptions={assetOptions}
      typeOptions={listOpts("RELATION_TYPE")}
      {readonly}
      highlight={currentCode != null}
    />
  </div>

  <div data-tabpanel="related_inits" role="tabpanel" class="pt-4" class:hidden={activeTab !== "related_inits"}>
    <RelatedLinksTab
      bind:this={initTab}
      {idPrefix}
      kind="init"
      targetOptions={initOptions}
      typeOptions={listOpts("RELATION_TYPE")}
      {readonly}
      highlight={currentCode != null}
    />
  </div>
</div>
