<script lang="ts">
  /**
   * UsageAdoption — adoption by business unit (expandable tree, rolled up), by
   * team and by project (specs/008-usage-metrics US4: FR-005, FR-013, FR-014,
   * FR-014a). Projects are reached through their owning team.
   *
   * Clicking a row asks the parent to filter the rest of the page by that unit
   * (including sub-units), team or project. This section itself is never
   * narrowed.
   */
  import type { UsagePeriod, UsageProjectRow, UsageTeamRow, UsageUnitNode } from "@/types/api";
  import { fmtInt, fmtPct, NO_TEAM, usageText, type UsageGroupKind } from "@/lib/usageMetrics";
  import { downloadFile, exportFileName, toCSV } from "@/lib/tableExport";
  import { toXlsx, XLSX_MIME } from "@/lib/xlsx";

  interface Props {
    units: UsageUnitNode[];
    teams: UsageTeamRow[];
    projects: UsageProjectRow[];
    period: UsagePeriod;
    selected: { unit: string | null; team: string | null; project: string | null };
    onselect: (kind: UsageGroupKind, code: string, name: string) => void;
    onclear: () => void;
    langTick: number;
  }
  let { units, teams, projects, period, selected, onselect, onclear, langTick }: Props = $props();

  let tab: UsageGroupKind = $state("unit");
  let open: Set<string> = $state(new Set());
  let exportOpen = $state(false);
  let seeded = false;
  const tipId = `usage-adoption-tip-${Math.random().toString(36).slice(2, 8)}`;

  const t = (key: string, fallback: string, vars?: Record<string, string | number>) => {
    void langTick;
    return usageText(`adoption.${key}`, fallback, vars);
  };

  // Top-level units start expanded one level (once per data set).
  $effect(() => {
    if (!seeded && units.length) {
      open = new Set(units.map((u) => u.code));
      seeded = true;
    }
  });

  type Flat = { node: UsageUnitNode; depth: number; path: string };
  function flatten(nodes: UsageUnitNode[], depth = 0, prefix = "", all = false, out: Flat[] = []): Flat[] {
    for (const n of nodes) {
      const path = prefix ? `${prefix} › ${n.name}` : n.name;
      out.push({ node: n, depth, path });
      if (all || open.has(n.code)) flatten(n.children, depth + 1, path, all, out);
    }
    return out;
  }
  const unitRows = $derived(flatten(units));

  function toggle(code: string) {
    const next = new Set(open);
    if (next.has(code)) next.delete(code);
    else next.add(code);
    open = next;
  }

  /** Team and project rows share one flat shape; `sub` is the project's team. */
  type GroupRow = {
    code: string; name: string; sub: string | null; none: boolean;
    members: number | null; users: number; adoption_rate: number | null;
    runs: number; success_rate: number | null;
  };
  const groupRows = $derived.by((): GroupRow[] => {
    void langTick;
    if (tab === "team") {
      return teams.map((r) => ({
        ...r, none: r.code === NO_TEAM, sub: null,
        name: r.code === NO_TEAM ? t("no_team", "No team") : r.name || r.code,
      }));
    }
    return projects.map((r) => ({
      ...r, none: r.code === NO_TEAM, sub: r.team_name ?? r.team ?? null,
      name: r.code === NO_TEAM ? t("no_project", "No project") : r.name || r.code,
    }));
  });

  const firstCol = $derived.by(() => {
    void langTick;
    return tab === "unit" ? t("col_unit", "Unit") : tab === "team" ? t("col_team", "Team") : t("col_project", "Project");
  });

  function exportRows(kind: "csv" | "xlsx") {
    exportOpen = false;
    const cols = [
      { key: "name", label: firstCol },
      ...(tab === "project" ? [{ key: "sub", label: t("col_team", "Team") }] : []),
      { key: "members", label: t("col_members", "Members") },
      { key: "users", label: t("col_users_full", "Users who ran a dashboard") },
      { key: "adoption_rate", label: t("col_adoption", "Adoption") },
      { key: "runs", label: t("col_runs", "Runs") },
      { key: "success_rate", label: t("col_rate", "Success rate") },
    ];
    const data: Record<string, unknown>[] = tab === "unit"
      ? flatten(units, 0, "", true).map(({ node, path }) => ({ ...node, name: path }))
      : groupRows;
    const name = exportFileName(`usage-${tab}s`, period);
    if (kind === "csv") {
      downloadFile(toCSV(data, cols, { bom: true }), `${name}.csv`, "text/csv;charset=utf-8");
    } else {
      const rows = data.map((d) => cols.map((c) => (d[c.key] as string | number | null | undefined) ?? null));
      const sheet = { unit: t("sheet_units", "Units"), team: t("sheet_teams", "Teams"), project: t("sheet_projects", "Projects") }[tab];
      downloadFile(toXlsx(sheet, cols.map((c) => c.label), rows), `${name}.xlsx`, XLSX_MIME);
    }
  }

  const th = "px-2 py-1.5 font-medium whitespace-nowrap";
  const hint = $derived.by(() => {
    void langTick;
    if (tab === "unit") return t("hint_unit", "Each unit includes its sub-units. Select a row to filter the page by it.");
    if (tab === "team") return t("hint_team", "A run counts in every team its user belonged to at the time, so team totals can exceed the overall total. Select a row to filter the page by it.");
    return t("hint_project", "A run counts in the active projects of its user's team at the time (within the project's dates), so project totals can exceed the overall total. Select a row to filter the page by it.");
  });
  const isSelected = (kind: UsageGroupKind, code: string) => selected[kind] === code;
  const tabClass = (on: boolean) =>
    `whitespace-nowrap rounded px-2 py-0.5 text-xs font-medium ${on
      ? "bg-white text-indigo-700 shadow-sm dark:bg-gray-900 dark:text-indigo-300"
      : "text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white"}`;
  const rowClass = (on: boolean) =>
    `cursor-pointer border-b border-gray-100 dark:border-gray-700 ${on
      ? "bg-indigo-50 dark:bg-indigo-900/30"
      : "hover:bg-gray-50 dark:hover:bg-gray-700/50"}`;
</script>

{#snippet bar(rate: number | null)}
  <span class="flex items-center justify-end gap-2">
    <span class="hidden h-1.5 w-16 overflow-hidden rounded-full bg-gray-200 2xl:inline-block dark:bg-gray-700">
      <span class="block h-full rounded-full bg-indigo-500" style="width: {Math.round((rate ?? 0) * 100)}%"></span>
    </span>
    <span class="w-12 text-right tabular-nums">{fmtPct(rate, 0)}</span>
  </span>
{/snippet}

<section class="flex h-full flex-col rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800">
  <div class="mb-2 flex flex-wrap items-center justify-between gap-2">
    <div class="flex flex-wrap items-center gap-x-3 gap-y-1">
      <h2 class="flex items-center gap-1.5 text-base font-semibold text-gray-900 dark:text-white">
        {t("title", "Adoption")}
        <!-- Help: a styled tooltip on hover and keyboard focus -->
        <span class="group relative inline-flex">
          <button type="button" aria-describedby={tipId} aria-label={t("help", "How adoption is counted")}
            class="rounded-full text-gray-400 hover:text-indigo-600 focus:text-indigo-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 dark:text-gray-500 dark:hover:text-indigo-400">
            <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
              <circle cx="12" cy="12" r="9" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M9.6 9.2a2.5 2.5 0 1 1 3.4 2.3c-.6.3-1 .8-1 1.5v.5" />
              <circle cx="12" cy="16.8" r=".9" fill="currentColor" stroke="none" />
            </svg>
          </button>
          <span id={tipId} role="tooltip"
            class="pointer-events-none invisible absolute -left-2 top-full z-30 mt-2 w-72 rounded-lg bg-gray-900 px-3 py-2 text-xs font-normal leading-relaxed text-white opacity-0 shadow-lg transition-opacity duration-150 group-focus-within:visible group-focus-within:opacity-100 group-hover:visible group-hover:opacity-100 dark:bg-gray-700">
            <!-- Opens below and to the right of the icon: clear of the sidebar and of the tabs -->
            <span class="absolute -top-1 left-3 h-2 w-2 rotate-45 bg-gray-900 dark:bg-gray-700"></span>
            {hint}
          </span>
        </span>
      </h2>
      <div class="inline-flex rounded-md bg-gray-100 p-0.5 dark:bg-gray-700" role="tablist">
        <button type="button" role="tab" aria-selected={tab === "unit"} class={tabClass(tab === "unit")} onclick={() => (tab = "unit")}>{t("tab_unit", "By unit")}</button>
        <button type="button" role="tab" aria-selected={tab === "team"} class={tabClass(tab === "team")} onclick={() => (tab = "team")}>{t("tab_team", "By team")}</button>
        <button type="button" role="tab" aria-selected={tab === "project"} class={tabClass(tab === "project")} onclick={() => (tab = "project")}>{t("tab_project", "By project")}</button>
      </div>
    </div>
    <div class="flex items-center gap-2">
      {#if selected.unit || selected.team || selected.project}
        <button type="button" onclick={onclear}
          class="rounded-lg px-2.5 py-1 text-sm font-medium text-indigo-700 hover:bg-indigo-50 dark:text-indigo-300 dark:hover:bg-indigo-900/30">
          × {usageText("filter.clear", "Clear filter")}
        </button>
      {/if}
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

  <div class="min-h-0 max-h-[19rem] flex-1 overflow-auto">
    <table class="w-full text-left text-sm text-gray-700 dark:text-gray-300">
      <thead class="sticky top-0 z-10 bg-gray-50 text-xs uppercase text-gray-500 dark:bg-gray-700 dark:text-gray-400">
        <tr>
          <th class={th}>{firstCol}</th>
          <th class="{th} text-right">{t("col_members", "Members")}</th>
          <th class="{th} text-right" title={t("col_users_full", "Users who ran a dashboard")}>{t("col_users", "Users")}</th>
          <th class="{th} text-right">{t("col_adoption", "Adoption")}</th>
          <th class="{th} text-right">{t("col_runs", "Runs")}</th>
          <th class="{th} text-right">{t("col_rate", "Success rate")}</th>
        </tr>
      </thead>
      <tbody>
        {#if tab === "unit"}
          {#each unitRows as { node, depth } (node.code)}
            <tr class={rowClass(isSelected("unit", node.code))} onclick={() => onselect("unit", node.code, node.name)}>
              <td class="px-2 py-1.5">
                <span class="flex items-center gap-1" style="padding-left: {depth * 1.25}rem">
                  {#if node.children.length}
                    <button type="button" class="w-5 text-xs text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
                      aria-expanded={open.has(node.code)} aria-label={t("expand", "Expand or collapse")}
                      onclick={(e) => { e.stopPropagation(); toggle(node.code); }}>
                      {open.has(node.code) ? "▾" : "▸"}
                    </button>
                  {:else}<span class="w-5"></span>{/if}
                  <span class="font-medium text-gray-900 dark:text-white">{node.name}</span>
                  {#if node.children.length && node.direct_members}
                    <span class="text-xs text-gray-500 dark:text-gray-400">· {t("direct", "{n} direct", { n: node.direct_members })}</span>
                  {/if}
                </span>
              </td>
              <td class="px-2 py-1.5 text-right tabular-nums">{fmtInt(node.members)}</td>
              <td class="px-2 py-1.5 text-right tabular-nums">{fmtInt(node.users)}</td>
              <td class="px-2 py-1.5">{@render bar(node.adoption_rate)}</td>
              <td class="px-2 py-1.5 text-right tabular-nums">{fmtInt(node.runs)}</td>
              <td class="px-2 py-1.5 text-right tabular-nums">{fmtPct(node.success_rate)}</td>
            </tr>
          {:else}
            <tr><td colspan="6" class="px-3 py-6 text-center text-sm text-gray-500">{t("empty", "No data for this period.")}</td></tr>
          {/each}
        {:else}
          {#each groupRows as r (r.code)}
            <tr class={rowClass(isSelected(tab, r.code))} onclick={() => onselect(tab, r.code, r.name)}>
              <td class="px-2 py-1.5">
                <span class="font-medium text-gray-900 dark:text-white {r.none ? 'italic' : ''}">{r.name}</span>
                {#if r.sub}<span class="ml-1 text-xs text-gray-500 dark:text-gray-400">· {r.sub}</span>{/if}
              </td>
              <td class="px-2 py-1.5 text-right tabular-nums">{r.members == null ? "—" : fmtInt(r.members)}</td>
              <td class="px-2 py-1.5 text-right tabular-nums">{fmtInt(r.users)}</td>
              <td class="px-2 py-1.5">{#if r.none}<span class="block text-right">—</span>{:else}{@render bar(r.adoption_rate)}{/if}</td>
              <td class="px-2 py-1.5 text-right tabular-nums">{fmtInt(r.runs)}</td>
              <td class="px-2 py-1.5 text-right tabular-nums">{fmtPct(r.success_rate)}</td>
            </tr>
          {:else}
            <tr><td colspan="6" class="px-3 py-6 text-center text-sm text-gray-500">
              {tab === "project" ? t("empty_projects", "There are no active projects yet.") : t("empty", "No data for this period.")}
            </td></tr>
          {/each}
        {/if}
      </tbody>
    </table>
  </div>
</section>
