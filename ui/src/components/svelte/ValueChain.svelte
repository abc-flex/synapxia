<script lang="ts">
  /**
   * ValueChain — the /proc/value_chain island (specs/010-process-landscape-views,
   * HU-PR05, US1).
   *
   * Porter layout: the primary activities in one row along their PRECEDES
   * order, ending in the margin marker, and the support activities as bands
   * underneath, compact enough to fit one screen. Each block shows its
   * rolled-up asset / initiative counts and a Draft / Review marker; an AI
   * opportunity is told by its amber fill (legend), and *Only opportunities*
   * dims everything else. Blocks expand one level (Q2 = B).
   * Every figure comes from the server; the view state lives in the address.
   */
  import { onMount } from "svelte";
  import { apiErrorDetail } from "@/lib/api";
  import { listLabel } from "@/lib/listLang";
  import {
    byCode, getLandscape, isForbidden, landscapeText, loadLandscapeLists, readViewState,
    topLevelOf, writeViewState, type LandscapeLists, type ViewState,
  } from "@/lib/processLandscape";
  import type { LandscapeProcess, ProcessLandscape } from "@/types/api";
  import ProcessLandscapePanel from "./ProcessLandscapePanel.svelte";

  let langTick = $state(0);
  const t = (key: string, fallback: string, vars?: Record<string, string | number>) => {
    void langTick;
    return landscapeText("value_chain", key, fallback, vars);
  };
  const tl = (key: string, fallback: string, vars?: Record<string, string | number>) => {
    void langTick;
    return landscapeText("process_landscape", key, fallback, vars);
  };

  let view = $state<ViewState>(readViewState());
  let landscape = $state<ProcessLandscape | null>(null);
  let lists = $state<LandscapeLists>({ type: {}, status: {}, relation: {}, link: {} });
  let units = $state<{ code: string; name: string }[]>([]);
  let loading = $state(true);
  let error = $state("");
  let forbidden = $state(false);
  let notice = $state("");
  let expanded = $state<Set<string>>(new Set());
  let selected = $state<string | null>(null);
  let seq = 0;

  const index = $derived(landscape ? byCode(landscape) : new Map<string, LandscapeProcess>());
  const primaries = $derived(landscape ? landscape.primary_order.map((c) => index.get(c)!).filter(Boolean) : []);
  const supports = $derived(landscape ? landscape.support_order.map((c) => index.get(c)!).filter(Boolean) : []);
  const highlighted = $derived(selected && index.has(selected) ? topLevelOf(selected, index) : null);

  function unitsOf(l: ProcessLandscape) {
    const seen = new Map<string, string>();
    for (const p of l.processes) if (p.unit) seen.set(p.unit, p.unit_name ?? p.unit);
    return [...seen].map(([code, name]) => ({ code, name })).sort((a, b) => a.name.localeCompare(b.name));
  }

  async function load(applyFocus = false) {
    const mine = ++seq;
    loading = true;
    error = "";
    try {
      const result = await getLandscape(view.unit);
      if (mine !== seq) return;
      landscape = result;
      if (!view.unit) units = unitsOf(result);
      if (applyFocus && view.focus) focusOn(view.focus);
    } catch (err) {
      if (mine !== seq) return;
      forbidden = isForbidden(err);
      error = apiErrorDetail(err, tl("load_error", "The process landscape could not be loaded."));
    } finally {
      if (mine === seq) loading = false;
    }
  }

  function focusOn(code: string) {
    if (!index.has(code)) {
      notice = tl("focus_not_found", "The process in the address is not in this view.");
      view = { ...view, focus: null };
      writeViewState(view);
      return;
    }
    const top = topLevelOf(code, index);
    if (top !== code) expanded = new Set([...expanded, top]);
    selected = code;
  }

  function select(code: string) {
    selected = code;
    notice = "";
    view = { ...view, focus: code };
    writeViewState(view);
  }

  function closePanel() {
    selected = null;
    view = { ...view, focus: null };
    writeViewState(view);
  }

  function toggle(code: string) {
    const next = new Set(expanded);
    if (next.has(code)) next.delete(code);
    else next.add(code);
    expanded = next;
  }

  function setUnit(unit: string) {
    view = { ...view, unit: unit || null };
    writeViewState(view);
    load();
  }

  function setOpportunities() {
    view = { ...view, opportunities: !view.opportunities };
    writeViewState(view);
  }

  onMount(() => {
    const onLang = () => (langTick += 1);
    window.addEventListener("languageChanged", onLang);
    loadLandscapeLists().then((l) => (lists = l));
    // Unit options come from the unfiltered landscape, so filtering never shrinks them.
    if (view.unit) getLandscape(null).then((l) => (units = unitsOf(l))).catch(() => {});
    load(true);
    return () => window.removeEventListener("languageChanged", onLang);
  });

  const statusLabel = (p: LandscapeProcess) => {
    void langTick;
    return listLabel(lists.status, p.status) || p.status;
  };
  const marked = (p: LandscapeProcess) => p.status === "DRAFT" || p.status === "REVIEW";
  const dimmed = (p: LandscapeProcess) => view.opportunities && !p.is_opportunity;
  // *Only opportunities* also looks inside: a block that is not an opportunity
  // but has opportunity sub-processes stays lit while collapsed (amber ring as
  // a hint) and, once expanded, dims only its own header so those
  // sub-processes stand out.
  const hasOppChild = (p: LandscapeProcess) => p.child_order.some((c) => index.get(c)?.is_opportunity);
  const blockDim = (p: LandscapeProcess) => dimmed(p) && !hasOppChild(p);
  const headDim = (p: LandscapeProcess) => dimmed(p) && hasOppChild(p) && expanded.has(p.code);
  const oppHint = (p: LandscapeProcess) => dimmed(p) && hasOppChild(p) && !expanded.has(p.code);
  const expandable = $derived([...primaries, ...supports].filter((p) => p.child_order.length).map((p) => p.code));
  const allExpanded = $derived(expandable.length > 0 && expandable.every((c) => expanded.has(c)));
  function toggleAll() {
    expanded = allExpanded ? new Set() : new Set(expandable);
  }
  // The amber fill IS the AI-opportunity marker (see the legend); no badge.
  const tone = (p: LandscapeProcess, kind: "block" | "sub") =>
    p.is_opportunity
      ? "border-amber-300 bg-amber-100 dark:border-amber-700 dark:bg-amber-900/50"
      : kind === "block"
        ? "border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"
        : "border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-900";
</script>

<!-- Compact layout (2026-10-25): the whole chain fits one screen. An AI
     opportunity is shown by the amber fill alone, explained by the legend. -->

{#snippet counts(p: LandscapeProcess)}
  <span class="inline-flex shrink-0 items-center gap-2 text-[11px] tabular-nums text-gray-600 dark:text-gray-300">
    <span class="inline-flex items-center gap-0.5" title={tl("assets", "{n} assets", { n: p.assets })}>
      <!-- The sidebar's AI Library icon (src/images/icons/ai-library.svg) -->
      <svg class="h-3.5 w-3.5 text-indigo-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 6.75c-1.55-1.13-3.4-1.75-5.25-1.75-.95 0-1.87.16-2.75.46v12.04c.88-.3 1.8-.46 2.75-.46 1.85 0 3.7.62 5.25 1.75m0-12.04c1.55-1.13 3.4-1.75 5.25-1.75.95 0 1.87.16 2.75.46v12.04c-.88-.3-1.8-.46-2.75-.46-1.85 0-3.7.62-5.25 1.75m0-12.04v12.04" /><path d="M19 3.25v3.5M17.25 5h3.5" /></svg>{p.assets}
    </span>
    <span class="inline-flex items-center gap-0.5" title={tl("inits", "{n} initiatives", { n: p.inits })}>
      <!-- The sidebar's Initiatives rocket (src/images/icons/rocket-launch.svg) -->
      <svg class="h-3 w-3 text-sky-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15.59 14.37a6 6 0 0 1-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 0 0 6.16-12.12A14.98 14.98 0 0 0 9.631 8.41m5.96 5.96a14.926 14.926 0 0 1-5.841 2.58m-.119-8.54a6 6 0 0 0-7.381 5.84h4.8m2.581-5.84a14.927 14.927 0 0 0-2.58 5.84m2.699 2.7c-.103.021-.207.041-.311.06a15.09 15.09 0 0 1-2.448-2.448 14.9 14.9 0 0 1 .06-.312m-2.24 2.39a4.493 4.493 0 0 0-1.757 4.306 4.493 4.493 0 0 0 4.306-1.758M16.5 9a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0Z" /></svg>{p.inits}
    </span>
  </span>
{/snippet}

{#snippet status(p: LandscapeProcess)}
  {#if marked(p)}
    <span class="shrink-0 rounded border border-dashed border-gray-400 px-1 text-[9px] font-semibold uppercase tracking-wide text-gray-600 dark:border-gray-500 dark:text-gray-300">{statusLabel(p)}</span>
  {/if}
{/snippet}

{#snippet expander(p: LandscapeProcess)}
  {#if p.child_order.length}
    <button
      type="button"
      class="inline-flex shrink-0 items-center gap-0.5 rounded px-1 text-[11px] font-medium text-indigo-600 hover:bg-indigo-50 dark:text-indigo-400 dark:hover:bg-indigo-950/50"
      aria-expanded={expanded.has(p.code)}
      title={expanded.has(p.code) ? t("collapse", "Hide sub-processes") : t("expand", "Show sub-processes")}
      onclick={() => toggle(p.code)}
    >
      <svg class={`h-3 w-3 transition ${expanded.has(p.code) ? "rotate-90" : ""}`} viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M7.2 14.8a.75.75 0 010-1.06L10.94 10 7.2 6.26a.75.75 0 111.06-1.06l4.27 4.27a.75.75 0 010 1.06l-4.27 4.27a.75.75 0 01-1.06 0z" /></svg>
      {p.child_order.length}
    </button>
  {/if}
{/snippet}

{#snippet subList(p: LandscapeProcess, grid: boolean)}
  {#if expanded.has(p.code)}
    <ul class={grid ? "mt-1.5 grid grid-cols-[repeat(auto-fill,minmax(10rem,1fr))] gap-1" : "mt-1.5 space-y-1"}>
      {#each p.child_order as code (code)}
        {@const c = index.get(code)}
        {#if c}
          <li>
            <button
              type="button"
              class={`flex w-full items-center gap-1.5 rounded border px-1.5 py-1 text-left transition hover:border-indigo-400 ${tone(c, "sub")} ${selected === code ? "ring-2 ring-indigo-500" : ""} ${dimmed(c) ? "opacity-30" : ""}`}
              title={`${c.code} · ${c.name}`}
              onclick={() => select(code)}
            >
              <span class="min-w-0 flex-1 truncate text-[11px] text-gray-700 dark:text-gray-300"><span class="font-mono font-bold text-gray-900 dark:text-white">{c.code}</span> {c.name}</span>
              {@render status(c)}
              {@render counts(c)}
            </button>
          </li>
        {/if}
      {/each}
    </ul>
  {/if}
{/snippet}

<div class="space-y-3">
  <!-- One compact row: short subtitle (truncated, full text on hover) + controls -->
  <div class="flex flex-wrap items-center gap-x-3 gap-y-2 md:flex-nowrap">
    <!-- Subtitle, then the AI-opportunity color legend right after it -->
    <div class="flex min-w-0 flex-1 items-center gap-3">
    <p class="min-w-0 truncate text-xs text-gray-600 dark:text-gray-400" title={t("subtitle", "Primary activities along the flow; support activities below.")}>{t("subtitle", "Primary activities along the flow; support activities below.")}</p>
      <span class="inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap text-xs text-gray-600 dark:text-gray-400" title={t("legend_opportunity_hint", "No linked assets or initiatives")}>
        <span class="inline-block h-3 w-3 rounded-sm border border-amber-300 bg-amber-100 dark:border-amber-700 dark:bg-amber-900/60" aria-hidden="true"></span>
        {t("legend_opportunity", "AI opportunity")}
      </span>
    </div>
    <div class="flex shrink-0 items-center gap-2">
      {#if expandable.length}
        <button
          type="button"
          class="inline-flex items-center gap-1 whitespace-nowrap rounded-lg border border-gray-300 bg-white px-2 py-1 text-xs text-gray-700 hover:bg-gray-100 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700"
          aria-pressed={allExpanded}
          onclick={toggleAll}
        >
          <svg class={`h-3 w-3 transition ${allExpanded ? "rotate-90" : ""}`} viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M7.2 14.8a.75.75 0 010-1.06L10.94 10 7.2 6.26a.75.75 0 111.06-1.06l4.27 4.27a.75.75 0 010 1.06l-4.27 4.27a.75.75 0 01-1.06 0z" /></svg>
          {allExpanded ? t("collapse_all", "Collapse all") : t("expand_all", "Expand all")}
        </button>
      {/if}
      <button
        type="button"
        role="switch"
        aria-checked={view.opportunities}
        class="inline-flex items-center gap-2 whitespace-nowrap rounded-lg px-2 py-1 text-xs text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
        onclick={setOpportunities}
      >
        <span>{t("only_opportunities", "Only opportunities")}</span>
        <span class={`relative inline-block h-4 w-7 shrink-0 rounded-full transition ${view.opportunities ? "bg-indigo-600" : "bg-gray-300 dark:bg-gray-600"}`}>
          <span class={`absolute top-0.5 left-0.5 h-3 w-3 rounded-full bg-white shadow transition ${view.opportunities ? "translate-x-3" : ""}`}></span>
        </span>
      </button>
      <select
        class="rounded-lg border border-gray-300 bg-white px-2 py-1 text-xs dark:border-gray-600 dark:bg-gray-800 dark:text-white"
        aria-label={tl("unit", "Business unit")}
        value={view.unit ?? ""}
        onchange={(e) => setUnit((e.currentTarget as HTMLSelectElement).value)}
      >
        <option value="">{tl("all_units", "All units")}</option>
        {#each units as u (u.code)}<option value={u.code}>{u.name}</option>{/each}
      </select>
    </div>
  </div>

  {#if notice}
    <p class="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:bg-amber-950/40 dark:text-amber-200">{notice}</p>
  {/if}
  {#if landscape?.truncated}
    <p class="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:bg-amber-950/40 dark:text-amber-200">{tl("truncated", "The landscape is too large: only the first {n} processes are shown.", { n: landscape.processes.length })}</p>
  {/if}

  {#if loading && !landscape}
    <p class="text-sm text-gray-500 dark:text-gray-400">{tl("loading", "Loading the process landscape…")}</p>
  {:else if forbidden}
    <p class="rounded-lg border border-gray-200 px-4 py-6 text-center text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">{tl("not_authorized", "You are not authorized to see this view.")}</p>
  {:else if error && !landscape}
    <p class="text-sm text-red-600 dark:text-red-400">{error}</p>
  {:else if landscape && !landscape.processes.length}
    <p class="rounded-lg border border-gray-200 px-4 py-6 text-center text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">{tl("empty", "No processes to show.")}</p>
  {:else if landscape}
    <!-- Porter's layout: both rows of activities lead to ONE margin chevron
         that spans the primary and the support activities. -->
    <div class="flex items-stretch gap-1.5">
      <div class="min-w-0 flex-1 space-y-3">
        <section aria-label={t("primary", "Primary activities")}>
          <h2 class="mb-1 text-[11px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">{t("primary", "Primary activities")}</h2>
          {#if !primaries.length}
            <p class="text-sm text-gray-400">{t("no_primary", "No primary activities to show.")}</p>
          {:else}
            <div class="flex items-stretch gap-0.5">
              {#each primaries as p, i (p.code)}
                <div
                  class={`min-w-0 flex-1 rounded-lg border p-2 transition ${tone(p, "block")} ${highlighted === p.code ? "ring-2 ring-indigo-500" : oppHint(p) ? "ring-2 ring-amber-400" : ""} ${blockDim(p) ? "opacity-30" : ""} ${p.context ? "opacity-60" : ""}`}
                  title={p.context ? tl("context_hint", "Shown to place processes of the selected unit") : undefined}
                >
                  <div class={`flex items-start gap-1 transition ${headDim(p) ? "opacity-30" : ""}`}>
                    <button type="button" class="min-w-0 flex-1 text-left" title={`${p.code} · ${p.name}`} onclick={() => select(p.code)}>
                      <span class="block font-mono text-sm font-bold leading-tight text-gray-900 dark:text-white">{p.code}</span>
                      <span class="line-clamp-2 text-[11px] leading-tight text-gray-600 dark:text-gray-300">{p.name}</span>
                    </button>
                    {@render expander(p)}
                  </div>
                  <div class={`mt-1 flex flex-wrap items-center gap-1.5 transition ${headDim(p) ? "opacity-30" : ""}`}>
                    {@render status(p)}
                    {@render counts(p)}
                  </div>
                  {@render subList(p, false)}
                </div>
                {#if i < primaries.length - 1}
                  <div class="flex w-3 shrink-0 items-center justify-center text-gray-300 dark:text-gray-600" aria-hidden="true">
                    <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor"><path d="M7.2 14.8a.75.75 0 010-1.06L10.94 10 7.2 6.26a.75.75 0 111.06-1.06l4.27 4.27a.75.75 0 010 1.06l-4.27 4.27a.75.75 0 01-1.06 0z" /></svg>
                  </div>
                {/if}
              {/each}
            </div>
          {/if}
        </section>

        <section aria-label={t("support", "Support activities")}>
          <h2 class="mb-1 text-[11px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">{t("support", "Support activities")}</h2>
          {#if !supports.length}
            <p class="text-sm text-gray-400">{t("no_support", "No support activities to show.")}</p>
          {:else}
            <div class="space-y-1.5">
              {#each supports as p (p.code)}
                <div
                  class={`rounded-lg border px-3 py-3 transition ${tone(p, "block")} ${highlighted === p.code ? "ring-2 ring-indigo-500" : oppHint(p) ? "ring-2 ring-amber-400" : ""} ${blockDim(p) ? "opacity-30" : ""} ${p.context ? "opacity-60" : ""}`}
                  title={p.context ? tl("context_hint", "Shown to place processes of the selected unit") : undefined}
                >
                  <div class={`flex items-center gap-2 transition ${headDim(p) ? "opacity-30" : ""}`}>
                    <button type="button" class="flex min-w-0 flex-1 items-baseline gap-2 text-left" title={`${p.code} · ${p.name}`} onclick={() => select(p.code)}>
                      <span class="shrink-0 font-mono text-sm font-bold text-gray-900 dark:text-white">{p.code}</span>
                      <span class="truncate text-xs text-gray-600 dark:text-gray-300">{p.name}</span>
                    </button>
                    {@render status(p)}
                    {@render counts(p)}
                    {@render expander(p)}
                  </div>
                  {@render subList(p, true)}
                </div>
              {/each}
            </div>
          {/if}
        </section>
      </div>

      <div
        class="flex w-[88px] shrink-0 items-center justify-center bg-indigo-600 pl-5 pr-3 text-sm font-semibold text-white dark:bg-indigo-500"
        style="clip-path: polygon(0 0, calc(100% - 22px) 0, 100% 50%, calc(100% - 22px) 100%, 0 100%, 14px 50%);"
      ><span class="tracking-wide">{t("margin", "Margin")}</span></div>
    </div>
  {/if}
</div>

{#if selected && landscape && index.has(selected)}
  <ProcessLandscapePanel code={selected} from="chain" {landscape} {lists} {langTick} onClose={closePanel} />
{/if}
