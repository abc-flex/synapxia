/**
 * Usage Metrics services (specs/008-usage-metrics, HU-AN07).
 * Contract: specs/008-usage-metrics/contracts/usage-api.md.
 */
import { apiGet, buildQueryString } from "./api";
import type { UsageErrors, UsageMetrics } from "@/types/api";
import { translate } from "@/utils/i18nClient";

export const NO_TEAM = "__none__"; // also "No project"

export type UsageGroupKind = "unit" | "team" | "project";

export interface UsageQuery {
  dateFrom: string;
  dateTo: string;
  unit?: string | null;
  team?: string | null;
  project?: string | null;
}

const params = (q: UsageQuery) => ({
  date_from: q.dateFrom,
  date_to: q.dateTo,
  unit: q.unit || undefined,
  team: q.team || undefined,
  project: q.project || undefined,
});

export async function getUsageMetrics(q: UsageQuery): Promise<UsageMetrics> {
  return apiGet<UsageMetrics>(`/api/usage/metrics${buildQueryString(params(q))}`);
}

export async function getDashboardErrors(id: number, q: UsageQuery, limit = 10): Promise<UsageErrors> {
  return apiGet<UsageErrors>(
    `/api/usage/dashboards/${id}/errors${buildQueryString({ ...params(q), limit })}`);
}

export type UsagePreset = "7d" | "30d" | "90d" | "12m";
export const PRESET_DAYS: Record<UsagePreset, number> = { "7d": 7, "30d": 30, "90d": 90, "12m": 365 };
export const MAX_RANGE_DAYS = 731;

/** Local YYYY-MM-DD for a Date (browser zone). */
export function isoDate(d: Date): string {
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

/** Inclusive range of `PRESET_DAYS[preset]` days ending `today`. */
export function presetRange(preset: UsagePreset, today: Date = new Date()): { dateFrom: string; dateTo: string } {
  const start = new Date(today);
  start.setDate(start.getDate() - (PRESET_DAYS[preset] - 1));
  return { dateFrom: isoDate(start), dateTo: isoDate(today) };
}

/** Days between two YYYY-MM-DD dates (to − from), or NaN. */
export function daysBetween(from: string, to: string): number {
  const a = Date.parse(`${from}T00:00:00Z`);
  const b = Date.parse(`${to}T00:00:00Z`);
  return Math.round((b - a) / 86_400_000);
}

// ── Display helpers (shared by the Usage Metrics islands) ────────────────────

/** `usage_metrics.<key>` in the current language, or `fallback`. Read it under
 *  a `langTick` so Svelte re-renders on a language switch. */
export function usageText(key: string, fallback: string, vars: Record<string, string | number> = {}): string {
  const full = `usage_metrics.${key}`;
  const raw = translate(full);
  let text = raw && raw !== full ? raw : fallback;
  for (const [k, v] of Object.entries(vars)) text = text.replaceAll(`{${k}}`, String(v));
  return text;
}

const locale = () =>
  (typeof localStorage !== "undefined" && localStorage.getItem("lang")) === "es" ? "es-CO" : "en-US";

export const fmtInt = (n: number | null | undefined): string =>
  n == null ? "—" : new Intl.NumberFormat(locale()).format(n);

export const fmtPct = (r: number | null | undefined, digits = 1): string =>
  r == null ? "—" : new Intl.NumberFormat(locale(), { style: "percent", maximumFractionDigits: digits }).format(r);

export function fmtMs(ms: number | null | undefined): string {
  if (ms == null) return "—";
  if (Math.abs(ms) < 1000) return `${Math.round(ms)} ms`;
  return `${new Intl.NumberFormat(locale(), { maximumFractionDigits: 1 }).format(ms / 1000)} s`;
}

export function fmtDate(iso: string | null | undefined, withTime = false): string {
  if (!iso) return "—";
  const d = iso.length === 10 ? new Date(`${iso}T00:00:00`) : new Date(iso);
  return new Intl.DateTimeFormat(locale(), withTime
    ? { dateStyle: "medium", timeStyle: "short" }
    : { dateStyle: "medium" }).format(d);
}

/** "1,2 s" → {num: "1,2", unit: "s"}; "97,1 %" → {num: "97,1", unit: "%"}; "—" → {num: "—"}.
 *  Lets a tile render its unit smaller than the number. */
export function splitUnit(text: string): { num: string; unit: string } {
  const m = /^([−+-]?[\d.,\s  ]*\d)\s*(\D*)$/.exec(text);
  return m ? { num: m[1].trim(), unit: m[2].trim() } : { num: text, unit: "" };
}

export type ChangeKind = "ratio" | "points" | "ms";

/** Signed change text + direction for a tile. `null` → neutral mark. */
export function fmtChange(v: number | null | undefined, kind: ChangeKind): { text: string; dir: "up" | "down" | "flat" } {
  if (v == null) return { text: "—", dir: "flat" };
  const dir = v > 0 ? "up" : v < 0 ? "down" : "flat";
  const sign = v > 0 ? "+" : v < 0 ? "−" : "±";
  const abs = Math.abs(v);
  const text = kind === "ratio" ? fmtPct(abs, 0)
    : kind === "points" ? `${new Intl.NumberFormat(locale(), { maximumFractionDigits: 1 }).format(abs * 100)} pp`
    : fmtMs(abs);
  return { text: `${sign}${text}`, dir };
}
