/**
 * initTabs — a tiny, framework-free tab toggler shared by any markup that uses
 * the `data-tab` / `data-tab-panel` convention (see components/ui/Tabs.astro).
 *
 * Show/hide by attribute so ALL panels stay mounted in the DOM (forms still
 * submit hidden-tab inputs). Active styling is a fixed indigo underline; page-
 * level theming (e.g. a hero gradient) is layered by the page, not here.
 */
export interface TabsApi {
  /** Activate a tab + its panel by key. */
  activate(key: string): void;
  /** The currently active tab key (or null before first activate). */
  current(): string | null;
}

const ON = ["border-indigo-600", "text-indigo-600", "dark:text-indigo-400"];
const OFF = [
  "border-transparent", "text-gray-500", "hover:border-gray-300",
  "hover:text-gray-700", "dark:text-gray-400", "dark:hover:text-gray-200",
];

export function initTabs(
  root: ParentNode = document,
  opts: { onActivate?: (key: string) => void } = {},
): TabsApi {
  const buttons = Array.from(root.querySelectorAll<HTMLButtonElement>("[data-tab]"));
  const panels = Array.from(root.querySelectorAll<HTMLElement>("[data-tab-panel]"));
  let active: string | null = null;

  function activate(key: string): void {
    active = key;
    for (const b of buttons) {
      const on = b.dataset.tab === key;
      b.setAttribute("aria-selected", String(on));
      if (on) b.removeAttribute("tabindex");
      else b.setAttribute("tabindex", "-1");
      b.classList.remove(...ON, ...OFF);
      b.classList.add(...(on ? ON : OFF));
    }
    for (const p of panels) {
      p.classList.toggle("hidden", p.dataset.tabPanel !== key);
    }
    opts.onActivate?.(key);
  }

  for (const b of buttons) {
    b.addEventListener("click", () => activate(b.dataset.tab || ""));
  }

  return { activate, current: () => active };
}
