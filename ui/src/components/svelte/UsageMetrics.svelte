<script lang="ts">
  /**
   * UsageMetrics — the /ana/usage island (specs/008-usage-metrics, HU-AN07).
   *
   * Owns the period (presets + custom range), the unit/team/project filter chip, the
   * headline tiles, and feeds the timeline, dashboards table and adoption
   * sections. Data is fetched client-side on every change: an SSR snapshot
   * would be stale the moment the period changes. Every figure is computed by
   * the server (usage_service); this file only formats them.
   */
  import { onMount } from "svelte";
  import { apiErrorDetail } from "@/lib/api";
  import { getListItemsbyList } from "@/lib/list_items";
  import { labelsByValue, type ListLabels } from "@/lib/listLang";
  import {
    MAX_RANGE_DAYS, daysBetween, fmtChange, fmtDate, fmtInt, fmtMs, fmtPct, getUsageMetrics,
    presetRange, splitUnit, usageText, type ChangeKind, type UsageGroupKind, type UsagePreset,
    type UsageQuery,
  } from "@/lib/usageMetrics";
  import type { UsageMetrics } from "@/types/api";
  import UsageTimeline from "./UsageTimeline.svelte";
  import UsageDashboardsTable from "./UsageDashboardsTable.svelte";
  import UsageAdoption from "./UsageAdoption.svelte";

  let langTick = $state(0);
  const t = (key: string, fallback: string, vars?: Record<string, string | number>) => {
    void langTick;
    return usageText(key, fallback, vars);
  };

  // ── Period + filter ──────────────────────────────────────────────────
  const PRESETS: UsagePreset[] = ["7d", "30d", "90d", "12m"];
  let preset: UsagePreset | "custom" = $state("30d");
  const initial = presetRange("30d");
  let customFrom = $state(initial.dateFrom);
  let customTo = $state(initial.dateTo);
  let customError = $state("");
  let query: UsageQuery = $state({ ...initial, unit: null, team: null, project: null });
  let filterKind: UsageGroupKind | null = $state(null);
  let filterLabel = $state("");

  // ── Data ─────────────────────────────────────────────────────────────
  let data: UsageMetrics | null = $state(null);
  let loading = $state(false);
  let loadError = $state("");
  let seq = 0;
  let labels: Record<string, ListLabels> = $state({ exec: {}, type: {}, source: {}, status: {} });

  async function load() {
    const mine = ++seq;
    loading = true;
    loadError = "";
    try {
      const result = await getUsageMetrics(query);
      if (mine === seq) data = result;
    } catch (err) {
      // Keep the last good figures on screen; just say the refresh failed.
      if (mine === seq) loadError = apiErrorDetail(err, t("load_error", "The usage figures could not be loaded."));
    } finally {
      if (mine === seq) loading = false;
    }
  }

  function choosePreset(p: UsagePreset) {
    preset = p;
    customError = "";
    const r = presetRange(p);
    customFrom = r.dateFrom;
    customTo = r.dateTo;
    query = { ...query, ...r };
    load();
  }

  function applyCustom() {
    const span = daysBetween(customFrom, customTo);
    if (!customFrom || !customTo || Number.isNaN(span)) {
      customError = t("period.error_missing", "Choose a start and an end date.");
    } else if (span < 0) {
      customError = t("period.error_inverted", "The end date must not be before the start date.");
    } else if (span > MAX_RANGE_DAYS) {
      customError = t("period.error_long", "The period can span at most 24 months.");
    } else {
      customError = "";
      preset = "custom";
      query = { ...query, dateFrom: customFrom, dateTo: customTo };
      load();
    }
  }

  function setFilter(kind: UsageGroupKind, code: string, name: string) {
    const same = query[kind] === code;
    query = { ...query, unit: null, team: null, project: null, ...(same ? {} : { [kind]: code }) };
    filterKind = same ? null : kind;
    filterLabel = same ? "" : name;
    load();
  }

  function clearFilter() {
    query = { ...query, unit: null, team: null, project: null };
    filterKind = null;
    filterLabel = "";
    load();
  }

  onMount(() => {
    const onLang = () => (langTick += 1);
    window.addEventListener("languageChanged", onLang);
    load();
    const lists: [string, string][] = [
      ["exec", "EXECUTION_STATUS"], ["type", "DASHBOARD_TYPE"],
      ["source", "SOURCE_TYPE"], ["status", "DASHBOARD_STATUS"],
    ];
    Promise.allSettled(lists.map(([, code]) => getListItemsbyList(code, 0, 500))).then((res) => {
      const next = { ...labels };
      res.forEach((r, i) => {
        if (r.status === "fulfilled") next[lists[i][0]] = labelsByValue(r.value);
      });
      labels = next;
    });
    return () => window.removeEventListener("languageChanged", onLang);
  });

  // ── Tiles ────────────────────────────────────────────────────────────
  type Tile = { key: string; label: string; value: string; sub?: string; change: number | null; kind: ChangeKind; goodUp: boolean };
  const tiles = $derived.by((): Tile[] => {
    void langTick;
    if (!data) return [];
    const c = data.summary.current, ch = data.summary.change;
    return [
      { key: "runs", label: t("summary.runs", "Runs"), value: fmtInt(c.runs), change: ch.runs, kind: "ratio", goodUp: true },
      { key: "users", label: t("summary.users", "People who ran a dashboard"), value: fmtInt(c.users), change: ch.users, kind: "ratio", goodUp: true },
      { key: "dashboards", label: t("summary.dashboards", "Dashboards run"), value: fmtInt(c.dashboards), change: ch.dashboards, kind: "ratio", goodUp: true },
      { key: "rate", label: t("summary.success_rate", "Success rate"), value: fmtPct(c.success_rate),
        sub: t("summary.rate_hint", "Success ÷ (Success + Failed + Timeout)"), change: ch.success_rate, kind: "points", goodUp: true },
      { key: "median", label: t("summary.median", "Median duration"), value: fmtMs(c.median_ms),
        sub: t("summary.average", "Average {v}", { v: fmtMs(c.avg_ms) }), change: ch.median_ms, kind: "ms", goodUp: false },
      { key: "attempts", label: t("summary.attempts", "Abandoned or refused"), value: fmtInt(c.attempts),
        sub: t("summary.attempts_hint", "Cancelled + Unauthorized — not counted as runs"), change: ch.attempts, kind: "ratio", goodUp: false },
      { key: "incomplete", label: t("summary.incomplete", "Incomplete"), value: fmtInt(c.incomplete),
        sub: t("summary.incomplete_hint", "The browser closed before reporting the outcome"), change: ch.incomplete, kind: "ratio", goodUp: false },
    ];
  });

  const previousText = $derived.by(() => {
    void langTick;
    return data ? t("summary.vs_previous", "vs {from} – {to}", {
      from: fmtDate(data.period.previous_from), to: fmtDate(data.period.previous_to) }) : "";
  });

  const empty = $derived(!!data && data.summary.current.runs + data.summary.current.attempts === 0);

  function changeClass(dir: string, goodUp: boolean): string {
    if (dir === "flat") return "text-gray-500 dark:text-gray-400";
    const good = (dir === "up") === goodUp;
    return good ? "text-emerald-700 dark:text-emerald-400" : "text-rose-700 dark:text-rose-400";
  }

  const presetClass = (on: boolean) =>
    `rounded-md border px-2.5 py-1 text-sm font-medium transition-colors ${on
      ? "border-indigo-600 bg-indigo-600 text-white shadow-sm dark:border-indigo-500 dark:bg-indigo-500"
      : "border-gray-300 bg-white text-gray-700 hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:hover:border-indigo-400 dark:hover:bg-gray-700"}`;
  // usage-date: tight width, calendar icon right next to the date (styles at the end of the file)
  const dateInput = "usage-date rounded-lg border border-gray-300 bg-gray-50 py-1 pl-2 pr-1 text-sm tabular-nums text-gray-900 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:[color-scheme:dark]";
</script>

<div class="space-y-3">
  <!-- Period selector, one compact bar (FR-004) -->
  <div class="rounded-lg border border-gray-200 bg-white px-3 py-2 dark:border-gray-700 dark:bg-gray-800">
    <div class="flex flex-wrap items-center gap-x-3 gap-y-2">
      <div class="flex flex-wrap items-center gap-1" role="group" aria-label={t("period.label", "Period")}>
        {#each PRESETS as p}
          <button type="button" class={presetClass(preset === p)} aria-pressed={preset === p} onclick={() => choosePreset(p)}>
            {t(`period.${p}`, { "7d": "Last 7 days", "30d": "Last 30 days", "90d": "Last 90 days", "12m": "Last 12 months" }[p])}
          </button>
        {/each}
      </div>
      <form class="flex flex-wrap items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-2 py-1 dark:border-gray-600 dark:bg-gray-900/40" onsubmit={(e) => { e.preventDefault(); applyCustom(); }}>
        <label class="flex items-center gap-1 text-xs font-medium text-gray-600 dark:text-gray-300">
          {t("period.from", "From")}
          <input type="date" class={dateInput} bind:value={customFrom} />
        </label>
        <label class="flex items-center gap-1 text-xs font-medium text-gray-600 dark:text-gray-300">
          {t("period.to", "To")}
          <input type="date" class={dateInput} bind:value={customTo} />
        </label>
        <button type="submit" class={presetClass(preset === "custom")}>{t("period.apply", "Apply")}</button>
      </form>
    </div>
    {#if customError}<p class="mt-1 text-xs text-red-600 dark:text-red-400" role="alert">{customError}</p>{/if}
    {#if loadError}<p class="mt-1 text-xs text-red-600 dark:text-red-400" role="alert">{loadError}</p>{/if}
  </div>

  <!-- Scope note, filter chip, selected dates and status: outside the bar, left-aligned -->
  <div class="flex min-h-[1.5rem] flex-wrap items-center gap-2 text-xs">
    {#if data?.scope.restricted}
      <span class="rounded-md bg-amber-50 px-2 py-0.5 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300">
        {t("scope_note", "Limited to the {n} dashboards you manage", { n: data.scope.dashboards ?? 0 })}
      </span>
    {/if}
    {#if filterKind}
      <span class="inline-flex items-center gap-1 rounded-full bg-indigo-100 px-2.5 py-0.5 font-medium text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-200">
        <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M4 5h16l-6 7.5V18l-4 1.5v-7L4 5Z" /></svg>
        {filterKind === "unit" ? t("filter.unit", "Unit: {name}", { name: filterLabel })
          : filterKind === "team" ? t("filter.team", "Team: {name}", { name: filterLabel })
          : t("filter.project", "Project: {name}", { name: filterLabel })}
        <button type="button" class="ml-0.5 font-bold hover:text-indigo-950 dark:hover:text-white" aria-label={t("filter.clear", "Clear filter")} onclick={clearFilter}>×</button>
      </span>
    {:else if data}
      <!-- No filter yet: say how to set one, so the dates never stand alone -->
      <span class="inline-flex items-center gap-1 rounded-full border border-dashed border-gray-300 px-2.5 py-0.5 text-gray-500 dark:border-gray-600 dark:text-gray-400">
        <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M4 5h16l-6 7.5V18l-4 1.5v-7L4 5Z" /></svg>
        {t("filter.none", "No filter: select a row in Adoption to filter by unit, team or project")}
      </span>
    {/if}
    {#if data}
      <span class="text-gray-500 dark:text-gray-400" title={previousText}>
        <span class="font-medium text-gray-600 dark:text-gray-300">{t("period.label", "Period")}:</span>
        {fmtDate(data.period.date_from)} – {fmtDate(data.period.date_to)}
      </span>
    {/if}
    {#if loading}<span class="text-gray-500 dark:text-gray-400" aria-live="polite">{t("loading", "Loading…")}</span>{/if}
  </div>

  {#if !data && loading}
    <p class="py-10 text-center text-sm text-gray-500">{t("loading", "Loading…")}</p>
  {:else if data}
    <!-- Headline tiles (US1): compact; explanations move to the tooltip -->
    <div class="grid grid-cols-2 gap-2 sm:grid-cols-4 xl:grid-cols-7">
      {#each tiles as tile (tile.key)}
        {@const c = fmtChange(tile.change, tile.kind)}
        {@const v = splitUnit(tile.value)}
        <!-- min-w-0 + flex-wrap: on a narrow tile the change drops below the
             value instead of overflowing; units are smaller than the number. -->
        <div class="min-w-0 rounded-lg border border-gray-200 bg-white px-3 py-2 dark:border-gray-700 dark:bg-gray-800"
          title={[tile.label, tile.sub, previousText].filter(Boolean).join(" · ")}>
          <p class="truncate text-xs font-medium text-gray-500 dark:text-gray-400">{tile.label}</p>
          <div class="flex flex-wrap items-baseline justify-between gap-x-2">
            <p class="whitespace-nowrap text-xl font-semibold tabular-nums text-gray-900 dark:text-white">
              {v.num}{#if v.unit}<span class="ml-0.5 text-xs font-medium text-gray-500 dark:text-gray-400">{v.unit}</span>{/if}
            </p>
            <p class="whitespace-nowrap text-[11px] font-medium leading-tight {changeClass(c.dir, tile.goodUp)}">
              {c.dir === "up" ? "▲" : c.dir === "down" ? "▼" : "•"} {c.text}
            </p>
          </div>
        </div>
      {/each}
    </div>

    <!-- Adoption (its rows are the page filter) beside the timeline, right under
         the tiles, so a selection's effect shows at a glance. -->
    <div class="grid gap-3 xl:grid-cols-2">
      <UsageAdoption units={data.units} teams={data.teams} projects={data.projects} period={data.period}
        selected={{ unit: query.unit ?? null, team: query.team ?? null, project: query.project ?? null }}
        onselect={setFilter}
        onclear={clearFilter} {langTick} />

      {#if empty}
        <p class="flex items-center justify-center rounded-lg border border-dashed border-gray-300 p-8 text-center text-sm text-gray-500 dark:border-gray-600 dark:text-gray-400">
          {t("summary.empty", "No dashboard usage in this period.")}
        </p>
      {:else}
        <UsageTimeline buckets={data.timeline} bucket={data.period.bucket} statusLabels={labels.exec} {langTick} />
      {/if}
    </div>

    <UsageDashboardsTable rows={data.dashboards} period={data.period} {query}
      typeLabels={labels.type} sourceLabels={labels.source} statusLabels={labels.status}
      execLabels={labels.exec} {langTick} />
  {/if}
</div>

<style>
  /* Date inputs as wide as their content (date + calendar icon), so there is
     no gap before the icon. `field-sizing: content` (Chromium 123+) sizes the
     field to what it shows; elsewhere a fixed width is the fallback. */
  :global(input.usage-date) {
    width: 8.4rem;
  }
  @supports (field-sizing: content) {
    :global(input.usage-date) {
      field-sizing: content;
      width: auto;
      min-width: 0;
    }
  }
  :global(input.usage-date::-webkit-datetime-edit) {
    padding: 0;
  }
  :global(input.usage-date::-webkit-calendar-picker-indicator) {
    margin-left: 0.3rem;
    padding: 0;
    width: 0.95rem;
    height: 0.95rem;
    flex-shrink: 0;
    cursor: pointer;
    opacity: 0.7;
  }
  :global(input.usage-date::-webkit-calendar-picker-indicator:hover) {
    opacity: 1;
  }
</style>
