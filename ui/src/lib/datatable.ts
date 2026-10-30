// Pure, server-side presentation helpers for the DataTable cell renderer.
// No DOM access — safe to import from any .astro component frontmatter.
import { t } from "@/i18n";
import type { ColumnConfig, FilterConfig, FilterOption } from "@/types/datatable";

/** Raw per-slot inputs (from DataTable props) for building the 4 filter slots. */
export interface FilterSlotInput {
  key?: string | null;
  options?: FilterOption[];
  defaultValue?: string;
  allLabel?: string | null;
  /** Display-column key whose <th> hosts this filter (omits it from the toolbar). */
  headerColumn?: string | null;
  /** Render the toolbar control as a toggle switch instead of a <select>. */
  asToggle?: boolean;
}

/**
 * Build the (up to 4) FilterConfig slots from raw inputs, assigning the canonical
 * ids advancedTable.ts binds to (`${tableId}-filter`, `-filter2`, `-filter3`,
 * `-filter4`). Shared by DataTableFilters (toolbar) and DataTableHead (column
 * funnels) so both render from one source of truth.
 */
export function buildFilterConfigs(
  tableId: string,
  slots: FilterSlotInput[],
): FilterConfig[] {
  return slots.map((s, i) => ({
    id: i === 0 ? `${tableId}-filter` : `${tableId}-filter${i + 1}`,
    key: s.key ?? null,
    options: s.options ?? [],
    defaultValue: s.defaultValue ?? "",
    allLabel: s.allLabel ?? null,
    headerColumn: s.headerColumn ?? null,
    asToggle: s.asToggle ?? false,
  }));
}

// Semantic colors for status pills (columns flagged `as: "status"`). Tone is
// inferred from the status text so it works across entities/locales. Literal
// class strings so Tailwind's JIT keeps them.
export const TONE: Record<string, string> = {
  green: "bg-green-50 text-green-700 dark:bg-green-500/15 dark:text-green-300",
  red: "bg-red-50 text-red-700 dark:bg-red-500/15 dark:text-red-300",
  amber: "bg-amber-50 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300",
  indigo: "bg-indigo-50 text-indigo-700 dark:bg-indigo-500/15 dark:text-indigo-300",
};

export const statusTone = (val: unknown): string => {
  const v = String(val ?? "").toLowerCase();
  if (/(in[\s-]?use|en uso|activ|active|publi|aprob|approv|complet|done|live)/.test(v)) return TONE.green;
  if (/(deprecat|obsolet|retir|inactiv|archiv|reject|rechaz|error|fail|cancel)/.test(v)) return TONE.red;
  if (/(review|revisi|pending|pendiente|draft|borrador|progress|proceso|hold|espera)/.test(v)) return TONE.amber;
  return TONE.indigo;
};

// Locale-aware short date (e.g. "Jun 7, 2026" / "7 jun 2026"). Guards invalid → "".
export const formatDate = (raw: any, locale: string): string => {
  if (raw === null || raw === undefined || raw === "") return "";
  const d = new Date(raw);
  if (isNaN(d.getTime())) return "";
  return new Intl.DateTimeFormat(locale === "es" ? "es-ES" : "en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(d);
};

// Relative span without prefix: "2 d ago" / "hace 2 d". Empty on invalid input.
export const formatRelative = (raw: any, locale: string): string => {
  if (raw === null || raw === undefined || raw === "") return "";
  const d = new Date(raw);
  if (isNaN(d.getTime())) return "";
  const sec = Math.max(0, Math.floor((Date.now() - d.getTime()) / 1000));
  if (sec < 60) return t(locale, "data_table.rel_now");
  const min = Math.floor(sec / 60);
  let n: number;
  let unit: string;
  if (min < 60) { n = min; unit = t(locale, "data_table.unit_min"); }
  else if (min < 1440) { n = Math.floor(min / 60); unit = t(locale, "data_table.unit_hour"); }
  else if (min < 10080) { n = Math.floor(min / 1440); unit = t(locale, "data_table.unit_day"); }
  else if (min < 43200) { n = Math.floor(min / 10080); unit = t(locale, "data_table.unit_week"); }
  else if (min < 525600) { n = Math.floor(min / 43200); unit = t(locale, "data_table.unit_month"); }
  else { n = Math.floor(min / 525600); unit = t(locale, "data_table.unit_year"); }
  const ago = t(locale, "data_table.rel_ago");
  // Word order differs per locale: "2 d ago" vs "hace 2 d".
  return locale === "es" ? `${ago} ${n} ${unit}` : `${n} ${unit} ${ago}`;
};

// Muted subtitle line under a title cell. Dispatches on subtitleFormat.
export const renderSubtitle = (col: ColumnConfig, row: Record<string, any>, locale: string): string => {
  if (!col.subtitleKey) return "";
  const raw = row[col.subtitleKey];
  if (raw === null || raw === undefined || raw === "") return "";
  const fmt = col.subtitleFormat ?? "text";
  if (fmt === "relative") {
    const prefix = t(locale, col.subtitleKey === "created_at" ? "data_table.created" : "data_table.updated");
    const rel = formatRelative(raw, locale);
    return rel ? `${prefix} ${rel}` : "";
  }
  if (fmt === "date") return formatDate(raw, locale);
  return String(raw);
};

/** Per-row position in a tree-mode DataTable (aligned 1:1 with the ordered rows). */
export interface TreeRowMeta {
  id: string;
  /** Effective parent id: null for roots and for rows whose parent isn't in the data. */
  parent: string | null;
  depth: number;
  hasChildren: boolean;
}

/**
 * Order rows depth-first (each parent followed by its descendants), keeping the
 * incoming order among siblings, and describe each row's place in the tree.
 * A row whose parent is missing becomes a root; a parent cycle is broken by
 * placing its unvisited rows as roots, so every row appears exactly once.
 */
export function buildTreeRows<T extends Record<string, any>>(
  rows: T[],
  parentKey: string,
): { rows: T[]; meta: TreeRowMeta[] } {
  const idOf = (r: T) => String(r.id);
  const ids = new Set(rows.map(idOf));
  const parentOf = (r: T): string | null => {
    const p = r[parentKey];
    return p != null && p !== "" && ids.has(String(p)) && String(p) !== idOf(r) ? String(p) : null;
  };
  const children = new Map<string | null, T[]>();
  for (const r of rows) {
    const p = parentOf(r);
    if (!children.has(p)) children.set(p, []);
    children.get(p)!.push(r);
  }

  const out: T[] = [];
  const meta: TreeRowMeta[] = [];
  const seen = new Set<string>();
  const visit = (r: T, parent: string | null, depth: number) => {
    const id = idOf(r);
    if (seen.has(id)) return;
    seen.add(id);
    const kids = (children.get(id) ?? []).filter((k) => !seen.has(idOf(k)));
    out.push(r);
    meta.push({ id, parent, depth, hasChildren: kids.length > 0 });
    for (const k of kids) visit(k, id, depth + 1);
  };
  for (const r of children.get(null) ?? []) visit(r, null, 0);
  for (const r of rows) visit(r, null, 0); // rows only reachable through a cycle
  return { rows: out, meta };
}
