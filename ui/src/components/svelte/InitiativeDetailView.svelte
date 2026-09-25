<script lang="ts">
  /**
   * InitiativeDetailView — the read-mostly Initiative Detail opened from an
   * Explore Initiatives card (HU-IN06, specs/005-explore-initiatives R12).
   *
   * Tabs: Core Fields (read-only), Diagnosis Questions (DiagnosisTable `view`),
   * Related Assets (read-only), Discussion (Foro — interactive) and History
   * (a shell `mountHistory` hydrates). No Permissions tab, no save controls.
   * The header's favorite and vote bar write through the same services as the
   * card and report back via `onChange` so the card stays in sync.
   *
   * Mounted by InitiativeExploreModal.astro, which calls the exported `open()`.
   */
  import { translate } from "@/utils/i18nClient";
  import { getInitiativeAssets, getInitiativeDiagnostics, setInitiativeFavorite } from "@/lib/initiatives";
  import { initiativeForoApi, setInitiativeVote } from "@/lib/collaborations";
  import { showToast } from "@/lib/toast";
  import Foro from "@/components/svelte/Foro.svelte";
  import DiagnosisTable from "@/components/svelte/DiagnosisTable.svelte";
  import type { DiagnosticRow, InitiativeAsset, InitiativeExploreItem, InitVoteTally } from "@/types/api";

  type TabName = "core" | "diagnosis" | "related" | "discussion" | "history";
  // value → { en, es } per list; `label()` picks the viewer's language.
  type Labels = Record<"status" | "type" | "impact" | "priority", Record<string, Record<string, string>>>;

  let {
    modalId,
    labels = { status: {}, type: {}, impact: {}, priority: {} },
    onClose,
    onChange,
  }: {
    modalId: string;
    labels?: Labels;
    onClose?: () => void;
    onChange?: (change: { id: number; favorite?: boolean; tally?: InitVoteTally }) => void;
  } = $props();

  // ── i18n ──────────────────────────────────────────────────────────────
  let langTick = $state(0);
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
  const lang = (): string =>
    (typeof localStorage !== "undefined" && localStorage.getItem("lang")) === "es" ? "es" : "en";
  $effect(() => {
    const bump = () => {
      langTick += 1;
      if (item) void loadDiagnosis(item.id);
    };
    window.addEventListener("languageChanged", bump);
    document.addEventListener("synapxia:locale-changed", bump);
    return () => {
      window.removeEventListener("languageChanged", bump);
      document.removeEventListener("synapxia:locale-changed", bump);
    };
  });

  // ── State ─────────────────────────────────────────────────────────────
  let item = $state<InitiativeExploreItem | null>(null);
  let activeTab = $state<TabName>("core");
  let diagItems = $state<DiagnosticRow[]>([]);
  let diagState = $state<"idle" | "loading" | "error">("idle");
  let assets = $state<InitiativeAsset[]>([]);
  let assetsState = $state<"idle" | "loading" | "error">("idle");
  let voting = $state(false);

  const TABS: [TabName, string, string][] = [
    ["core", "inits_explore.tab_core", "Core Fields"],
    ["diagnosis", "inits_explore.tab_diagnosis", "Diagnosis Questions"],
    ["related", "inits_explore.tab_related", "Related Assets"],
    ["discussion", "inits_explore.tab_discussion", "Discussion"],
    ["history", "inits_explore.tab_history", "History"],
  ];

  let seq = 0;
  async function loadDiagnosis(id: number): Promise<void> {
    const mine = ++seq;
    diagState = "loading";
    try {
      const res = await getInitiativeDiagnostics(id, lang());
      if (mine !== seq) return;
      diagItems = res.items;
      diagState = "idle";
    } catch {
      if (mine === seq) diagState = "error";
    }
  }
  async function loadAssets(id: number): Promise<void> {
    assetsState = "loading";
    try {
      assets = await getInitiativeAssets(id);
      assetsState = "idle";
    } catch {
      assetsState = "error";
    }
  }

  /** Show `next` (a gallery row) — optionally on a given tab. */
  export function open(next: InitiativeExploreItem, opts: { tab?: TabName } = {}): void {
    item = { ...next, votes: { ...next.votes } };
    activeTab = opts.tab ?? "core";
    diagItems = [];
    assets = [];
    void loadDiagnosis(next.id);
    void loadAssets(next.id);
  }

  async function toggleFavorite(): Promise<void> {
    if (!item) return;
    const on = !item.is_favorite;
    item.is_favorite = on;
    try {
      await setInitiativeFavorite(item.id, on);
      onChange?.({ id: item.id, favorite: on });
    } catch {
      item.is_favorite = !on;
      showToast(t("inits_explore.favorite_error", "Could not update your favorite"), "error");
    }
  }

  async function vote(value: "POSITIVE" | "NEGATIVE"): Promise<void> {
    if (!item || voting) return;
    voting = true;
    try {
      const tally = await setInitiativeVote(item.id, value);
      item.votes = tally;
      onChange?.({ id: item.id, tally });
    } catch {
      showToast(t("inits_explore.vote_error", "Could not register your vote"), "error");
    } finally {
      voting = false;
    }
  }

  const label = (group: keyof Labels, value?: string | null): string => {
    void langTick;
    if (!value) return "";
    const hit = labels[group]?.[value];
    return hit?.[lang()] ?? hit?.en ?? value;
  };
  // Same labels as the asset-side Related tab (related.type.*) and the category's
  // sidebar option name (menu_options.<code>), falling back to the raw code.
  const relationLabel = (type: string): string =>
    t(`related.type.${type}`, type.replace(/_/g, " ").toLowerCase());
  const categoryLabel = (code: string): string => t(`menu_options.${code.toLowerCase()}`, code);
  const tagsOf = (it: InitiativeExploreItem): string[] => (Array.isArray(it.tags) ? (it.tags as string[]) : []);

  const tabClass = (name: TabName) =>
    `whitespace-nowrap border-b-2 px-1 py-3 text-sm font-medium focus:outline-none ${
      activeTab === name
        ? "border-indigo-600 text-indigo-600 dark:text-indigo-400"
        : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
    }`;
  const fieldLabel = "text-xs font-semibold uppercase tracking-wide text-gray-400";
  const fieldValue = "mt-1 text-sm text-gray-800 dark:text-gray-200 whitespace-pre-line break-words";
  const muted = "mt-1 text-sm italic text-gray-400";
  const box = "rounded-lg border border-gray-200 bg-gray-50/60 px-4 py-3 dark:border-gray-800 dark:bg-white/[0.03]";
  const emptyClass =
    "rounded-lg border border-dashed border-gray-300 dark:border-gray-700 p-6 text-center text-sm text-gray-500 dark:text-gray-400";
  const thumb =
    "M7.493 18.5c-.425 0-.82-.236-.974-.632A7.48 7.48 0 016 15.125c0-1.75.599-3.358 1.602-4.634.151-.192.373-.309.6-.397.473-.183.89-.514 1.212-.924a9.042 9.042 0 012.861-2.4c.723-.384 1.35-.956 1.653-1.715a4.498 4.498 0 00.322-1.672V2.75a.75.75 0 01.75-.75 2.25 2.25 0 012.25 2.25c0 1.152-.26 2.243-.722 3.218-.266.558.107 1.282.725 1.282h3.126c1.026 0 1.945.694 2.054 1.715.045.422.068.85.068 1.285a11.95 11.95 0 01-2.649 7.521c-.388.482-.987.729-1.605.729H14.23c-.483 0-.964-.078-1.423-.23l-3.114-1.04a4.501 4.501 0 00-1.423-.23h-.777ZM2.331 10.727a11.969 11.969 0 00-.831 4.398 12 12 0 00.52 3.507c.26.85 1.084 1.368 1.973 1.368H4.9c.445 0 .72-.498.523-.898a8.963 8.963 0 01-.924-3.977c0-1.708.476-3.305 1.302-4.666.245-.403-.028-.959-.5-.959H4.25c-.832 0-1.612.453-1.918 1.227Z";
</script>

<!-- Fixed height: switching tabs must not resize the window (short tabs scroll
     inside the body instead). -->
<div class="flex h-[min(85vh,760px)] flex-col">
  <!-- Header -->
  <div class="flex items-start gap-3 border-b border-gray-200 px-5 py-4 dark:border-gray-800">
    <div class="min-w-0 flex-1">
      <div class="flex flex-wrap items-center gap-2">
        {#if item}
          <span class="inline-flex items-center rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-semibold text-indigo-700 dark:bg-indigo-500/15 dark:text-indigo-300">{label("status", item.status)}</span>
          {#if item.type}
            <span class="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-700 dark:bg-gray-800 dark:text-gray-300">{label("type", item.type)}</span>
          {/if}
        {/if}
      </div>
      <h2 class="mt-1 text-lg font-semibold text-gray-900 dark:text-white">{item?.name ?? ""}</h2>
    </div>
    {#if item}
      <div class="flex shrink-0 items-center gap-1">
        <button type="button" class={`rounded-md p-1 hover:bg-gray-100 dark:hover:bg-gray-800 ${item.votes.my_vote === "POSITIVE" ? "text-emerald-500" : "text-gray-400"}`}
          aria-pressed={item.votes.my_vote === "POSITIVE"} title={t("inits_explore.vote_up", "Useful")} aria-label={t("inits_explore.vote_up", "Useful")}
          disabled={voting} onclick={() => vote("POSITIVE")}>
          <svg class="h-5 w-5" viewBox="0 0 24 24" fill="currentColor"><path d={thumb} /></svg>
        </button>
        <span class="min-w-[1rem] text-center text-sm font-semibold text-gray-700 dark:text-gray-200">{item.votes.positive}</span>
        <button type="button" class={`rounded-md p-1 hover:bg-gray-100 dark:hover:bg-gray-800 ${item.votes.my_vote === "NEGATIVE" ? "text-rose-500" : "text-gray-400"}`}
          aria-pressed={item.votes.my_vote === "NEGATIVE"} title={t("inits_explore.vote_down", "Not useful")} aria-label={t("inits_explore.vote_down", "Not useful")}
          disabled={voting} onclick={() => vote("NEGATIVE")}>
          <svg class="h-5 w-5" viewBox="0 0 24 24" fill="currentColor"><g transform="rotate(180 12 12)"><path d={thumb} /></g></svg>
        </button>
        <span class="min-w-[1rem] text-center text-sm font-semibold text-gray-700 dark:text-gray-200">{item.votes.negative}</span>
        <button type="button" class={`ml-1 rounded-md p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 ${item.is_favorite ? "text-yellow-400" : "text-gray-400"}`}
          aria-pressed={item.is_favorite} title={t("inits_explore.favorite", "Favorite")} aria-label={t("inits_explore.favorite", "Favorite")}
          onclick={toggleFavorite}>
          <svg class="h-5 w-5" viewBox="0 0 20 20" fill={item.is_favorite ? "currentColor" : "none"} stroke="currentColor" stroke-width="1.5">
            <path d="M9.05 2.93c.3-.92 1.6-.92 1.9 0l1.3 4.02a1 1 0 00.95.69h4.22c.97 0 1.37 1.24.59 1.81l-3.42 2.48a1 1 0 00-.36 1.12l1.3 4.02c.3.92-.75 1.69-1.54 1.12l-3.41-2.48a1 1 0 00-1.18 0l-3.41 2.48c-.78.57-1.84-.2-1.54-1.12l1.3-4.02a1 1 0 00-.36-1.12L2 9.45c-.78-.57-.38-1.81.6-1.81h4.21a1 1 0 00.95-.69l1.3-4.02z" />
          </svg>
        </button>
      </div>
    {/if}
    <button type="button" class="shrink-0 rounded-md p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-800"
      aria-label={t("inits_explore.close", "Close")} title={t("inits_explore.close", "Close")} onclick={() => onClose?.()}>
      <svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" /></svg>
    </button>
  </div>

  <!-- Tabs -->
  <div class="border-b border-gray-200 px-5 dark:border-gray-800">
    <div role="tablist" aria-label="Initiative detail" class="-mb-px flex flex-nowrap gap-4 overflow-x-auto no-scrollbar sm:gap-6">
      {#each TABS as [name, key, fallback] (name)}
        <button type="button" role="tab" aria-selected={activeTab === name} class={tabClass(name)} onclick={() => (activeTab = name)}>
          {t(key, fallback)}
          {#if name === "related" && item?.related_assets_count}
            <span class="ml-1 rounded-full bg-indigo-100 px-1.5 py-0.5 text-[10px] font-semibold text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300">{item.related_assets_count}</span>
          {/if}
        </button>
      {/each}
    </div>
  </div>

  <div class="flex-1 overflow-y-auto px-5 py-4">
    <!-- Core Fields -->
    <div class:hidden={activeTab !== "core"} class="grid gap-3 sm:grid-cols-3">
      {#if item}
        <div class={`sm:col-span-3 ${box}`}>
          <p class={fieldLabel}>{t("inits_explore.field_description", "Description")}</p>
          {#if item.description}<p class={fieldValue}>{item.description}</p>{:else}<p class={muted}>—</p>{/if}
        </div>
        <div class={box}>
          <p class={fieldLabel}>{t("inits_explore.field_type", "Type")}</p>
          <p class={item.type ? fieldValue : muted}>{label("type", item.type) || "—"}</p>
        </div>
        <div class={box}>
          <p class={fieldLabel}>{t("inits_explore.field_impact", "Expected impact")}</p>
          <p class={fieldValue}>{label("impact", item.expected_impact) || "—"}</p>
        </div>
        <div class={box}>
          <p class={fieldLabel}>{t("inits_explore.field_priority", "Priority")}</p>
          <p class={fieldValue}>{label("priority", item.priority_level) || "—"}</p>
        </div>
        <div class={`sm:col-span-3 ${box}`}>
          <p class={fieldLabel}>{t("inits_explore.field_reference", "Reference")}</p>
          {#if item.reference}
            {#if /^https?:\/\//i.test(item.reference)}
              <a class="mt-1 block break-all text-sm text-indigo-600 hover:underline dark:text-indigo-400" href={item.reference} target="_blank" rel="noopener noreferrer">{item.reference}</a>
            {:else}
              <p class={fieldValue}>{item.reference}</p>
            {/if}
          {:else}<p class={muted}>—</p>{/if}
        </div>
        <div class={`sm:col-span-3 ${box}`}>
          <p class={fieldLabel}>{t("inits_explore.field_tags", "Tags")}</p>
          {#if tagsOf(item).length}
            <div class="mt-1 flex flex-wrap gap-2">
              {#each tagsOf(item) as tag (tag)}<span class="text-sm font-medium text-indigo-600 dark:text-indigo-400">#{tag}</span>{/each}
            </div>
          {:else}<p class={muted}>—</p>{/if}
        </div>
        <div class={`sm:col-span-3 ${box}`}>
          <p class={fieldLabel}>{t("inits_explore.field_detail", "Detail")}</p>
          {#if item.detail}<p class={fieldValue}>{item.detail}</p>{:else}<p class={muted}>—</p>{/if}
        </div>
      {/if}
    </div>

    <!-- Diagnosis Questions -->
    <div class:hidden={activeTab !== "diagnosis"}>
      {#if diagState === "loading"}
        <p class="text-sm text-gray-400">{t("inits_explore.loading", "Loading…")}</p>
      {:else if diagState === "error"}
        <p class="text-sm text-red-600 dark:text-red-400">{t("inits_explore.error", "Could not load this initiative.")}</p>
      {:else if !diagItems.length}
        <div class={emptyClass}>{t("inits_explore.diag_empty", "No diagnosis criteria are configured.")}</div>
      {:else}
        <DiagnosisTable items={diagItems} mode="view" />
      {/if}
    </div>

    <!-- Related Assets -->
    <div class:hidden={activeTab !== "related"}>
      {#if assetsState === "loading"}
        <p class="text-sm text-gray-400">{t("inits_explore.loading", "Loading…")}</p>
      {:else if assetsState === "error"}
        <p class="text-sm text-red-600 dark:text-red-400">{t("inits_explore.error", "Could not load this initiative.")}</p>
      {:else if !assets.length}
        <div class={emptyClass}>{t("inits_explore.related_empty", "No related assets.")}</div>
      {:else}
        <div class="grid gap-2 sm:grid-cols-2">
          {#each assets as a (`${a.asset}:${a.type}`)}
            <div class="rounded-lg border border-gray-200 p-3 dark:border-gray-800">
              <div class="mb-1 flex items-center justify-between gap-2">
                <span class="truncate text-sm font-semibold text-gray-900 dark:text-gray-100" title={a.asset_name ?? ""}>{a.asset_name ?? `#${a.asset}`}</span>
                <span class="shrink-0 rounded-md bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700 dark:bg-indigo-500/15 dark:text-indigo-300">{relationLabel(a.type)}</span>
              </div>
              {#if a.category}
                <p class="text-xs font-medium text-gray-500 dark:text-gray-400">{categoryLabel(a.category)}</p>
              {/if}
              {#if a.rationale}
                <p class="mt-1 line-clamp-2 text-xs text-gray-500 dark:text-gray-400" title={a.rationale}>{a.rationale}</p>
              {/if}
            </div>
          {/each}
        </div>
      {/if}
    </div>

    <!-- Discussion (interactive) -->
    <div class:hidden={activeTab !== "discussion"}>
      <Foro modalId={modalId} api={initiativeForoApi} idAttr="initId" />
    </div>

    <!-- History (hydrated by mountHistory from the modal shell) -->
    <div class:hidden={activeTab !== "history"}>
      <section id={`${modalId}-history`}>
        <p data-history-status class="hidden text-sm text-gray-400 dark:text-gray-500"></p>
        <div data-history-list></div>
      </section>
    </div>
  </div>
</div>
