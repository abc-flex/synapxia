/**
 * The list-backed initiative fields (type, expected impact, priority, status)
 * as `{value, label, labels}` options — `label` in the requested language
 * (English fallback), `labels` in every language so a page can follow the
 * header language switcher without refetching (lib/listLang.ts). Shared by
 * the diagnose / modify / outcome pages (specs/005-explore-initiatives).
 * One request per list, in parallel.
 */
import { getListItemsbyList } from "./list_items";
import { currentLang, labelIn, toListOptions, type ListOption } from "./listLang";

export type Option = ListOption;
export interface InitiativeLists {
  type: Option[];
  impact: Option[];
  priority: Option[];
  status: Option[];
}

export { currentLang };

async function options(code: string, lang: string): Promise<Option[]> {
  try {
    return toListOptions(await getListItemsbyList(code, 0, 200), lang);
  } catch {
    return [];
  }
}

export async function loadInitiativeLists(lang: string = currentLang()): Promise<InitiativeLists> {
  const [type, impact, priority, status] = await Promise.all([
    options("INITIATIVE_TYPE", lang),
    options("EXPECTED_IMPACT", lang),
    options("PRIORITY_LEVEL", lang),
    options("INITIATIVE_STATUS", lang),
  ]);
  return { type, impact, priority, status };
}

/** An option's label in `lang` (default: the current language). */
export const optionLabel = (o: Option, lang: string = currentLang()): string =>
  labelIn(o.labels, lang, o.label);

/** A stored value's label in `lang` (default: the current language). */
export const labelOf = (opts: Option[], value?: string | null, lang: string = currentLang()): string => {
  if (!value) return "";
  const hit = opts.find((o) => o.value === value);
  return hit ? optionLabel(hit, lang) : value;
};
