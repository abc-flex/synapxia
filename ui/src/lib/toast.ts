/**
 * toast — top-layer notifications, styled after Sonner (https://sonner.emilkowal.sk).
 *
 * Sonner itself is React-only and this UI is deliberately framework-free
 * (Astro + vanilla TS), so this is a dependency-free re-creation of Sonner's
 * look & feel: a neutral opaque card with a colored status icon, rounded
 * corners + subtle shadow, anchored **bottom-right**, stacked with the newest
 * nearest the corner, sliding up + fading in and out.
 *
 * Why a popover: the catalog detail view is a native `<dialog>.showModal()`,
 * which the browser promotes into the *top layer* — a paint layer that sits
 * above the entire page regardless of `z-index`. A toast appended to
 * `document.body` with `z-50` therefore renders *behind* an open modal. The
 * only reliable fix is to put the toast into the top layer too.
 *
 * This container used to be a `<dialog>` opened with `.show()`. That was wrong:
 * per the HTML spec only `showModal()` promotes a dialog to the top layer —
 * `show()` renders it as an ordinary positioned element, so the toast still
 * lost to any open modal no matter how large its `z-index`. The container is
 * now a `popover="manual"` element, which *does* join the top layer, without a
 * backdrop, without trapping focus and without light-dismiss. We re-promote it
 * on every toast (hide + show) so it sits above whatever modal opened last.
 * Browsers without the Popover API fall back to the plain fixed/z-index
 * container — the pre-existing behaviour, no worse than before.
 *
 * Public API mirrors the legacy inline `showToast(message, variant)` so vote
 * handlers (`window.showToast`) and page delete handlers keep working
 * unchanged.
 */

export type ToastVariant = "success" | "error" | "info";

// Colored status icon per variant (Sonner shows a neutral card + colored icon).
const VARIANT_ICONS: Record<ToastVariant, string> = {
  success:
    `<svg class="h-5 w-5 text-green-600 dark:text-green-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9" /><path d="M8.5 12.5l2.5 2.5 4.5-5" stroke-linecap="round" stroke-linejoin="round" /></svg>`,
  error:
    `<svg class="h-5 w-5 text-red-600 dark:text-red-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9" /><path d="M15 9l-6 6M9 9l6 6" stroke-linecap="round" /></svg>`,
  info:
    `<svg class="h-5 w-5 text-blue-600 dark:text-blue-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9" /><path d="M12 11v5M12 8h.01" stroke-linecap="round" /></svg>`,
};

const CLOSE_ICON =
  `<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 6l12 12M18 6L6 18" stroke-linecap="round" /></svg>`;

let container: HTMLElement | null = null;

/** True when this browser implements the Popover API (the only reliable way to
 * join the top layer without the focus-trap/backdrop of `showModal()`). */
const supportsPopover = (el: HTMLElement): boolean =>
  typeof (el as { showPopover?: unknown }).showPopover === "function";

/** Lazily create (or recover) the single top-layer toast container. */
function getContainer(): HTMLElement {
  if (container && document.body.contains(container)) return container;

  const box = document.createElement("div");
  box.id = "toast-layer";
  box.setAttribute("aria-live", "polite");
  box.setAttribute("aria-atomic", "true");
  // `popover="manual"` joins the top layer and stays there until we hide it:
  // no light-dismiss on outside clicks / Esc, which would otherwise kill a
  // toast the moment the user clicked anywhere.
  if (supportsPopover(box)) box.setAttribute("popover", "manual");
  // Neutralize the UA popover box (which is centered, bordered and padded by
  // default) and pin it bottom-right. `pointer-events: none` lets clicks pass
  // through the empty container; each toast re-enables them for itself so its
  // close button stays clickable. With `bottom` fixed and block-flow children,
  // the box grows upward and the newest (last-appended) toast sits nearest the
  // corner — matching Sonner. `display` is deliberately NOT set here: the UA
  // toggles it between `none` and `block` as the popover opens and closes.
  Object.assign(box.style, {
    position: "fixed",
    inset: "auto",
    bottom: "1rem",
    right: "1rem",
    margin: "0",
    padding: "0",
    border: "0",
    background: "transparent",
    width: "auto",
    maxWidth: "calc(100vw - 2rem)",
    maxHeight: "none",
    overflow: "visible",
    pointerEvents: "none",
    zIndex: "2147483647",
  });
  document.body.appendChild(box);
  container = box;
  return box;
}

/** Put the container at the top of the top layer, above whatever modal opened
 * last. Hiding then showing re-inserts it; both calls are synchronous, so
 * already-visible toasts don't flicker. No-op where popovers are unsupported —
 * the container then behaves like the plain fixed/z-index box it used to be. */
function promote(box: HTMLElement): void {
  if (!supportsPopover(box)) return;
  const el = box as HTMLElement & {
    showPopover: () => void;
    hidePopover: () => void;
  };
  try {
    el.hidePopover();
  } catch {
    /* not currently showing — nothing to hide */
  }
  try {
    el.showPopover();
  } catch {
    /* detached or not yet connected; the next toast re-creates the container */
  }
}

/** Drop the container out of the top layer once the last toast is gone. */
function demote(box: HTMLElement): void {
  if (!supportsPopover(box)) return;
  try {
    (box as HTMLElement & { hidePopover: () => void }).hidePopover();
  } catch {
    /* already hidden */
  }
}

/**
 * Show a toast. Renders in the browser top layer so it appears above any open
 * modal dialog (e.g. the catalog detail view).
 */
export function showToast(message: string, variant: ToastVariant | string = "info"): void {
  if (typeof document === "undefined") return;
  const v: ToastVariant =
    variant === "error" || variant === "success" || variant === "info"
      ? variant
      : "info";

  const box = getContainer();

  const toast = document.createElement("div");
  toast.setAttribute("role", "alert");
  // Sonner-style neutral card: opaque surface, colored icon, soft border + shadow.
  toast.className =
    "pointer-events-auto mt-3 flex w-[356px] max-w-full items-start gap-3 rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-900 shadow-lg dark:border-gray-800 dark:bg-gray-900 dark:text-gray-100";
  toast.style.transition = "opacity 0.3s ease, transform 0.3s ease";
  toast.style.opacity = "0";
  toast.style.transform = "translateY(16px)";

  const icon = document.createElement("span");
  icon.className = "mt-0.5 flex-shrink-0";
  icon.innerHTML = VARIANT_ICONS[v];

  const text = document.createElement("div");
  text.className = "flex-1 font-medium leading-snug";
  text.textContent = message;

  const closeBtn = document.createElement("button");
  closeBtn.type = "button";
  closeBtn.setAttribute("aria-label", "Close");
  closeBtn.className =
    "-mr-1 -mt-1 flex-shrink-0 rounded p-1 text-gray-400 transition-colors hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300";
  closeBtn.innerHTML = CLOSE_ICON;

  toast.append(icon, text, closeBtn);

  let removed = false;
  const remove = () => {
    if (removed) return;
    removed = true;
    toast.remove();
    // Drop the container out of the top layer when the last toast is gone.
    if (box.children.length === 0) demote(box);
  };
  const dismiss = () => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(16px)";
    setTimeout(remove, 300);
  };
  closeBtn.addEventListener("click", dismiss);

  box.appendChild(toast);

  // (Re)promote to the top of the top layer so we paint above any modal
  // opened after the container was first created.
  promote(box);

  // Animate in on the next frame (start state was set above).
  requestAnimationFrame(() => {
    toast.style.opacity = "1";
    toast.style.transform = "translateY(0)";
  });

  setTimeout(dismiss, 5000);
}

/** Register `window.showToast` so existing handlers reach the top-layer toast. */
export function installGlobalToast(): void {
  if (typeof window !== "undefined") {
    (window as unknown as { showToast: typeof showToast }).showToast = showToast;
  }
}

/* ============================================================
   Flash toast — survives a full-page reload.
   Several CRUD pages show a success toast then immediately call
   `window.location.reload()` to refresh the list (no client-side re-fetch),
   which tears the toast's DOM out mid-display instead of letting it run its
   5s/closable lifecycle. `flashToast` stashes the message in `sessionStorage`
   before the reload; `consumeFlashToast` (called once per page load from
   `BaseLayout.astro`) picks it up and shows it fresh on the reloaded page.
   ============================================================ */

const FLASH_KEY = "synapxia:flash-toast";

/** Queue a toast to show on the *next* page load instead of this one —
 * call this right before a `window.location.reload()` / navigation. */
export function flashToast(message: string, variant: ToastVariant | string = "info"): void {
  if (typeof sessionStorage === "undefined") return;
  try {
    sessionStorage.setItem(FLASH_KEY, JSON.stringify({ message, variant }));
  } catch {
    /* storage unavailable (private mode, quota) — the toast is just skipped */
  }
}

/** Show + clear any toast queued by `flashToast` on the previous page. */
export function consumeFlashToast(): void {
  if (typeof sessionStorage === "undefined") return;
  let raw: string | null = null;
  try {
    raw = sessionStorage.getItem(FLASH_KEY);
    if (raw) sessionStorage.removeItem(FLASH_KEY);
  } catch {
    return;
  }
  if (!raw) return;
  try {
    const parsed = JSON.parse(raw) as { message?: string; variant?: string };
    if (parsed.message) showToast(parsed.message, parsed.variant);
  } catch {
    /* corrupted payload — ignore */
  }
}
