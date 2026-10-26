<script lang="ts">
  /**
   * ProcessMap — the /proc/process_map island (specs/010-process-landscape-views,
   * HU-PR06, US2).
   *
   * Hand-built SVG, no graph library (research R1). One level at a time
   * (amended 2026-10-25): the overview shows the top-level processes in two
   * lanes (Primary on top, Support below) in the Value Chain's order; the "+"
   * marker of a process (BPMN's collapsed sub-process) replaces it with that
   * process's internal diagram — a pool with its sub-processes ordered by
   * their sequence flows, start and end events, and the outside processes they
   * relate to in a lane below — with Back and a breadcrumb to return.
   * Relations are drawn after their BPMN counterpart (RELATION_STYLES, shared
   * with the legend, which can be shown or hidden). Search, focus/dim, pan and
   * zoom; the view state lives in the address (`in` = drilled process).
   */
  import { onMount } from "svelte";
  import { apiErrorDetail } from "@/lib/api";
  import { listLabel } from "@/lib/listLang";
  import {
    END_NODE, RELATION_TYPES, START_NODE, ancestors, byCode, connectorPath, drillPath,
    getLandscape, isForbidden, landscapeText, layoutDrill, layoutOverview, loadLandscapeLists,
    mergeEdges, neighborhood, readViewState, relationStyle, visibleAncestor, writeViewState,
    type LandscapeLists, type MapNode, type MarkerKind, type ViewState,
  } from "@/lib/processLandscape";
  import type { LandscapeProcess, ProcessLandscape } from "@/types/api";
  import ProcessLandscapePanel from "./ProcessLandscapePanel.svelte";

  let langTick = $state(0);
  const t = (key: string, fallback: string, vars?: Record<string, string | number>) => {
    void langTick;
    return landscapeText("process_map", key, fallback, vars);
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
  let focus = $state<string | null>(null);
  let panelOpen = $state(false);
  let showLegend = $state(true);
  let query = $state("");
  let searchOpen = $state(false);
  let seq = 0;

  // Viewport (pan / zoom)
  let boxW = $state(800);
  let boxH = $state(560);
  let scale = $state(1);
  let tx = $state(0);
  let ty = $state(0);
  let drag: { x: number; y: number; tx: number; ty: number } | null = null;

  const markerId = `pm-${Math.random().toString(36).slice(2, 8)}`;
  const ALL_TYPES = new Set(RELATION_TYPES);
  const index = $derived(landscape ? byCode(landscape) : new Map<string, LandscapeProcess>());
  const drill = $derived(view.drill && index.get(view.drill)?.child_order.length ? view.drill : null);
  const expanded = $derived(drillPath(drill, index));
  const enabled = $derived(new Set(view.types ?? RELATION_TYPES));
  const internal = $derived(new Set(drill ? index.get(drill)?.child_order ?? [] : []));
  // Layout always uses every relation type, so hiding a type never moves boxes.
  const layoutEdges = $derived.by(() => {
    if (!landscape) return [];
    const all = mergeEdges(landscape.relations, expanded, ALL_TYPES, index);
    return drill ? all.filter((e) => internal.has(e.source) || internal.has(e.target)) : all;
  });
  const edges = $derived(layoutEdges.filter((e) => enabled.has(e.type)));
  const layout = $derived(
    !landscape
      ? { nodes: [], lanes: [], eventEdges: [], width: 0, height: 0 }
      : drill
        ? layoutDrill(drill, layoutEdges, index)
        : layoutOverview(landscape, index),
  );
  const nodeAt = $derived(new Map(layout.nodes.map((n) => [n.code, n])));
  const trail = $derived(drill ? [...ancestors(drill, index)].reverse().concat(drill) : []);
  // Focus dims the rest only when the focused process is a box of the level on
  // screen. (A focus left on a drilled process used to fade every connector of
  // its internal diagram to 10%, so its flow looked missing.)
  const focusVisible = $derived.by((): string | null => {
    if (!focus || !index.has(focus)) return null;
    const v = visibleAncestor(focus, expanded, index);
    return nodeAt.has(v) ? v : null;
  });
  const lit = $derived.by((): Set<string> | null => {
    if (!focusVisible || !landscape || !focus) return null;
    return new Set([...neighborhood(focus, landscape, index)].map((c) => visibleAncestor(c, expanded, index)));
  });
  const results = $derived.by(() => {
    const q = query.trim().toLowerCase();
    if (!q || !landscape) return [];
    return landscape.processes
      .filter((p) => p.code.toLowerCase().includes(q) || p.name.toLowerCase().includes(q))
      .slice(0, 8);
  });

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
      if (applyFocus && view.focus) focusOn(view.focus, true, !view.drill);
      requestAnimationFrame(() => {
        fit();
        if (focus) centerOn(focus);
      });
    } catch (err) {
      if (mine !== seq) return;
      forbidden = isForbidden(err);
      error = apiErrorDetail(err, tl("load_error", "The process landscape could not be loaded."));
    } finally {
      if (mine === seq) loading = false;
    }
  }

  function save(patch: Partial<ViewState>) {
    view = { ...view, ...patch };
    writeViewState(view);
  }

  // ── Levels ────────────────────────────────────────────────────────────
  function drillInto(code: string | null) {
    // A new level starts unfocused, so its whole flow is visible.
    focus = null;
    panelOpen = false;
    save({ drill: code, focus: null });
    requestAnimationFrame(fit);
  }

  function back() {
    drillInto(drill ? index.get(drill)?.display_parent ?? null : null);
  }

  // ── Focus, selection ──────────────────────────────────────────────────
  /** `place` moves the map to the level where `code` is drawn as a box. */
  function focusOn(code: string, openPanel: boolean, place = false) {
    if (!index.has(code)) {
      notice = tl("focus_not_found", "The process in the address is not in this view.");
      save({ focus: null });
      return;
    }
    focus = code;
    panelOpen = openPanel;
    notice = "";
    save({ focus: code, ...(place ? { drill: index.get(code)?.display_parent ?? null } : {}) });
  }

  function clearFocus() {
    focus = null;
    panelOpen = false;
    save({ focus: null });
  }

  function choose(code: string) {
    query = "";
    searchOpen = false;
    focusOn(code, true, true);
    requestAnimationFrame(() => { fit(); centerOn(code); });
  }

  function toggleType(type: string) {
    const next = new Set(enabled);
    if (next.has(type)) next.delete(type);
    else next.add(type);
    const all = RELATION_TYPES.every((x) => next.has(x));
    save({ types: all ? null : RELATION_TYPES.filter((x) => next.has(x)) });
  }

  function setUnit(unit: string) {
    save({ unit: unit || null });
    load();
  }

  // ── Pan / zoom ────────────────────────────────────────────────────────
  function fit() {
    if (!layout.width || !layout.height) return;
    const s = Math.min((boxW - 32) / layout.width, (boxH - 32) / layout.height, 1.2);
    scale = Math.max(0.2, s);
    tx = (boxW - layout.width * scale) / 2;
    ty = Math.max(16, (boxH - layout.height * scale) / 2);
  }

  function centerOn(code: string) {
    const n = nodeAt.get(visibleAncestor(code, expanded, index));
    if (!n) return;
    tx = boxW / 2 - (n.x + n.w / 2) * scale;
    ty = boxH / 2 - (n.y + n.h / 2) * scale;
  }

  function zoom(factor: number, cx = boxW / 2, cy = boxH / 2) {
    const next = Math.min(3, Math.max(0.2, scale * factor));
    tx = cx - ((cx - tx) * next) / scale;
    ty = cy - ((cy - ty) * next) / scale;
    scale = next;
  }

  function onWheel(e: WheelEvent) {
    e.preventDefault();
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    zoom(e.deltaY < 0 ? 1.1 : 1 / 1.1, e.clientX - rect.left, e.clientY - rect.top);
  }

  function onPointerDown(e: PointerEvent) {
    if ((e.target as Element).closest("[data-node]")) return;
    drag = { x: e.clientX, y: e.clientY, tx, ty };
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
  }

  function onPointerMove(e: PointerEvent) {
    if (!drag) return;
    tx = drag.tx + e.clientX - drag.x;
    ty = drag.ty + e.clientY - drag.y;
  }

  const onPointerUp = () => (drag = null);

  onMount(() => {
    const onLang = () => (langTick += 1);
    window.addEventListener("languageChanged", onLang);
    try { showLegend = localStorage.getItem("process_map_legend") !== "0"; } catch { /* default */ }
    loadLandscapeLists().then((l) => (lists = l));
    if (view.unit) getLandscape(null).then((l) => (units = unitsOf(l))).catch(() => {});
    load(true);
    return () => window.removeEventListener("languageChanged", onLang);
  });

  function toggleLegend() {
    showLegend = !showLegend;
    try { localStorage.setItem("process_map_legend", showLegend ? "1" : "0"); } catch { /* per-viewer only */ }
  }

  // ── Drawing helpers ───────────────────────────────────────────────────
  const clip = (s: string, n: number) => (s.length > n ? `${s.slice(0, n - 1)}…` : s);
  const relLabel = (type: string) => {
    void langTick;
    return listLabel(lists.relation, type) || type;
  };
  const statusLabel = (p: LandscapeProcess) => {
    void langTick;
    return listLabel(lists.status, p.status) || p.status;
  };
  const nodeDim = (n: MapNode) => lit !== null && !lit.has(n.code);
  const edgeDim = (source: string, target: string) =>
    focusVisible !== null && source !== focusVisible && target !== focusVisible;
  const marked = (p: LandscapeProcess) => p.status === "DRAFT" || p.status === "REVIEW";

  function nodeClass(p: LandscapeProcess, n: MapNode): string {
    if (n.kind === "external") return "fill-gray-50 stroke-gray-400 dark:fill-gray-900 dark:stroke-gray-500";
    return p.type === "PRIMARY"
      ? "fill-white stroke-indigo-400 dark:fill-gray-900 dark:stroke-indigo-500"
      : "fill-white stroke-gray-400 dark:fill-gray-900 dark:stroke-gray-500";
  }

  function laneClass(kind: string): string {
    switch (kind) {
      case "primary": return "fill-indigo-50/60 dark:fill-indigo-950/20";
      case "pool": return "fill-white stroke-gray-300 dark:fill-gray-900/60 dark:stroke-gray-600";
      case "external": return "fill-transparent stroke-gray-300 dark:stroke-gray-600";
      default: return "fill-gray-100/80 dark:fill-gray-900/60";
    }
  }

  function laneLabel(kind: string): string {
    if (kind === "primary") return t("primary", "Primary");
    if (kind === "support") return t("support", "Support");
    if (kind === "external") return t("outside", "Related processes outside {name}", { name: drill ? index.get(drill)?.name ?? drill : "" });
    return "";
  }

  const markerShapes: Record<Exclude<MarkerKind, "none">, string> = {
    arrow: '<path d="M0,0 L10,5 L0,10 z" fill="currentColor" />',
    open: '<path d="M0,0 L10,5 L0,10" fill="none" stroke="currentColor" stroke-width="1.5" />',
    diamond: '<path d="M0,5 L5,0 L10,5 L5,10 z" fill="currentColor" />',
    circle: '<circle cx="5" cy="5" r="4" fill="white" stroke="currentColor" stroke-width="1.5" />',
  };
  const markerRef = (type: string, end: "start" | "end") => {
    const kind = relationStyle(type)[end];
    return kind === "none" ? undefined : `url(#${markerId}-${type}-${end})`;
  };
  const btn = "rounded-md border border-gray-300 bg-white px-2 py-1 text-sm shadow-sm hover:bg-gray-100 dark:border-gray-600 dark:bg-gray-800 dark:text-white dark:hover:bg-gray-700";
</script>

<div class="space-y-3">
  <!-- One compact row: short subtitle (truncated, full text on hover) + controls -->
  <div class="flex flex-wrap items-center gap-x-3 gap-y-2 md:flex-nowrap">
    <p class="min-w-0 flex-1 truncate text-sm text-gray-600 dark:text-gray-400" title={t("subtitle", "Processes and their BPMN relations. Use + to open a process.")}>{t("subtitle", "Processes and their BPMN relations. Use + to open a process.")}</p>
    <div class="flex shrink-0 items-center gap-2">
      <select
        class="rounded-lg border border-gray-300 bg-white py-1 pl-2 pr-7 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
        aria-label={tl("unit", "Business unit")}
        title={tl("unit", "Business unit")}
        value={view.unit ?? ""}
        onchange={(e) => setUnit((e.currentTarget as HTMLSelectElement).value)}
      >
        <option value="">{tl("all_units", "All units")}</option>
        {#each units as u (u.code)}<option value={u.code}>{u.name}</option>{/each}
      </select>
      <div class="relative">
        <input
          type="search"
          class="w-44 rounded-lg border border-gray-300 bg-white px-2.5 py-1 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
          placeholder={t("search", "Search process")}
          aria-label={t("search", "Search process")}
          bind:value={query}
          onfocus={() => (searchOpen = true)}
          onblur={() => setTimeout(() => (searchOpen = false), 150)}
          onkeydown={(e) => { if (e.key === "Enter" && results[0]) choose(results[0].code); }}
        />
        {#if searchOpen && query.trim()}
          <ul class="absolute right-0 z-20 mt-1 max-h-72 w-72 overflow-y-auto rounded-lg border border-gray-200 bg-white py-1 shadow-lg dark:border-gray-700 dark:bg-gray-800">
            {#each results as r (r.code)}
              <li>
                <button type="button" class="flex w-full items-baseline gap-2 px-3 py-1.5 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700" onmousedown={() => choose(r.code)}>
                  <span class="font-mono text-xs font-semibold text-gray-700 dark:text-gray-200">{r.code}</span>
                  <span class="text-gray-900 dark:text-white">{r.name}</span>
                </button>
              </li>
            {:else}
              <li class="px-3 py-1.5 text-sm text-gray-500">{t("no_results", "No matching process")}</li>
            {/each}
          </ul>
        {/if}
      </div>
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
    <!-- Map frame: the diagram, and the legend docked on its right -->
    <div class="flex h-[72vh] min-h-[420px] overflow-hidden rounded-xl border border-gray-200 dark:border-gray-700">
    <div class="relative min-w-0 flex-1">
      <!-- Level: Back + breadcrumb -->
      {#if drill}
        <div class={`absolute left-2 top-2 z-10 flex items-center gap-2 ${focus ? "max-w-[calc(100%-20rem)]" : "max-w-[calc(100%-14rem)]"}`}>
          <button type="button" class={`${btn} inline-flex items-center gap-1 text-xs`} onclick={back}>
            <svg class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M16.7 10a.75.75 0 01-.75.75H6.11l3.47 3.47a.75.75 0 11-1.06 1.06L3.77 10.53a.75.75 0 010-1.06l4.75-4.75a.75.75 0 111.06 1.06L6.11 9.25h9.84a.75.75 0 01.75.75z" /></svg>
            {t("back", "Back")}
          </button>
          <nav class="flex min-w-0 items-center gap-1 truncate rounded-md bg-white/90 px-2 py-1 text-xs text-gray-600 shadow-sm dark:bg-gray-800/90 dark:text-gray-300" aria-label={t("levels", "Levels")}>
            <button type="button" class="shrink-0 hover:text-indigo-600 hover:underline dark:hover:text-indigo-400" onclick={() => drillInto(null)}>{t("overview", "All processes")}</button>
            {#each trail as code (code)}
              <span aria-hidden="true">›</span>
              {#if code === drill}
                <span class="truncate font-semibold text-gray-900 dark:text-white">{code} · {index.get(code)?.name ?? code}</span>
              {:else}
                <button type="button" class="truncate hover:text-indigo-600 hover:underline dark:hover:text-indigo-400" onclick={() => drillInto(code)}>{code} · {index.get(code)?.name ?? code}</button>
              {/if}
            {/each}
          </nav>
        </div>
      {/if}

      <!-- Viewport controls: Clear focus (when focused), +, −, Fit, Legends — one height, one type size -->
      <div class="absolute right-2 top-2 z-10 flex h-7 items-stretch gap-1">
        {#if focus}
          <button type="button" class={`${btn} inline-flex items-center whitespace-nowrap text-xs`} onclick={clearFocus}>{t("clear_focus", "Clear focus")}</button>
        {/if}
        <button type="button" class={`${btn} inline-flex items-center`} title={t("zoom_in", "Zoom in")} aria-label={t("zoom_in", "Zoom in")} onclick={() => zoom(1.2)}>+</button>
        <button type="button" class={`${btn} inline-flex items-center`} title={t("zoom_out", "Zoom out")} aria-label={t("zoom_out", "Zoom out")} onclick={() => zoom(1 / 1.2)}>−</button>
        <button type="button" class={`${btn} inline-flex items-center text-xs`} onclick={fit}>{t("fit", "Fit")}</button>
        <button
          type="button"
          class={`${btn} inline-flex items-center gap-1 text-xs ${showLegend ? "!border-indigo-400 !bg-indigo-50 text-indigo-700 dark:!bg-indigo-950/60 dark:text-indigo-300" : ""}`}
          title={t("toggle_legend", "Show or hide the legends")}
          aria-pressed={showLegend}
          onclick={toggleLegend}
        >
          <svg class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M3 5.25A.75.75 0 013.75 4.5h1.5a.75.75 0 010 1.5h-1.5A.75.75 0 013 5.25zm5 0a.75.75 0 01.75-.75h7.5a.75.75 0 010 1.5h-7.5A.75.75 0 018 5.25zM3 10a.75.75 0 01.75-.75h1.5a.75.75 0 010 1.5h-1.5A.75.75 0 013 10zm5 0a.75.75 0 01.75-.75h7.5a.75.75 0 010 1.5h-7.5A.75.75 0 018 10zm-5 4.75a.75.75 0 01.75-.75h1.5a.75.75 0 010 1.5h-1.5a.75.75 0 01-.75-.75zm5 0a.75.75 0 01.75-.75h7.5a.75.75 0 010 1.5h-7.5a.75.75 0 01-.75-.75z" /></svg>
          {t("legend", "Legends")}
        </button>
      </div>

      <div
        class="h-full w-full cursor-grab touch-none overflow-hidden bg-gray-50 active:cursor-grabbing dark:bg-gray-950"
        bind:clientWidth={boxW}
        bind:clientHeight={boxH}
        onwheel={onWheel}
        onpointerdown={onPointerDown}
        onpointermove={onPointerMove}
        onpointerup={onPointerUp}
        onpointercancel={onPointerUp}
        role="application"
        aria-label={t("title", "Process Map")}
      >
        <svg width="100%" height="100%" class="select-none">
          <defs>
            {#each RELATION_TYPES as type (type)}
              {@const s = relationStyle(type)}
              {#each ["start", "end"] as const as end (end)}
                {#if s[end] !== "none"}
                  <marker id={`${markerId}-${type}-${end}`} class={s.color} viewBox="0 0 10 10" refX={end === "end" ? (s[end] === "diamond" ? 10 : 9) : s[end] === "circle" ? 5 : 1} refY="5" markerWidth="8" markerHeight="8" markerUnits="userSpaceOnUse" orient="auto-start-reverse">
                    {@html markerShapes[s[end] as Exclude<MarkerKind, "none">]}
                  </marker>
                {/if}
              {/each}
            {/each}
          </defs>
          <g transform={`translate(${tx} ${ty}) scale(${scale})`}>
            {#each layout.lanes as lane (lane.key)}
              <rect
                x={lane.x} y={lane.y} width={lane.w} height={lane.h} rx={lane.kind === "pool" ? 4 : 12}
                class={laneClass(lane.kind)}
                stroke-dasharray={lane.kind === "external" ? "6 4" : undefined}
              />
              {#if lane.kind === "pool"}
                <!-- BPMN pool: the drilled process's name in a vertical band -->
                <line x1={lane.x + 34} y1={lane.y} x2={lane.x + 34} y2={lane.y + lane.h} class="stroke-gray-300 dark:stroke-gray-600" />
                <text
                  x={lane.x + 21} y={lane.y + lane.h / 2} text-anchor="middle"
                  transform={`rotate(-90 ${lane.x + 21} ${lane.y + lane.h / 2})`}
                  class="fill-gray-700 text-[12px] font-semibold dark:fill-gray-200"
                >{clip(drill ? index.get(drill)?.name ?? drill : "", Math.max(8, Math.floor(lane.h / 8)))}</text>
              {:else}
                <text x={lane.x + 14} y={lane.y + 21} class={`text-[14px] font-bold uppercase tracking-wider ${lane.kind === "primary" ? "fill-indigo-700 dark:fill-indigo-300" : "fill-gray-700 dark:fill-gray-200"}`}>{laneLabel(lane.kind)}</text>
              {/if}
            {/each}

            <!-- Sequence flows from the start event / to the end event -->
            {#each layout.eventEdges as e (e.key)}
              {@const a = nodeAt.get(e.source)}
              {@const b = nodeAt.get(e.target)}
              {#if a && b}
                <path d={connectorPath(a, b).d} fill="none" stroke="currentColor" stroke-width="1.5" class={`pointer-events-none text-gray-400 dark:text-gray-500 ${focusVisible ? "opacity-20" : ""}`} marker-end={`url(#${markerId}-PRECEDES-end)`} />
              {/if}
            {/each}

            {#each layout.nodes as n (n.code)}
              {#if n.kind === "start" || n.kind === "end"}
                <g class={focusVisible ? "opacity-30" : ""}>
                  <circle
                    cx={n.x + n.w / 2} cy={n.y + n.h / 2} r={n.w / 2}
                    class={n.kind === "start" ? "fill-white stroke-emerald-600 dark:fill-gray-900" : "fill-white stroke-rose-600 dark:fill-gray-900"}
                    stroke-width={n.kind === "start" ? 2 : 4}
                  ><title>{n.code === START_NODE ? t("start", "Start") : n.code === END_NODE ? t("end", "End") : ""}</title></circle>
                </g>
              {:else}
                {@const p = index.get(n.code)}
                {#if p}
                  <g
                    data-node
                    role="button"
                    tabindex="0"
                    aria-label={`${p.name} (${p.code})`}
                    class={`cursor-pointer outline-none transition-opacity ${nodeDim(n) ? "opacity-25" : ""} ${p.context ? "opacity-60" : ""}`}
                    onclick={() => focusOn(n.code, true)}
                    onkeydown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); focusOn(n.code, true); } }}
                  >
                    <rect
                      x={n.x} y={n.y} width={n.w} height={n.h} rx="10"
                      class={`${nodeClass(p, n)} ${focus === n.code ? "!stroke-indigo-600 dark:!stroke-indigo-300" : ""}`}
                      stroke-width={focus === n.code ? 3 : 1.5}
                      stroke-dasharray={marked(p) ? "5 4" : undefined}
                    />
                    <text x={n.x + 12} y={n.y + 22} class="fill-gray-900 text-[13px] font-semibold dark:fill-white">{clip(p.name, 24)}</text>
                    <text x={n.x + 12} y={n.y + 40} class="fill-gray-500 font-mono text-[10px] dark:fill-gray-400">
                      {p.code}{marked(p) ? ` · ${statusLabel(p)}` : ""}
                    </text>
                    {#if p.is_opportunity}
                      <circle cx={n.x + n.w - 12} cy={n.y + 12} r="4" class="fill-amber-500"><title>{tl("opportunity_hint", "No linked assets or initiatives")}</title></circle>
                    {/if}
                  </g>
                  {#if n.hasChildren && n.kind === "process"}
                    <!-- BPMN collapsed sub-process marker: opens the internal diagram -->
                    <g
                      data-node
                      role="button"
                      tabindex="0"
                      aria-label={t("drill", "Open the internal diagram of {name}", { name: p.name })}
                      class={`cursor-pointer ${nodeDim(n) ? "opacity-25" : ""}`}
                      onclick={() => drillInto(n.code)}
                      onkeydown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); drillInto(n.code); } }}
                    >
                      <title>{t("drill", "Open the internal diagram of {name}", { name: p.name })}</title>
                      <rect x={n.x + n.w / 2 - 8} y={n.y + n.h - 17} width="16" height="16" rx="2" class="fill-white stroke-gray-500 hover:fill-indigo-50 hover:stroke-indigo-600 dark:fill-gray-800 dark:stroke-gray-400" />
                      <path d={`M ${n.x + n.w / 2} ${n.y + n.h - 13.5} v 9 M ${n.x + n.w / 2 - 4.5} ${n.y + n.h - 9} h 9`} class="pointer-events-none stroke-gray-600 dark:stroke-gray-300" stroke-width="1.5" />
                    </g>
                  {/if}
                {/if}
              {/if}
            {/each}

            {#each edges as e (e.key)}
              {@const a = nodeAt.get(e.source)}
              {@const b = nodeAt.get(e.target)}
              {#if a && b}
                {@const s = relationStyle(e.type)}
                {@const geo = connectorPath(a, b)}
                <g class={`${s.color} pointer-events-none transition-opacity ${edgeDim(e.source, e.target) ? "opacity-10" : ""}`}>
                  <path
                    d={geo.d} fill="none" stroke="currentColor" stroke-width={s.width}
                    stroke-dasharray={s.dash || undefined}
                    marker-start={markerRef(e.type, "start")}
                    marker-end={markerRef(e.type, "end")}
                  />
                  {#if e.count > 1}
                    <circle cx={geo.mx} cy={geo.my} r="9" class="fill-white stroke-current dark:fill-gray-900" stroke-width="1.5"><title>{t("merged", "{n} relations", { n: e.count })}</title></circle>
                    <text x={geo.mx} y={geo.my + 3.5} text-anchor="middle" class="fill-current text-[10px] font-semibold">{e.count}</text>
                  {/if}
                </g>
              {/if}
            {/each}
          </g>
        </svg>
      </div>
    </div>

    <!-- Legend panel docked on the right (one table: RELATION_STYLES) -->
    {#if showLegend}
      <aside class="flex w-60 shrink-0 flex-col border-l border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900" aria-label={t("legend", "Legend")}>
        <header class="flex items-center gap-2 border-b border-gray-200 px-3 py-2.5 dark:border-gray-700">
          <h3 class="flex-1 text-sm font-semibold text-gray-900 dark:text-white">{t("legend", "Legend")}</h3>
          <button
            type="button"
            class="rounded-md p-1 text-gray-500 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-white"
            title={tl("close", "Close")}
            aria-label={tl("close", "Close")}
            onclick={toggleLegend}
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" /></svg>
          </button>
        </header>
        <div class="min-h-0 flex-1 space-y-4 overflow-y-auto px-3 py-3">
          <section>
            <p class="mb-2 text-[11px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">{t("relations", "Relations")}</p>
            <ul class="space-y-1.5">
              {#each RELATION_TYPES as type (type)}
                {@const s = relationStyle(type)}
                <li>
                  <label class="flex cursor-pointer items-center gap-2 whitespace-nowrap text-xs text-gray-700 dark:text-gray-300">
                    <input type="checkbox" class="h-3.5 w-3.5 shrink-0 rounded border-gray-300 text-indigo-600 dark:border-gray-600" checked={enabled.has(type)} onchange={() => toggleType(type)} />
                    <svg class={`h-3 w-8 shrink-0 ${s.color}`} viewBox="0 0 40 12" aria-hidden="true">
                      <line x1="2" y1="6" x2="38" y2="6" stroke="currentColor" stroke-width={Math.min(s.width, 3)} stroke-dasharray={s.dash || undefined} marker-start={markerRef(type, "start")} marker-end={markerRef(type, "end")} />
                    </svg>
                    <span>{relLabel(type)}</span>
                  </label>
                </li>
              {/each}
            </ul>
          </section>
          <section>
            <p class="mb-2 text-[11px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">{t("elements", "Elements")}</p>
            <ul class="space-y-1.5 text-xs text-gray-700 dark:text-gray-300">
              <li class="flex items-center gap-2 whitespace-nowrap pl-[22px]">
                <svg class="h-4 w-8 shrink-0" viewBox="0 0 40 16" aria-hidden="true"><circle cx="20" cy="8" r="6" class="fill-white stroke-emerald-600 dark:fill-gray-900" stroke-width="1.5" /></svg>
                {t("legend_start", "Start of the flow")}
              </li>
              <li class="flex items-center gap-2 whitespace-nowrap pl-[22px]">
                <svg class="h-4 w-8 shrink-0" viewBox="0 0 40 16" aria-hidden="true"><circle cx="20" cy="8" r="6" class="fill-white stroke-rose-600 dark:fill-gray-900" stroke-width="3" /></svg>
                {t("legend_end", "End of the flow")}
              </li>
              <li class="flex items-center gap-2 whitespace-nowrap pl-[22px]">
                <svg class="h-4 w-8 shrink-0" viewBox="0 0 40 16" aria-hidden="true"><rect x="13" y="1" width="14" height="14" rx="2" class="fill-white stroke-gray-500 dark:fill-gray-900" /><path d="M20 4.5v7M16.5 8h7" class="stroke-gray-500" stroke-width="1.5" /></svg>
                {t("legend_subprocess", "Open the internal diagram")}
              </li>
              <li class="flex items-center gap-2 whitespace-nowrap pl-[22px]">
                <svg class="h-4 w-8 shrink-0" viewBox="0 0 40 16" aria-hidden="true"><rect x="6" y="2" width="28" height="12" rx="3" class="fill-white stroke-gray-500 dark:fill-gray-900" stroke-dasharray="4 3" /></svg>
                {t("legend_draft", "Draft or in review")}
              </li>
              <li class="flex items-center gap-2 whitespace-nowrap pl-[22px]">
                <svg class="h-4 w-8 shrink-0" viewBox="0 0 40 16" aria-hidden="true"><circle cx="20" cy="8" r="4" class="fill-amber-500" /></svg>
                {t("legend_opportunity", "AI opportunity")}
              </li>
              <li class="flex items-center gap-2 whitespace-nowrap pl-[22px]">
                <svg class="h-4 w-8 shrink-0" viewBox="0 0 40 16" aria-hidden="true"><rect x="2" y="1" width="36" height="14" rx="3" class="fill-transparent stroke-gray-400" stroke-dasharray="4 3" /></svg>
                {t("legend_outside", "Related processes outside")}
              </li>
            </ul>
          </section>
        </div>
      </aside>
    {/if}
    </div>
  {/if}
</div>

{#if panelOpen && focus && landscape && index.has(focus)}
  <ProcessLandscapePanel code={focus} from="map" {landscape} {lists} {langTick} onClose={() => (panelOpen = false)} />
{/if}
