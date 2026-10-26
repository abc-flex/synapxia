/**
 * Process landscape — shared by the Value Chain and the Process Map
 * (specs/010-process-landscape-views, HU-PR05 / HU-PR06).
 *
 * The server owns every figure (shown rule, roll-up counts, opportunity flag,
 * chain order: api/app/workflows/internal/landscape_service.py). This module
 * only holds what depends on the viewer: the view state kept in the address,
 * which parents are expanded, how connectors are redirected to visible
 * ancestors, the focus neighborhood and the map layout. One relation-style
 * table drives both the map's connectors and its legend.
 */
import { apiGet, buildQueryString } from "./api";
import { getListItemsbyList } from "./list_items";
import { labelsByValue, type ListLabels } from "./listLang";
import { translate } from "@/utils/i18nClient";
import type {
  LandscapeProcess, LandscapeProcessDetail, LandscapeRelation, ProcessLandscape,
} from "@/types/api";

// ── API ─────────────────────────────────────────────────────────────────────

export async function getLandscape(unit?: string | null): Promise<ProcessLandscape> {
  return apiGet<ProcessLandscape>(`/api/processes/landscape${buildQueryString({ unit: unit || undefined })}`);
}

export async function getLandscapeDetail(code: string): Promise<LandscapeProcessDetail> {
  return apiGet<LandscapeProcessDetail>(`/api/processes/landscape/${encodeURIComponent(code)}`);
}

export interface LandscapeLists {
  type: ListLabels;
  status: ListLabels;
  relation: ListLabels;
  link: ListLabels;
}

/** The four list values the views label (every language; see listLang.ts). */
export async function loadLandscapeLists(): Promise<LandscapeLists> {
  const codes: [keyof LandscapeLists, string][] = [
    ["type", "PROCESS_TYPE"], ["status", "PROCESS_STATUS"],
    ["relation", "PROCESS_RELATION_TYPE"], ["link", "RELATION_TYPE"],
  ];
  const lists: LandscapeLists = { type: {}, status: {}, relation: {}, link: {} };
  const results = await Promise.allSettled(codes.map(([, code]) => getListItemsbyList(code, 0, 500)));
  results.forEach((r, i) => {
    if (r.status === "fulfilled") lists[codes[i][0]] = labelsByValue(r.value);
  });
  return lists;
}

/** Status 403 from an apiGet error ("GET … failed (403): …"). */
export const isForbidden = (err: unknown): boolean =>
  err instanceof Error && /failed \(403\)/.test(err.message);

// ── Text ────────────────────────────────────────────────────────────────────

/** `<ns>.<key>` in the current language, or `fallback`; read it under a
 *  `langTick` so Svelte re-renders on a language switch. */
export function landscapeText(
  ns: "value_chain" | "process_map" | "process_landscape",
  key: string,
  fallback: string,
  vars: Record<string, string | number> = {},
): string {
  const full = `${ns}.${key}`;
  const raw = translate(full);
  let text = raw && raw !== full ? raw : fallback;
  for (const [k, v] of Object.entries(vars)) text = text.replaceAll(`{${k}}`, String(v));
  return text;
}

// ── View state in the address (FR-017) ──────────────────────────────────────

export interface ViewState {
  focus: string | null;
  unit: string | null;
  opportunities: boolean;
  /** Process Map: the process whose internal diagram is shown (null = overview). */
  drill: string | null;
  /** Enabled relation types (map); null = all. */
  types: string[] | null;
}

export function readViewState(search: string = typeof location !== "undefined" ? location.search : ""): ViewState {
  const p = new URLSearchParams(search);
  const types = p.get("types");
  return {
    focus: p.get("focus") || null,
    unit: p.get("unit") || null,
    opportunities: p.get("opportunities") === "1",
    drill: p.get("in") || null,
    types: types === null ? null : types.split(",").filter(Boolean),
  };
}

export function writeViewState(state: ViewState): void {
  const p = new URLSearchParams(location.search);
  const set = (k: string, v: string | null) => (v ? p.set(k, v) : p.delete(k));
  set("focus", state.focus);
  set("unit", state.unit);
  set("opportunities", state.opportunities ? "1" : null);
  set("in", state.drill);
  set("types", state.types === null ? null : state.types.join(","));
  const qs = p.toString();
  history.replaceState(history.state, "", `${location.pathname}${qs ? `?${qs}` : ""}`);
}

// ── Tree helpers ────────────────────────────────────────────────────────────

export function byCode(landscape: ProcessLandscape): Map<string, LandscapeProcess> {
  return new Map(landscape.processes.map((p) => [p.code, p]));
}

/** Shown ancestors of `code`, nearest first. */
export function ancestors(code: string, index: Map<string, LandscapeProcess>): string[] {
  const out: string[] = [];
  let parent = index.get(code)?.display_parent ?? null;
  while (parent && !out.includes(parent)) {
    out.push(parent);
    parent = index.get(parent)?.display_parent ?? null;
  }
  return out;
}

export const topLevelOf = (code: string, index: Map<string, LandscapeProcess>): string =>
  ancestors(code, index).at(-1) ?? code;

/** The first process on the way up whose ancestors are all expanded. */
export function visibleAncestor(code: string, expanded: Set<string>, index: Map<string, LandscapeProcess>): string {
  const chain = [code, ...ancestors(code, index)];   // self → root
  let visible = chain[chain.length - 1];
  for (let i = chain.length - 2; i >= 0; i--) {
    if (!expanded.has(chain[i + 1])) break;
    visible = chain[i];
  }
  return visible;
}

/** The process, its parent, its children and every directly related process. */
export function neighborhood(code: string, landscape: ProcessLandscape, index: Map<string, LandscapeProcess>): Set<string> {
  const set = new Set<string>([code]);
  const p = index.get(code);
  if (p?.display_parent) set.add(p.display_parent);
  p?.child_order.forEach((c) => set.add(c));
  for (const r of landscape.relations) {
    if (r.source === code) set.add(r.target);
    if (r.target === code) set.add(r.source);
  }
  return set;
}

// ── Relation styles (FR-011): one table for connectors and legend ───────────

export type MarkerKind = "arrow" | "open" | "diamond" | "circle" | "none";

export interface RelationStyle {
  /** SVG stroke-dasharray ("" = solid). */
  dash: string;
  width: number;
  start: MarkerKind;
  end: MarkerKind;
  /** Tailwind stroke/text color classes (light + dark). */
  color: string;
}

/** BPMN counterparts: sequence flow, event start, call activity, data
 *  association, message flow (undirected), association (×2). */
export const RELATION_STYLES: Record<string, RelationStyle> = {
  PRECEDES:       { dash: "",     width: 2,   start: "none",   end: "arrow",   color: "text-indigo-600 dark:text-indigo-400" },
  TRIGGERS:       { dash: "",     width: 1.5, start: "circle", end: "arrow",   color: "text-rose-600 dark:text-rose-400" },
  CALLS:          { dash: "",     width: 3.5, start: "none",   end: "arrow",   color: "text-sky-700 dark:text-sky-400" },
  FEEDS_INTO:     { dash: "2 4",  width: 1.5, start: "none",   end: "open",    color: "text-emerald-600 dark:text-emerald-400" },
  INTERACTS_WITH: { dash: "7 5",  width: 1.5, start: "none",   end: "none",    color: "text-amber-600 dark:text-amber-400" },
  SUPPORTS:       { dash: "1 4",  width: 1.75, start: "none",  end: "open",    color: "text-gray-600 dark:text-gray-300" },
  GOVERNS:        { dash: "1 4",  width: 1.75, start: "none",  end: "diamond", color: "text-purple-600 dark:text-purple-400" },
};

export const RELATION_TYPES = Object.keys(RELATION_STYLES);

export const relationStyle = (type: string): RelationStyle =>
  RELATION_STYLES[type] ?? { dash: "", width: 1.5, start: "none", end: "arrow", color: "text-gray-500" };

// ── Connectors (FR-012) ─────────────────────────────────────────────────────

export interface MapEdge {
  key: string;
  source: string;
  target: string;
  type: string;
  directed: boolean;
  count: number;
}

/** Redirect both ends to their visible ancestor, drop self-loops, and merge
 *  per (source, target, type) — per unordered pair for undirected types. */
export function mergeEdges(
  relations: LandscapeRelation[],
  expanded: Set<string>,
  enabled: Set<string>,
  index: Map<string, LandscapeProcess>,
): MapEdge[] {
  const merged = new Map<string, MapEdge>();
  for (const r of relations) {
    if (!enabled.has(r.type)) continue;
    let source = visibleAncestor(r.source, expanded, index);
    let target = visibleAncestor(r.target, expanded, index);
    if (source === target) continue;
    if (!r.directed && target < source) [source, target] = [target, source];
    const key = `${source}|${target}|${r.type}`;
    const edge = merged.get(key);
    if (edge) edge.count += 1;
    else merged.set(key, { key, source, target, type: r.type, directed: r.directed, count: 1 });
  }
  return [...merged.values()];
}

// ── Map layouts (research R1, amended 2026-10-25) ───────────────────────────
// The map shows ONE level at a time: the overview (top-level processes in two
// lanes) or the internal diagram of one process ("drill"), drawn BPMN-style:
// a pool with the sub-processes as tasks ordered by their sequence flows
// (PRECEDES), start and end events, and the processes outside it that they
// relate to in a lane underneath. Deterministic: same data, same picture.

export const NODE_W = 184;
export const NODE_H = 58;
export const EVENT_D = 34;
const GAP_X = 56;
const ROW_GAP = 26;
const PAD = 24;
const LANE_LABEL = 30;
const LANE_GAP = 40;
const POOL_LABEL = 34;

export type MapNodeKind = "process" | "external" | "start" | "end";

export interface MapNode {
  code: string;
  kind: MapNodeKind;
  x: number;
  y: number;
  w: number;
  h: number;
  hasChildren: boolean;
}

export interface MapLane {
  key: string;
  kind: "primary" | "support" | "pool" | "external";
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface MapLayout {
  nodes: MapNode[];
  lanes: MapLane[];
  /** Sequence flows from the start event / to the end event (drill only). */
  eventEdges: { key: string; source: string; target: string }[];
  width: number;
  height: number;
}

export const START_NODE = "__start__";
export const END_NODE = "__end__";

const box = (code: string, kind: MapNodeKind, x: number, y: number, index: Map<string, LandscapeProcess>): MapNode => ({
  code, kind, x, y, w: NODE_W, h: NODE_H,
  hasChildren: (index.get(code)?.child_order.length ?? 0) > 0,
});

/** The parents that must count as "expanded" to show `drill`'s children:
 *  the drilled process and every ancestor (feeds visibleAncestor/mergeEdges). */
export function drillPath(drill: string | null, index: Map<string, LandscapeProcess>): Set<string> {
  return drill ? new Set([drill, ...ancestors(drill, index)]) : new Set();
}

/** Top level: Primary lane on top in chain order, Support lane below. */
export function layoutOverview(landscape: ProcessLandscape, index: Map<string, LandscapeProcess>): MapLayout {
  const nodes: MapNode[] = [];
  const lanes: MapLane[] = [];
  let y = 0;
  let width = 0;
  const rows: ["primary" | "support", string[]][] = [
    ["primary", landscape.primary_order],
    ["support", landscape.support_order],
  ];
  for (const [kind, codes] of rows) {
    let x = PAD;
    for (const code of codes) {
      nodes.push(box(code, "process", x, y + LANE_LABEL, index));
      x += NODE_W + GAP_X;
    }
    const laneW = Math.max(x - GAP_X + PAD, NODE_W + 2 * PAD);
    lanes.push({ key: kind, kind, x: 0, y, w: laneW, h: LANE_LABEL + NODE_H + PAD });
    width = Math.max(width, laneW);
    y += LANE_LABEL + NODE_H + PAD + LANE_GAP;
  }
  lanes.forEach((l) => (l.w = width));
  return { nodes, lanes, eventEdges: [], width, height: Math.max(0, y - LANE_GAP) };
}

/** `codes` in sequence-flow order: each after every code that precedes it,
 *  the earliest in `codes` first among those ready, a cycle entered at its
 *  earliest code. Same rule as the server's `chain_order`, applied here to the
 *  edges actually drawn (redirected onto visible boxes). */
function flowOrder(codes: string[], precedes: MapEdge[]): string[] {
  const rank = new Map(codes.map((c, i) => [c, i]));
  const links = precedes.filter((e) => rank.has(e.source) && rank.has(e.target) && e.source !== e.target);
  const indegree = new Map(codes.map((c) => [c, 0]));
  for (const e of links) indegree.set(e.target, indegree.get(e.target)! + 1);
  const remaining = new Set(codes);
  const ordered: string[] = [];
  const earliest = (pool: string[]) => pool.reduce((a, b) => (rank.get(a)! <= rank.get(b)! ? a : b));
  while (remaining.size) {
    const ready = [...remaining].filter((c) => indegree.get(c) === 0);
    const node = earliest(ready.length ? ready : [...remaining]);
    remaining.delete(node);
    ordered.push(node);
    for (const e of links) if (e.source === node && remaining.has(e.target)) indegree.set(e.target, indegree.get(e.target)! - 1);
  }
  return ordered;
}

/** Inside `parent`: its sub-processes laid out by sequence-flow layers
 *  (longest PRECEDES path, following child_order, so a cycle never loops),
 *  the ones outside any flow on a row of their own, start/end events around
 *  the flow, and the external processes the edges reach in a lane below. */
export function layoutDrill(
  parent: string,
  edges: MapEdge[],
  index: Map<string, LandscapeProcess>,
): MapLayout {
  const children = index.get(parent)?.child_order ?? [];
  const precedes = edges.filter((e) => e.type === "PRECEDES");
  const internal = flowOrder(children, precedes);
  const pos = new Map(internal.map((c, i) => [c, i]));
  const forward = precedes.filter((e) => pos.has(e.source) && pos.has(e.target)
    && pos.get(e.source)! < pos.get(e.target)!);
  const inFlow = new Set(forward.flatMap((e) => [e.source, e.target]));
  const layer = new Map<string, number>();
  for (const code of internal) {
    if (!inFlow.has(code)) continue;
    const preds = forward.filter((e) => e.target === code).map((e) => (layer.get(e.source) ?? 0) + 1);
    layer.set(code, Math.max(0, ...preds));
  }
  const columns: string[][] = [];
  for (const code of internal) {
    if (!layer.has(code)) continue;
    (columns[layer.get(code)!] ??= []).push(code);
  }
  const isolated = internal.filter((c) => !inFlow.has(c));
  const hasFlow = columns.length > 0;

  const nodes: MapNode[] = [];
  const inner = POOL_LABEL + PAD;
  const left = inner + (hasFlow ? EVENT_D + GAP_X : 0);
  const step = NODE_W + GAP_X;
  const rowH = NODE_H + ROW_GAP;
  const flowRows = Math.max(0, ...columns.map((c) => c.length));
  columns.forEach((col, i) => col.forEach((code, row) =>
    nodes.push(box(code, "process", left + i * step, PAD + row * rowH, index))));

  const perRow = Math.max(columns.length, 4);
  const gap = hasFlow && isolated.length ? ROW_GAP : 0;
  const isoTop = PAD + flowRows * rowH + gap;
  isolated.forEach((code, i) => nodes.push(box(code, "process",
    inner + (i % perRow) * step, isoTop + Math.floor(i / perRow) * rowH, index)));
  const isoRows = Math.ceil(isolated.length / perRow);

  const eventEdges: MapLayout["eventEdges"] = [];
  let right = Math.max(inner + NODE_W, ...nodes.map((n) => n.x + n.w));
  if (hasFlow) {
    const flowMid = PAD + ((flowRows - 1) * rowH + NODE_H) / 2;
    const endX = left + columns.length * step;
    nodes.push({ code: START_NODE, kind: "start", x: inner, y: flowMid - EVENT_D / 2, w: EVENT_D, h: EVENT_D, hasChildren: false });
    nodes.push({ code: END_NODE, kind: "end", x: endX, y: flowMid - EVENT_D / 2, w: EVENT_D, h: EVENT_D, hasChildren: false });
    for (const code of internal) {
      if (!inFlow.has(code)) continue;
      if (!forward.some((e) => e.target === code)) eventEdges.push({ key: `s|${code}`, source: START_NODE, target: code });
      if (!forward.some((e) => e.source === code)) eventEdges.push({ key: `e|${code}`, source: code, target: END_NODE });
    }
    right = Math.max(right, endX + EVENT_D);
  }
  const width = right + PAD;
  const poolH = Math.max(NODE_H + 2 * PAD, PAD + (flowRows + isoRows) * rowH - ROW_GAP + gap + PAD);
  const lanes: MapLane[] = [{ key: "pool", kind: "pool", x: 0, y: 0, w: width, h: poolH }];

  // Processes outside `parent` reached by an edge of one of its sub-processes.
  const externals = [...new Set(edges.flatMap((e) =>
    pos.has(e.source) && !pos.has(e.target) ? [e.target]
      : pos.has(e.target) && !pos.has(e.source) ? [e.source] : []))].sort();
  let height = poolH;
  if (externals.length) {
    const top = poolH + LANE_GAP;
    const perExt = Math.max(1, Math.floor((width - 2 * PAD + GAP_X) / step));
    externals.forEach((code, i) => nodes.push(box(code, "external",
      PAD + (i % perExt) * step, top + LANE_LABEL + Math.floor(i / perExt) * rowH, index)));
    const laneH = LANE_LABEL + Math.ceil(externals.length / perExt) * rowH - ROW_GAP + PAD;
    lanes.push({ key: "external", kind: "external", x: 0, y: top, w: width, h: laneH });
    height = top + laneH;
  }
  return { nodes, lanes, eventEdges, width, height };
}

/** A cubic path between two boxes: from the sides when they sit apart
 *  horizontally, from bottom/top otherwise. Returns the path and its midpoint. */
export function connectorPath(a: MapNode, b: MapNode): { d: string; mx: number; my: number } {
  const ac = { x: a.x + a.w / 2, y: a.y + a.h / 2 };
  const bc = { x: b.x + b.w / 2, y: b.y + b.h / 2 };
  const dx = bc.x - ac.x;
  const dy = bc.y - ac.y;
  let p1: { x: number; y: number }, p2: { x: number; y: number }, c1, c2;
  if (Math.abs(dx) >= (a.w + b.w) / 2) {
    const dir = Math.sign(dx);
    p1 = { x: dir > 0 ? a.x + a.w : a.x, y: ac.y };
    p2 = { x: dir > 0 ? b.x : b.x + b.w, y: bc.y };
    const k = Math.max(30, Math.abs(p2.x - p1.x) / 2);
    c1 = { x: p1.x + dir * k, y: p1.y };
    c2 = { x: p2.x - dir * k, y: p2.y };
  } else {
    const dir = Math.sign(dy) || 1;
    p1 = { x: ac.x, y: dir > 0 ? a.y + a.h : a.y };
    p2 = { x: bc.x, y: dir > 0 ? b.y : b.y + b.h };
    const k = Math.max(30, Math.abs(p2.y - p1.y) / 2);
    c1 = { x: p1.x, y: p1.y + dir * k };
    c2 = { x: p2.x, y: p2.y - dir * k };
  }
  const d = `M ${p1.x} ${p1.y} C ${c1.x} ${c1.y}, ${c2.x} ${c2.y}, ${p2.x} ${p2.y}`;
  return { d, mx: (p1.x + 3 * c1.x + 3 * c2.x + p2.x) / 8, my: (p1.y + 3 * c1.y + 3 * c2.y + p2.y) / 8 };
}
