/**
 * listLang — list values (list_items) in the viewer's language, kept in sync
 * with the header language switcher.
 *
 * `/api/list_items/list/{code}` returns every language, so switching language
 * never needs a new request: each rendered value carries all of its labels in
 * a `data-list-labels` attribute (`{"en": "...", "es": "..."}`), and
 * `relabelLists()` — run by `loadClientTranslations()` on load and on every
 * language switch — rewrites their text. The value (the list item's code) is
 * the same in every language, so a select keeps its selection.
 *
 * Vanilla code: build options with `fillListSelect` / `listOption`, or put
 * `listLabelsAttr(...)` on any element. Svelte islands render their own text
 * (an external textContent write would fight Svelte), so they read
 * `toListOptions` / `listLabel` / `labelIn` inside a block that depends on
 * their `langTick`.
 */

export type Lang = "en" | "es";

/** value → lang → label */
export type ListLabels = Record<string, Record<string, string>>;

export interface ListItemLike {
  value: string;
  label?: string | null;
  lang?: string | null;
  sort_order?: number | null;
}

export interface ListOption {
  value: string;
  label: string;
  /** Every language's label for this value (for relabeling). */
  labels: Record<string, string>;
}

export const LIST_LABELS_ATTR = "data-list-labels";

export const currentLang = (): Lang =>
  (typeof localStorage !== "undefined" && localStorage.getItem("lang")) === "es" ? "es" : "en";

/** Legacy rows may store the bare code (`IN_USE`) where the list value is `6-IN_USE`. */
export const bareCode = (v: unknown): string => String(v ?? "").replace(/^\d+-/, "");

/** Group a list's items as value → lang → label. */
export function labelsByValue(items: ListItemLike[]): ListLabels {
  const map: ListLabels = {};
  for (const it of items) {
    if (!it.value) continue;
    (map[it.value] ??= {})[it.lang || "en"] = it.label || it.value;
  }
  return map;
}

/** The label for one language, falling back to English, then any language. */
export function labelIn(byLang: Record<string, string> | undefined, lang: string = currentLang(), fallback = ""): string {
  if (!byLang) return fallback;
  return byLang[lang] ?? byLang.en ?? Object.values(byLang)[0] ?? fallback;
}

/** Resolve a stored value (tolerating the `N-` prefix) to its labels. */
export function labelsFor(labels: ListLabels, raw: unknown): Record<string, string> | undefined {
  if (raw == null || raw === "") return undefined;
  const v = String(raw);
  if (labels[v]) return labels[v];
  const bare = bareCode(v);
  const key = Object.keys(labels).find((k) => k === bare || bareCode(k) === bare);
  return key ? labels[key] : undefined;
}

/** Display label of a stored value in a language (the raw value when unknown). */
export function listLabel(labels: ListLabels, raw: unknown, lang: string = currentLang()): string {
  return labelIn(labelsFor(labels, raw), lang, raw == null ? "" : String(raw));
}

/**
 * Items → one option per value, carrying every language's label, labeled in
 * `lang` (English fallback). Every value is kept even when only some
 * languages translate it, so the option set never changes with the language.
 * Ordered by the value's sort_order (its `lang` row first, then English).
 */
export function toListOptions(items: ListItemLike[], lang: string = currentLang()): ListOption[] {
  const all = labelsByValue(items);
  const order = new Map<string, number>();
  const rank = (it: ListItemLike) => (it.lang === lang ? 0 : it.lang === "en" || !it.lang ? 1 : 2);
  const best = new Map<string, number>();
  for (const it of items) {
    if (!it.value) continue;
    const r = rank(it);
    if (!best.has(it.value) || r < (best.get(it.value) as number)) {
      best.set(it.value, r);
      order.set(it.value, it.sort_order ?? 0);
    }
  }
  return [...order.keys()]
    .sort((a, b) => (order.get(a) as number) - (order.get(b) as number))
    .map((value) => ({ value, label: labelIn(all[value], lang, value), labels: all[value] ?? { en: value } }));
}

/** Attribute value for an element whose text is a list label. */
export const listLabelsAttr = (byLang: Record<string, string> | undefined): string | undefined =>
  byLang && Object.keys(byLang).length ? JSON.stringify(byLang) : undefined;

/** Mark an existing element as a relabelable list label and paint it now. */
export function setListLabel(el: Element, byLang: Record<string, string> | undefined, fallback = ""): void {
  const attr = listLabelsAttr(byLang);
  if (attr) el.setAttribute(LIST_LABELS_ATTR, attr);
  else el.removeAttribute(LIST_LABELS_ATTR);
  el.textContent = labelIn(byLang, currentLang(), fallback);
}

/** One `<option>` for a list value, relabeled on language switch. */
export function listOption(value: string, byLang: Record<string, string>): HTMLOptionElement {
  const opt = document.createElement("option");
  opt.value = value;
  setListLabel(opt, byLang, value);
  return opt;
}

/**
 * Replace a select's options (after the first `keep` fixed ones, e.g. a
 * "— choose —" placeholder) with list options that follow the language.
 * Keeps the current selection when it is still offered.
 */
export function fillListSelect(
  sel: HTMLSelectElement | null,
  options: { value: string; labels: Record<string, string> }[],
  keep = 1,
): void {
  if (!sel) return;
  const selected = sel.value;
  while (sel.options.length > keep) sel.remove(keep);
  for (const o of options) sel.appendChild(listOption(o.value, o.labels));
  if (selected && options.some((o) => o.value === selected)) sel.value = selected;
}

/** Rewrite every `[data-list-labels]` element under `root` in the current language. */
export function relabelLists(root: ParentNode = document, lang: string = currentLang()): void {
  root.querySelectorAll<HTMLElement>(`[${LIST_LABELS_ATTR}]`).forEach((el) => {
    try {
      const byLang = JSON.parse(el.getAttribute(LIST_LABELS_ATTR) || "{}");
      const next = labelIn(byLang, lang);
      if (next && el.textContent !== next) el.textContent = next;
    } catch {
      /* malformed attribute — keep the rendered text */
    }
  });
}
