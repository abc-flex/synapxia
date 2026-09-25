/**
 * The list-backed initiative fields (type, expected impact, priority, status)
 * as `{value, label}` options in the current language, with an English
 * fallback — shared by the diagnose / modify / outcome pages
 * (specs/005-explore-initiatives). One request per list, in parallel.
 */
import { getListItemsbyList } from "./list_items";

export type Option = { value: string; label: string };
export interface InitiativeLists {
  type: Option[];
  impact: Option[];
  priority: Option[];
  status: Option[];
}

export const currentLang = (): "en" | "es" =>
  (typeof localStorage !== "undefined" && localStorage.getItem("lang")) === "es" ? "es" : "en";

async function options(code: string, lang: string): Promise<Option[]> {
  try {
    const items = await getListItemsbyList(code, 0, 200);
    const scoped = items.filter((i) => i.lang === lang);
    return (scoped.length ? scoped : items.filter((i) => i.lang === "en"))
      .slice()
      .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0))
      .map((i) => ({ value: i.value, label: i.label || i.value }));
  } catch {
    return [];
  }
}

export async function loadInitiativeLists(lang = currentLang()): Promise<InitiativeLists> {
  const [type, impact, priority, status] = await Promise.all([
    options("INITIATIVE_TYPE", lang),
    options("EXPECTED_IMPACT", lang),
    options("PRIORITY_LEVEL", lang),
    options("INITIATIVE_STATUS", lang),
  ]);
  return { type, impact, priority, status };
}

export const labelOf = (opts: Option[], value?: string | null): string =>
  value ? opts.find((o) => o.value === value)?.label ?? value : "";
