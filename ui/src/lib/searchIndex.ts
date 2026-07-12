/**
 * Header search palette — index/scoring + client-side "used more" tracking.
 *
 * Pure functions only (no DOM/framework deps) so `SearchPalette.svelte` stays a
 * thin view over this. Everything here reads/writes localStorage only — no
 * backend call, per the feature's "don't save it in the DB" requirement.
 */
import type { NavOption } from "@/types/nav";

const USAGE_KEY = "search_usage_v1";
const RECENT_KEY = "search_recent_v1";
const MAX_RECENT = 10;

// The AI Library module (LIB) is the most-used catalog surface — give it a
// standing edge over other modules whenever relevance is otherwise close.
const BOOSTED_MODULE = "LIB";
const MODULE_BOOST = 25;

export interface SearchEntry {
  moduleCode: string;
  moduleName: string;
  optionCode: string;
  optionName: string;
  path: string;
}

export interface SearchResult extends SearchEntry {
  score: number;
}

type UsageMap = Record<string, number>;

function readJson<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function writeJson(key: string, value: unknown): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* localStorage may be unavailable — non-fatal */
  }
}

function readUsage(): UsageMap {
  return readJson<UsageMap>(USAGE_KEY, {});
}

function readRecent(): string[] {
  return readJson<string[]>(RECENT_KEY, []);
}

/** Call when the user opens a result — grows both its usage count and recency. */
export function recordOptionUse(optionCode: string): void {
  const usage = readUsage();
  usage[optionCode] = (usage[optionCode] || 0) + 1;
  writeJson(USAGE_KEY, usage);

  const recent = readRecent().filter((c) => c !== optionCode);
  recent.unshift(optionCode);
  writeJson(RECENT_KEY, recent.slice(0, MAX_RECENT));
}

export function buildSearchEntries(
  options: NavOption[],
  resolveModuleName: (moduleCode: string) => string,
  resolveOptionName: (optionCode: string) => string,
): SearchEntry[] {
  return options.map((o) => ({
    moduleCode: o.module,
    moduleName: resolveModuleName(o.module),
    optionCode: o.code,
    optionName: resolveOptionName(o.code),
    path: o.path,
  }));
}

/**
 * Closeness of `query` to `target`: exact/substring match scores highest
 * (earlier position + tighter coverage score higher); otherwise falls back to
 * an in-order subsequence match (e.g. "pgl" ~ "Prompt Gallery"). Returns null
 * when the query doesn't match at all.
 */
function fuzzyScore(query: string, target: string): number | null {
  const q = query.toLowerCase().trim();
  const t = target.toLowerCase();
  if (!q) return 0;

  const idx = t.indexOf(q);
  if (idx !== -1) {
    const positionBonus = 1 - idx / Math.max(t.length, 1);
    const coverage = q.length / Math.max(t.length, 1);
    return 60 + 25 * positionBonus + 15 * coverage;
  }

  let ti = 0;
  let gaps = 0;
  for (let qi = 0; qi < q.length; qi++) {
    const found = t.indexOf(q[qi], ti);
    if (found === -1) return null;
    if (found > ti) gaps += found - ti;
    ti = found + 1;
  }
  const spread = gaps / Math.max(t.length, 1);
  return Math.max(10, 40 - spread * 30);
}

function scoreEntry(query: string, entry: SearchEntry): number | null {
  const nameScore = fuzzyScore(query, entry.optionName);
  const codeScore = fuzzyScore(query, entry.optionCode.replace(/_/g, " "));
  const moduleScore = fuzzyScore(query, entry.moduleName);

  const candidates = [
    nameScore,
    codeScore != null ? codeScore * 0.9 : null,
    moduleScore != null ? moduleScore * 0.5 : null,
  ].filter((v): v is number => v != null);

  if (!candidates.length) return null;
  return Math.max(...candidates);
}

/** Rank options against a typed query: text relevance + usage boost + AI Library boost. */
export function rankEntries(query: string, entries: SearchEntry[]): SearchResult[] {
  const trimmed = query.trim();
  if (!trimmed) return [];
  const usage = readUsage();

  const results: SearchResult[] = [];
  for (const entry of entries) {
    const base = scoreEntry(trimmed, entry);
    if (base === null) continue;
    const usageBoost = Math.min(usage[entry.optionCode] || 0, 20) * 1.5;
    const moduleBoost = entry.moduleCode === BOOSTED_MODULE ? MODULE_BOOST : 0;
    results.push({ ...entry, score: base + usageBoost + moduleBoost });
  }

  results.sort((a, b) => b.score - a.score);
  return results;
}

/** No query yet: surface what the user opens most / most recently, AI Library first on ties. */
export function suggestEntries(entries: SearchEntry[], limit = 6): SearchResult[] {
  const usage = readUsage();
  const recent = readRecent();

  const results: SearchResult[] = [];
  for (const entry of entries) {
    const usageCount = usage[entry.optionCode] || 0;
    const recentIndex = recent.indexOf(entry.optionCode);
    if (!usageCount && recentIndex === -1) continue;
    const recencyBoost = recentIndex === -1 ? 0 : (recent.length - recentIndex) * 3;
    const moduleBoost = entry.moduleCode === BOOSTED_MODULE ? MODULE_BOOST / 5 : 0;
    results.push({ ...entry, score: usageCount * 5 + recencyBoost + moduleBoost });
  }

  results.sort((a, b) => b.score - a.score);
  return results.slice(0, limit);
}
