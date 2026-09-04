/**
 * Shared "Show/Hide detail" disclosure control for vanilla-DOM surfaces —
 * icon (eye/eye-off) + label + a small switch, all as one clickable button
 * that toggles a target element's `hidden` class. Pure visibility toggle: it
 * never touches the target's content, only whether it's shown, and always
 * starts collapsed (the target must carry `hidden` up front).
 *
 * Used by the Propose page's Characteristics tab and the read-only catalog
 * detail view's per-characterization elaboration. The Svelte equivalent
 * (`AssetDetailTabs.svelte`'s `toggleCharDetail`) is reimplemented
 * declaratively there — Svelte's reactivity model doesn't fit calling into a
 * vanilla DOM builder — but renders the identical icon/label/switch markup.
 */
const EYE_OPEN_SVG =
  '<svg viewBox="0 0 20 20" fill="currentColor" class="h-3.5 w-3.5" aria-hidden="true">' +
  '<path d="M10 3.5c-4.5 0-8 3.5-9.5 6.5C1.99 13 5.5 16.5 10 16.5s8.01-3.5 9.5-6.5C18 7 14.5 3.5 10 3.5zm0 11a4.5 4.5 0 110-9 4.5 4.5 0 010 9z"></path>' +
  '<circle cx="10" cy="10" r="2"></circle></svg>';
const EYE_OFF_SVG =
  '<svg viewBox="0 0 20 20" fill="currentColor" class="h-3.5 w-3.5" aria-hidden="true">' +
  '<path d="M2.53 2.47a.75.75 0 00-1.06 1.06l3.02 3.02C2.6 8.03 1.2 9.6.5 10.5c1.99 3 5.5 6.5 9.5 6.5 1.5 0 2.9-.35 4.15-.95l2.32 2.32a.75.75 0 101.06-1.06L2.53 2.47zM10 14.5a4.47 4.47 0 01-3.02-1.18l1.14-1.14A2.98 2.98 0 0010 13a3 3 0 003-3c0-.4-.08-.78-.22-1.12l1.14-1.14A4.47 4.47 0 0113.5 10 4.5 4.5 0 0110 14.5zM10 3.5c1.5 0 2.9.35 4.15.95l-1.24 1.24A6.98 6.98 0 0010 5.5a7 7 0 00-6.16 3.65L2.6 7.9C4.1 5.5 6.9 3.5 10 3.5z"></path></svg>';

export interface DetailToggleOptions {
  /** Translate a key with a fallback — callers supply their own i18n hookup
   * since this module has no opinion on which i18n mechanism is in play. */
  tr: (key: string, fallback: string) => string;
  /** Called after every toggle with the new expanded state (e.g. to focus
   * the target once it becomes visible). */
  onToggle?: (expanded: boolean) => void;
}

/** Builds the toggle button. `target`'s `hidden` class is the single source
 * of truth for the current state — the caller must add `hidden` to it
 * up front so the control starts collapsed. */
export function buildDetailToggle(target: HTMLElement, opts: DetailToggleOptions): HTMLButtonElement {
  const { tr, onToggle } = opts;
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className =
    "flex shrink-0 items-center gap-1.5 text-[11px] font-medium text-gray-500 hover:text-indigo-600 dark:text-gray-400 dark:hover:text-indigo-400";
  const icon = document.createElement("span");
  icon.className = "inline-flex h-3.5 w-3.5";
  const labelSpan = document.createElement("span");
  const thumb = document.createElement("span");
  const track = document.createElement("span");
  track.appendChild(thumb);
  btn.append(icon, labelSpan, track);

  const paint = () => {
    const expanded = !target.classList.contains("hidden");
    btn.setAttribute("aria-pressed", expanded ? "true" : "false");
    icon.innerHTML = expanded ? EYE_OFF_SVG : EYE_OPEN_SVG;
    labelSpan.textContent = expanded
      ? tr("asset_detail_modal.characterization_hide_detail", "Hide detail")
      : tr("asset_detail_modal.characterization_show_detail", "Show detail");
    track.className = `relative inline-block h-4 w-7 shrink-0 rounded-full transition ${expanded ? "bg-indigo-600" : "bg-gray-300 dark:bg-gray-600"}`;
    thumb.className = `absolute top-0.5 left-0.5 h-3 w-3 rounded-full bg-white shadow transition ${expanded ? "translate-x-3" : ""}`;
  };

  btn.addEventListener("click", () => {
    target.classList.toggle("hidden");
    paint();
    onToggle?.(!target.classList.contains("hidden"));
  });
  paint();
  return btn;
}
