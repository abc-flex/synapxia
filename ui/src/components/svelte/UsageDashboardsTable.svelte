<script lang="ts">
  /**
   * UsageDashboardsTable — which dashboards are used and how well they work
   * (specs/008-usage-metrics US3: FR-011, FR-012, FR-014a).
   *
   * Sortable, searchable (name, type and source in every language), a "show
   * unused" toggle, per-row top errors loaded lazily, and CSV / Excel export of
   * exactly the visible rows.
   */
  import type { UsageDashboardRow, UsageErrors, UsagePeriod } from "@/types/api";
  import {
    fmtDate, fmtInt, fmtMs, fmtPct, getDashboardErrors, usageText, type UsageQuery,
  } from "@/lib/usageMetrics";
  import { labelsFor, listLabel, type ListLabels } from "@/lib/listLang";
  import { downloadFile, exportFileName, toCSV } from "@/lib/tableExport";
  import { toXlsx, XLSX_MIME } from "@/lib/xlsx";

  interface Props {
    rows: UsageDashboardRow[];
    period: UsagePeriod;
    query: UsageQuery;
    typeLabels: ListLabels;
    sourceLabels: ListLabels;
    statusLabels: ListLabels;
    execLabels: ListLabels;
    langTick: number;
  }
  let { rows, period, query, typeLabels, sourceLabels, statusLabels, execLabels, langTick }: Props = $props();

  type SortKey = "name" | "runs" | "attempts" | "users" | "success_rate" | "median_ms" | "last_run_at";
  let sortKey: SortKey = $state("runs");
  let sortDesc = $state(true);
  let search = $state("");
  let showUnused = $state(false);
  let expanded: number | null = $state(null);
  let errors: Record<number, UsageErrors | "loading" | "error"> = $state({});
  let exportOpen = $state(false);

  const t = (key: string, fallback: string, vars?: Record<string, string | number>) => {
    void langTick;
    return usageText(`dashboards.${key}`, fallback, vars);
  };
  const lbl = (labels: ListLabels, v: string) => {
    void langTick;
    return listLabel(labels, v) || v;
  };

  // Reset lazily loaded errors when the period / filter changes.
  $effect(() => {
    void query.dateFrom; void query.dateTo; void query.unit; void query.team;
    errors = {};
    expanded = null;
  });

  const haystack = (r: UsageDashboardRow) =>
    [r.name, ...Object.values(labelsFor(typeLabels, r.type) ?? {}), r.type,
      ...Object.values(labelsFor(sourceLabels, r.source) ?? {}), r.source].join(" ").toLowerCase();

  const visible = $derived.by(() => {
    const q = search.trim().toLowerCase();
    const list = rows.filter((r) => (showUnused || !r.unused) && (!q || haystack(r).includes(q)));
    const dir = sortDesc ? -1 : 1;
    return [...list].sort((a, b) => {
      const av = a[sortKey], bv = b[sortKey];
      if (sortKey === "name") return dir * String(av).localeCompare(String(bv));
      if (av == null && bv == null) return a.name.localeCompare(b.name);
      if (av == null) return 1;
      if (bv == null) return -1;
      return av < bv ? -dir : av > bv ? dir : a.name.localeCompare(b.name);
    });
  });
  const unusedCount = $derived(rows.filter((r) => r.unused).length);

  function sortBy(key: SortKey) {
    if (sortKey === key) sortDesc = !sortDesc;
    else {
      sortKey = key;
      sortDesc = key !== "name";
    }
  }

  async function toggle(r: UsageDashboardRow) {
    if (expanded === r.id) {
      expanded = null;
      return;
    }
    expanded = r.id;
    if (errors[r.id] && errors[r.id] !== "error") return;
    errors[r.id] = "loading";
    try {
      errors[r.id] = await getDashboardErrors(r.id, query);
    } catch {
      errors[r.id] = "error";
    }
  }

  const COLUMNS = $derived.by(() => {
    void langTick;
    return [
      { key: "name", label: t("col_name", "Dashboard") },
      { key: "type", label: t("col_type", "Type") },
      { key: "source", label: t("col_source", "Source") },
      { key: "status", label: t("col_status", "Status") },
      { key: "runs", label: t("col_runs", "Runs") },
      { key: "attempts", label: t("col_attempts", "Abandoned") },
      { key: "users", label: t("col_users", "Users") },
      { key: "success_rate", label: t("col_rate", "Success rate") },
      { key: "median_ms", label: t("col_median", "Median duration") },
      { key: "last_run_at", label: t("col_last", "Last run") },
    ];
  });

  function exportRows(kind: "csv" | "xlsx") {
    exportOpen = false;
    const data = visible.map((r) => ({
      name: r.name, type: lbl(typeLabels, r.type), source: lbl(sourceLabels, r.source),
      status: lbl(statusLabels, r.status), runs: r.runs, attempts: r.attempts, users: r.users,
      success_rate: r.success_rate, median_ms: r.median_ms,
      last_run_at: r.last_run_at ?? "",
    }));
    const name = exportFileName("usage-dashboards", period, { unit: query.unit, team: query.team });
    if (kind === "csv") {
      downloadFile(toCSV(data, COLUMNS, { bom: true }), `${name}.csv`, "text/csv;charset=utf-8");
    } else {
      const rowsOut = data.map((d) => COLUMNS.map((c) => (d as Record<string, string | number | null>)[c.key]));
      downloadFile(toXlsx(t("sheet", "Dashboards"), COLUMNS.map((c) => c.label), rowsOut), `${name}.xlsx`, XLSX_MIME);
    }
  }

  const th = "px-3 py-2 font-medium whitespace-nowrap";
  const sortable = (key: SortKey) => (sortKey === key ? (sortDesc ? " ↓" : " ↑") : "");
</script>

<section class="rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800">
  <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
    <h2 class="text-base font-semibold text-gray-900 dark:text-white">{t("title", "Dashboards")}</h2>
    <div class="flex flex-wrap items-center gap-2">
      <input type="search" bind:value={search} placeholder={t("search", "Search dashboards…")}
        class="w-48 rounded-lg border border-gray-300 bg-gray-50 px-3 py-1.5 text-sm text-gray-900 focus:border-indigo-500 focus:ring-indigo-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white" />
      <label class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
        <input type="checkbox" bind:checked={showUnused} class="rounded border-gray-300 text-indigo-600 dark:border-gray-600" />
        {t("show_unused", "Show unused ({n})", { n: unusedCount })}
      </label>
      <div class="relative">
        <button type="button" onclick={() => (exportOpen = !exportOpen)}
          title={usageText("export.button", "Export")} aria-label={usageText("export.button", "Export")}
          aria-haspopup="menu" aria-expanded={exportOpen}
          class="inline-flex items-center rounded-lg border border-gray-300 p-1.5 text-gray-600 hover:bg-gray-100 hover:text-gray-900 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700 dark:hover:text-white">
          <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v11m0 0-4-4m4 4 4-4M5 17v1.5A1.5 1.5 0 0 0 6.5 20h11a1.5 1.5 0 0 0 1.5-1.5V17" />
          </svg>
        </button>
        {#if exportOpen}
          <ul class="absolute right-0 z-20 mt-1 w-36 rounded-md border border-gray-200 bg-white py-1 text-sm shadow-lg dark:border-gray-600 dark:bg-gray-800">
            <li><button type="button" class="w-full px-3 py-1.5 text-left hover:bg-gray-100 dark:hover:bg-gray-700 dark:text-gray-200" onclick={() => exportRows("csv")}>CSV</button></li>
            <li><button type="button" class="w-full px-3 py-1.5 text-left hover:bg-gray-100 dark:hover:bg-gray-700 dark:text-gray-200" onclick={() => exportRows("xlsx")}>Excel (.xlsx)</button></li>
          </ul>
        {/if}
      </div>
    </div>
  </div>

  <div class="overflow-x-auto">
    <table class="w-full text-left text-sm text-gray-700 dark:text-gray-300">
      <thead class="bg-gray-50 text-xs uppercase text-gray-500 dark:bg-gray-700 dark:text-gray-400">
        <tr>
          <th class={th}><button type="button" onclick={() => sortBy("name")}>{t("col_name", "Dashboard")}{sortable("name")}</button></th>
          <th class={th}>{t("col_type", "Type")}</th>
          <th class={th}>{t("col_source", "Source")}</th>
          <th class={th}>{t("col_status", "Status")}</th>
          <th class="{th} text-right"><button type="button" onclick={() => sortBy("runs")}>{t("col_runs", "Runs")}{sortable("runs")}</button></th>
          <th class="{th} text-right" title={t("col_attempts_full", "Abandoned or refused: Cancelled + Unauthorized")}><button type="button" onclick={() => sortBy("attempts")}>{t("col_attempts", "Abandoned")}{sortable("attempts")}</button></th>
          <th class="{th} text-right"><button type="button" onclick={() => sortBy("users")}>{t("col_users", "Users")}{sortable("users")}</button></th>
          <th class="{th} text-right"><button type="button" onclick={() => sortBy("success_rate")}>{t("col_rate", "Success rate")}{sortable("success_rate")}</button></th>
          <th class="{th} text-right"><button type="button" onclick={() => sortBy("median_ms")}>{t("col_median", "Median duration")}{sortable("median_ms")}</button></th>
          <th class={th}><button type="button" onclick={() => sortBy("last_run_at")}>{t("col_last", "Last run")}{sortable("last_run_at")}</button></th>
        </tr>
      </thead>
      <tbody>
        {#each visible as r (r.id)}
          <tr class="border-b border-gray-100 hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-700/50 {r.unused ? 'text-gray-400 dark:text-gray-500' : ''}">
            <td class="px-3 py-2">
              <button type="button" class="flex items-center gap-1.5 text-left font-medium text-gray-900 dark:text-white"
                aria-expanded={expanded === r.id} onclick={() => toggle(r)} title={t("errors_toggle", "Show the most frequent errors")}>
                <span class="text-xs text-gray-400">{expanded === r.id ? "▾" : "▸"}</span>{r.name}
              </button>
            </td>
            <td class="whitespace-nowrap px-3 py-2">{lbl(typeLabels, r.type)}</td>
            <td class="whitespace-nowrap px-3 py-2">{lbl(sourceLabels, r.source)}</td>
            <td class="whitespace-nowrap px-3 py-2">
              {lbl(statusLabels, r.status)}
              {#if r.unused}<span class="ml-1 rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-500 dark:bg-gray-700 dark:text-gray-400">{t("unused_badge", "Unused")}</span>{/if}
            </td>
            <td class="px-3 py-2 text-right tabular-nums">{fmtInt(r.runs)}</td>
            <td class="px-3 py-2 text-right tabular-nums">{fmtInt(r.attempts)}</td>
            <td class="px-3 py-2 text-right tabular-nums">{fmtInt(r.users)}</td>
            <td class="px-3 py-2 text-right tabular-nums">{fmtPct(r.success_rate)}</td>
            <td class="px-3 py-2 text-right tabular-nums">{fmtMs(r.median_ms)}</td>
            <td class="whitespace-nowrap px-3 py-2">{fmtDate(r.last_run_at, true)}</td>
          </tr>
          {#if expanded === r.id}
            {@const e = errors[r.id]}
            <tr class="bg-gray-50 dark:bg-gray-900/40">
              <td colspan="10" class="px-6 py-3">
                {#if e === "loading" || e === undefined}
                  <p class="text-sm text-gray-500">{t("errors_loading", "Loading errors…")}</p>
                {:else if e === "error"}
                  <p class="text-sm text-red-600 dark:text-red-400">{t("errors_failed", "The errors could not be loaded.")}</p>
                {:else if !e.items.length}
                  <p class="text-sm text-gray-500">{t("errors_none", "No errors recorded in this period.")}</p>
                {:else}
                  <p class="mb-2 text-xs text-gray-500 dark:text-gray-400">
                    {t("errors_total", "{n} records with an error message in this period", { n: fmtInt(e.total_with_error) })}
                  </p>
                  <ul class="space-y-1 text-sm">
                    {#each e.items as item}
                      <li class="flex flex-wrap items-baseline gap-2">
                        <span class="w-12 shrink-0 text-right font-semibold tabular-nums text-gray-900 dark:text-white">{fmtInt(item.count)}</span>
                        <span class="text-gray-800 dark:text-gray-200">{item.message}</span>
                        <span class="text-xs text-gray-500 dark:text-gray-400">{item.statuses.map((s) => lbl(execLabels, s)).join(", ")}</span>
                      </li>
                    {/each}
                  </ul>
                {/if}
              </td>
            </tr>
          {/if}
        {:else}
          <tr><td colspan="10" class="px-3 py-6 text-center text-sm text-gray-500">{t("empty", "No dashboards match.")}</td></tr>
        {/each}
      </tbody>
    </table>
  </div>
</section>
