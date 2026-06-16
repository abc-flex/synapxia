// Pure, server-side presentation helpers for the DataTable cell renderer.
// No DOM access — safe to import from any .astro component frontmatter.
import { t } from "@/i18n";
import type { ColumnConfig } from "@/types/datatable";

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
