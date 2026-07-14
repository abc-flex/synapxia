/**
 * toast — top-layer notifications, styled after Sonner (https://sonner.emilkowal.sk).
 *
 * Sonner itself is React-only and this UI is deliberately framework-free
 * (Astro + vanilla TS), so this is a dependency-free re-creation of Sonner's
 * look & feel: a neutral opaque card with a colored status icon, rounded
 * corners + subtle shadow, anchored **bottom-right**, stacked with the newest
 * nearest the corner, sliding up + fading in and out.
 *
 * Why a `<dialog>`: the catalog detail view is a native `<dialog>.showModal()`,
 * which the browser promotes into the *top layer* — a paint layer that sits
 * above the entire page regardless of `z-index`. A toast appended to
 * `document.body` with `z-50` therefore renders *behind* an open modal. The
 * only reliable fix is to put the toast into the top layer too: a non-modal
 * `<dialog>.show()` joins the top layer without a backdrop and without trapping
 * focus/clicks. We re-promote the container on every toast so it always sits
 * above whatever modal is currently open.
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

let container: HTMLDialogElement | null = null;

/** Lazily create (or recover) the single top-layer toast container. */
function getContainer(): HTMLDialogElement {
  if (container && document.body.contains(container)) return container;

  const dlg = document.createElement("dialog");
  dlg.id = "toast-layer";
  dlg.setAttribute("aria-live", "polite");
  dlg.setAttribute("aria-atomic", "true");
  // Neutralize the default <dialog> box and pin it bottom-right. `pointer-events:
  // none` lets clicks pass through the empty container; each toast re-enables
  // them for itself so its close button stays clickable. With `bottom` fixed and
  // block-flow children, the box grows upward and the newest (last-appended)
  // toast sits nearest the corner — matching Sonner.
  Object.assign(dlg.style, {
    position: "fixed",
    bottom: "1rem",
    right: "1rem",
    top: "auto",
    left: "auto",
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
  document.body.appendChild(dlg);
  container = dlg;
  return dlg;
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

  const dlg = getContainer();

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
    // Close the container when the last toast is gone so it leaves the top
    // layer (and stops intercepting nothing).
    if (dlg.children.length === 0 && dlg.open) dlg.close();
  };
  const dismiss = () => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(16px)";
    setTimeout(remove, 300);
  };
  closeBtn.addEventListener("click", dismiss);

  dlg.appendChild(toast);

  // (Re)promote to the top of the top layer so we paint above any modal opened
  // after the container was first created. close()+show() is synchronous, so
  // existing toasts don't flicker.
  try {
    if (dlg.open) dlg.close();
    dlg.show();
  } catch {
    /* show() can throw if the dialog was removed; the next toast re-creates it. */
  }

  // Animate in on the next frame (start state was set above).
  requestAnimationFrame(() => {
    toast.style.opacity = "1";
    toast.style.transform = "translateY(0)";
  });

  setTimeout(dismiss, 4000);
}

/** Register `window.showToast` so existing handlers reach the top-layer toast. */
export function installGlobalToast(): void {
  if (typeof window !== "undefined") {
    (window as unknown as { showToast: typeof showToast }).showToast = showToast;
  }
}
