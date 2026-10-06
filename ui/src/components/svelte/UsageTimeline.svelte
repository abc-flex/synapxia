<script lang="ts">
  /**
   * UsageTimeline — runs and attempts per bucket, stacked by outcome
   * (specs/008-usage-metrics US2, FR-010, research R10).
   *
   * Hand-built SVG, no chart library. Palette: the dataviz reference
   * categorical slots 1–6 in fixed order, validated light and dark (adjacent
   * CVD ΔE ≥ 8.4, normal-vision ≥ 19.3). Light mode has three slots under 3:1
   * on the surface, so relief is shipped: legend + per-bar tooltip + a table
   * view. Cancelled / Unauthorized (attempts, not runs) carry a 45° texture as
   * a second channel and sit above the runs.
   */
  import type { UsageBucket, UsageBucketKind } from "@/types/api";
  import { fmtDate, fmtInt, usageText } from "@/lib/usageMetrics";
  import { listLabel, type ListLabels } from "@/lib/listLang";

  interface Props {
    buckets: UsageBucket[];
    bucket: UsageBucketKind;
    statusLabels: ListLabels;
    langTick: number;
  }
  let { buckets, bucket, statusLabels, langTick }: Props = $props();

  const SERIES = [
    { key: "SUCCESS", slot: 1, attempt: false },
    { key: "FAILED", slot: 2, attempt: false },
    { key: "TIMEOUT", slot: 3, attempt: false },
    { key: "INCOMPLETE", slot: 4, attempt: false },
    { key: "CANCELLED", slot: 5, attempt: true },
    { key: "UNAUTHORIZED", slot: 6, attempt: true },
  ] as const;

  const t = (key: string, fallback: string, vars?: Record<string, string | number>) => {
    void langTick;
    return usageText(`timeline.${key}`, fallback, vars);
  };
  const label = (key: string): string => {
    void langTick;
    if (key === "INCOMPLETE") return usageText("outcome.incomplete", "Incomplete");
    return listLabel(statusLabels, key) || key;
  };

  const patternId = `usage-hatch-${Math.random().toString(36).slice(2, 8)}`;
  const H = 260;
  const M = { top: 10, right: 8, bottom: 26, left: 44 };
  let width = $state(640);
  let showTable = $state(false);
  let hover: number | null = $state(null);
  let tipX = $state(0);

  const totals = $derived(buckets.map((b) => SERIES.reduce((n, s) => n + (b.outcomes[s.key] ?? 0), 0)));
  const yMax = $derived(niceMax(Math.max(1, ...totals)));
  const ticks = $derived([0, 0.25, 0.5, 0.75, 1].map((f) => Math.round(yMax * f)));
  const innerW = $derived(Math.max(10, width - M.left - M.right));
  const innerH = H - M.top - M.bottom;
  const step = $derived(buckets.length ? innerW / buckets.length : innerW);
  const barW = $derived(Math.max(2, Math.min(28, step * 0.7)));
  const labelEvery = $derived(Math.max(1, Math.ceil(buckets.length / Math.max(2, Math.floor(innerW / 64)))));
  const y = (v: number) => M.top + innerH - (v / yMax) * innerH;

  function niceMax(v: number): number {
    const mag = 10 ** Math.floor(Math.log10(v));
    const n = v / mag;
    const nice = n <= 1 ? 1 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 5 ? 5 : 10;
    return Math.max(4, nice * mag);
  }

  type Seg = { key: string; slot: number; attempt: boolean; y: number; h: number; top: boolean };
  function segments(b: UsageBucket): Seg[] {
    const out: Seg[] = [];
    let acc = 0;
    for (const s of SERIES) {
      const v = b.outcomes[s.key] ?? 0;
      if (!v) continue;
      const y0 = y(acc), y1 = y(acc + v);
      out.push({ key: s.key, slot: s.slot, attempt: s.attempt, y: y1, h: y0 - y1, top: false });
      acc += v;
    }
    if (out.length) out[out.length - 1].top = true;
    // 2px surface gap between stacked fills: each segment above the first
    // gives up its bottom 2px, so the baseline stays anchored.
    return out.map((s, i) => (i > 0 && s.h > 3 ? { ...s, h: s.h - 2 } : s));
  }

  /** Rect with only its top corners rounded (data end), r ≤ 4. */
  function topRounded(x: number, yy: number, w: number, h: number): string {
    const r = Math.min(4, w / 2, h);
    return `M${x},${yy + h}V${yy + r}Q${x},${yy} ${x + r},${yy}H${x + w - r}Q${x + w},${yy} ${x + w},${yy + r}V${yy + h}Z`;
  }

  function xLabel(b: UsageBucket): string {
    void langTick;
    const d = new Date(`${b.start}T00:00:00`);
    const lang = (typeof localStorage !== "undefined" && localStorage.getItem("lang")) === "es" ? "es-CO" : "en-US";
    return new Intl.DateTimeFormat(lang, bucket === "month" ? { month: "short", year: "2-digit" } : { month: "short", day: "numeric" }).format(d);
  }

  function rangeText(b: UsageBucket): string {
    return b.start === b.end ? fmtDate(b.start) : `${fmtDate(b.start)} – ${fmtDate(b.end)}`;
  }

  const summary = $derived.by(() => {
    void langTick;
    const runs = buckets.reduce((n, b) => n + SERIES.filter((s) => !s.attempt).reduce((m, s) => m + (b.outcomes[s.key] ?? 0), 0), 0);
    return t("aria", "Stacked bar chart of {n} periods, {runs} runs in total.", { n: buckets.length, runs });
  });

  function onMove(i: number, ev: PointerEvent) {
    hover = i;
    const host = (ev.currentTarget as SVGElement).ownerSVGElement?.getBoundingClientRect();
    tipX = host ? ev.clientX - host.left : 0;
  }
</script>

<section class="usage-viz flex h-full flex-col rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800">
  <div class="mb-2 flex flex-wrap items-center justify-between gap-2">
    <h2 class="text-base font-semibold text-gray-900 dark:text-white">
      {t("title", "Runs over time")}
    </h2>
    <button type="button" class="text-sm font-medium text-indigo-600 hover:underline dark:text-indigo-400"
      onclick={() => (showTable = !showTable)}>
      {showTable ? t("show_chart", "Show chart") : t("show_table", "Show as table")}
    </button>
  </div>

  <!-- Legend: always present (≥ 2 series); attempts set apart and textured -->
  <ul class="mb-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-600 dark:text-gray-300">
    {#each SERIES as s, i}
      {#if s.attempt && !SERIES[i - 1].attempt}
        <li class="ml-1 border-l border-gray-300 pl-3 font-medium text-gray-500 dark:border-gray-600 dark:text-gray-400">
          {t("attempts_group", "Abandoned or refused:")}
        </li>
      {/if}
      <li class="flex items-center gap-1.5">
        <svg width="12" height="12" aria-hidden="true">
          <rect width="12" height="12" rx="2" style="fill: var(--series-{s.slot})" />
          {#if s.attempt}<rect width="12" height="12" rx="2" fill="url(#{patternId})" />{/if}
        </svg>
        {label(s.key)}
      </li>
    {/each}
  </ul>

  {#if showTable}
    <div class="max-h-[17rem] overflow-auto">
      <table class="w-full text-left text-sm text-gray-700 dark:text-gray-300">
        <thead class="sticky top-0 bg-gray-50 text-xs uppercase text-gray-500 dark:bg-gray-700 dark:text-gray-400">
          <tr>
            <th class="px-3 py-2">{t("col_period", "Period")}</th>
            {#each SERIES as s}<th class="px-3 py-2 text-right">{label(s.key)}</th>{/each}
          </tr>
        </thead>
        <tbody>
          {#each buckets as b}
            <tr class="border-b border-gray-100 dark:border-gray-700">
              <td class="whitespace-nowrap px-3 py-1.5">{rangeText(b)}</td>
              {#each SERIES as s}<td class="px-3 py-1.5 text-right tabular-nums">{fmtInt(b.outcomes[s.key] ?? 0)}</td>{/each}
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {:else}
    <div class="relative" bind:clientWidth={width}>
      <svg {width} height={H} role="img" aria-label={summary} class="block select-none">
        <defs>
          <pattern id={patternId} width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <line x1="0" y1="0" x2="0" y2="5" stroke="var(--hatch)" stroke-width="1.6" />
          </pattern>
        </defs>

        <!-- recessive grid + y axis -->
        {#each ticks as tk}
          <line x1={M.left} x2={width - M.right} y1={y(tk)} y2={y(tk)} stroke="var(--grid)" stroke-width="1" />
          <text x={M.left - 6} y={y(tk) + 4} text-anchor="end" class="tick">{fmtInt(tk)}</text>
        {/each}

        {#each buckets as b, i}
          {@const x = M.left + i * step + (step - barW) / 2}
          {#each segments(b) as s}
            {#if s.top}
              <path d={topRounded(x, s.y, barW, s.h)} style="fill: var(--series-{s.slot})" opacity={hover === null || hover === i ? 1 : 0.45} />
              {#if s.attempt}<path d={topRounded(x, s.y, barW, s.h)} fill="url(#{patternId})" />{/if}
            {:else}
              <rect {x} y={s.y} width={barW} height={Math.max(0, s.h)} style="fill: var(--series-{s.slot})" opacity={hover === null || hover === i ? 1 : 0.45} />
              {#if s.attempt}<rect {x} y={s.y} width={barW} height={Math.max(0, s.h)} fill="url(#{patternId})" />{/if}
            {/if}
          {/each}
          {#if i % labelEvery === 0}
            <text x={M.left + i * step + step / 2} y={H - 8} text-anchor="middle" class="tick">{xLabel(b)}</text>
          {/if}
          <!-- hit target: the whole column, bigger than the mark -->
          <rect role="presentation" x={M.left + i * step} y={M.top} width={step} height={innerH} fill="transparent"
            onpointermove={(e) => onMove(i, e)} onpointerenter={(e) => onMove(i, e)} onpointerleave={() => (hover = null)} />
        {/each}

        <line x1={M.left} x2={width - M.right} y1={y(0)} y2={y(0)} stroke="var(--axis)" stroke-width="1" />
      </svg>

      {#if hover !== null && buckets[hover]}
        {@const b = buckets[hover]}
        <div class="pointer-events-none absolute top-2 z-10 w-52 rounded-md border border-gray-200 bg-white p-2.5 text-xs shadow-lg dark:border-gray-600 dark:bg-gray-900"
          style="left: {Math.min(Math.max(tipX + 12, 0), Math.max(0, width - 216))}px">
          <p class="mb-1.5 font-semibold text-gray-900 dark:text-white">{rangeText(b)}</p>
          <ul class="space-y-0.5">
            {#each SERIES as s}
              <li class="flex items-center justify-between gap-3 text-gray-600 dark:text-gray-300">
                <span class="flex items-center gap-1.5">
                  <span class="inline-block h-2.5 w-2.5 rounded-sm" style="background: var(--series-{s.slot})"></span>
                  {label(s.key)}
                </span>
                <span class="tabular-nums text-gray-900 dark:text-white">{fmtInt(b.outcomes[s.key] ?? 0)}</span>
              </li>
            {/each}
          </ul>
        </div>
      {/if}
    </div>
  {/if}
</section>

<style>
  .usage-viz {
    --series-1: #2a78d6;
    --series-2: #eb6834;
    --series-3: #1baf7a;
    --series-4: #eda100;
    --series-5: #e87ba4;
    --series-6: #008300;
    --hatch: rgba(255, 255, 255, 0.75);
    --grid: #ecebe8;
    --axis: #a3a29c;
    --tick: #6b6a65;
  }
  :global(.dark) .usage-viz {
    --series-1: #3987e5;
    --series-2: #d95926;
    --series-3: #199e70;
    --series-4: #c98500;
    --series-5: #d55181;
    --series-6: #008300;
    --hatch: rgba(26, 26, 25, 0.7);
    --grid: #33332f;
    --axis: #6b6a65;
    --tick: #a3a29c;
  }
  .tick {
    fill: var(--tick);
    font-size: 11px;
    font-variant-numeric: tabular-nums;
  }
</style>
