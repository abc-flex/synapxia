<script lang="ts">
  /**
   * Header search palette — search the sidebar's modules/options, ranked by
   * text relevance (AI Library module boosted), then by how often/recently
   * the user has opened each result. Client-side only: the index comes from
   * the already-cached `nav_cache` (see lib/navigation) and usage/recency
   * live in localStorage (lib/searchIndex) — nothing is sent to the API.
   */
  import { onMount } from "svelte";
  import { getNavigationData, readNavCache } from "@/lib/navigation";
  import { translate } from "@/utils/i18nClient";
  import {
    buildSearchEntries,
    rankEntries,
    suggestEntries,
    recordOptionUse,
    type SearchEntry,
    type SearchResult,
  } from "@/lib/searchIndex";
  import SearchIcon from "@/images/icons/search.svg?raw";
  import type { NavOption } from "@/types/nav";

  interface Props {
    placeholder?: string;
  }
  let { placeholder = "Search or type command..." }: Props = $props();

  let entries = $state<SearchEntry[]>([]);
  let query = $state("");
  let open = $state(false);
  let activeIndex = $state(0);
  let langTick = $state(0); // bump on language switch → re-translate names + labels

  let containerEl = $state<HTMLDivElement | undefined>(undefined);
  let inputEl = $state<HTMLInputElement | undefined>(undefined);

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

  const results = $derived<SearchResult[]>(
    query.trim() ? rankEntries(query, entries).slice(0, 8) : suggestEntries(entries, 6),
  );
  const sectionLabel = $derived(
    query.trim() ? t("search.results", "Results") : t("search.suggested", "Suggested"),
  );

  function moduleName(code: string): string {
    return t(`modules.${code}`, code);
  }
  function optionName(code: string): string {
    return t(`menu_options.${code.toLowerCase()}`, code);
  }

  function buildEntries(options: NavOption[]): SearchEntry[] {
    return buildSearchEntries(options, moduleName, optionName);
  }

  async function load(): Promise<void> {
    const cached = readNavCache();
    if (cached?.itemsNav?.length) entries = buildEntries(cached.itemsNav);
    try {
      const fresh = await getNavigationData();
      if (fresh.itemsNav.length) entries = buildEntries(fresh.itemsNav);
    } catch {
      /* keep whatever cache we had — non-fatal */
    }
  }

  function openPanel(): void {
    open = true;
    activeIndex = 0;
  }

  function closePanel(): void {
    open = false;
  }

  function go(result: SearchResult): void {
    recordOptionUse(result.optionCode);
    window.location.href = result.path || "#";
  }

  function onInput(): void {
    activeIndex = 0;
    openPanel();
  }

  function onKeydown(e: KeyboardEvent): void {
    if (e.key === "Escape") {
      closePanel();
      inputEl?.blur();
      return;
    }
    if (!open) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (results.length) activeIndex = (activeIndex + 1) % results.length;
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (results.length) activeIndex = (activeIndex - 1 + results.length) % results.length;
    } else if (e.key === "Enter") {
      e.preventDefault();
      const pick = results[activeIndex];
      if (pick) go(pick);
    }
  }

  function onGlobalKeydown(e: KeyboardEvent): void {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      inputEl?.focus();
      openPanel();
    }
  }

  function onDocumentClick(e: MouseEvent): void {
    if (containerEl && !containerEl.contains(e.target as Node)) closePanel();
  }

  onMount(() => {
    const onLang = () => (langTick += 1);
    window.addEventListener("languageChanged", onLang);
    document.addEventListener("keydown", onGlobalKeydown);
    document.addEventListener("mousedown", onDocumentClick);
    void load();
    return () => {
      window.removeEventListener("languageChanged", onLang);
      document.removeEventListener("keydown", onGlobalKeydown);
      document.removeEventListener("mousedown", onDocumentClick);
    };
  });
</script>

<div class="search-palette relative" bind:this={containerEl}>
  <div class="relative">
    <span class="absolute top-1/2 left-4 -translate-y-1/2 h-5 w-5 text-gray-400">
      {@html SearchIcon}
    </span>
    <input
      type="text"
      bind:value={query}
      bind:this={inputEl}
      placeholder={t("header.search_placeholder", placeholder)}
      oninput={onInput}
      onfocus={openPanel}
      onkeydown={onKeydown}
      class="h-11 w-full rounded-lg border border-gray-200 bg-transparent py-2.5 pr-14 pl-12 text-sm text-gray-800 placeholder:text-gray-400 shadow-inner focus:border-indigo-300 focus:ring-2 focus:ring-indigo-100 focus:outline-none dark:border-gray-800 dark:bg-gray-900 dark:text-white/90 dark:placeholder:text-white/30"
    />
    <button
      type="button"
      class="absolute top-1/2 right-2.5 inline-flex -translate-y-1/2 items-center gap-0.5 rounded-lg border border-gray-200 bg-gray-50 px-[7px] py-[4.5px] text-xs text-gray-500 dark:border-gray-800 dark:bg-white/5 dark:text-gray-400"
      onclick={() => { inputEl?.focus(); openPanel(); }}
    >
      <span>⌘</span>
      <span>K</span>
    </button>
  </div>

  {#if open}
    <div class="search-dropdown">
      <p class="search-section-label">{sectionLabel}</p>
      {#if results.length}
        <ul class="search-result-list custom-scrollbar">
          {#each results as result, i (result.optionCode)}
            <li>
              <button
                type="button"
                class="search-result-item {i === activeIndex ? 'search-result-item-active' : ''}"
                onmouseenter={() => (activeIndex = i)}
                onclick={() => go(result)}
              >
                <span class="search-result-breadcrumb">
                  {t("breadcrumb.home", "Home")} › {result.moduleName}
                </span>
                <span class="search-result-title">{result.optionName}</span>
              </button>
            </li>
          {/each}
        </ul>
      {:else}
        <p class="search-empty">{t("search.no_results", "No matching options")}</p>
      {/if}
    </div>
  {/if}
</div>
