/**
 * toast — top-layer notifications.
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

const VARIANT_CLASSES: Record<ToastVariant, string> = {
  error:
    "bg-red-50 text-red-800 border-red-200 dark:bg-red-900/20 dark:text-red-400 dark:border-red-800",
  success:
    "bg-green-50 text-green-800 border-green-200 dark:bg-green-900/20 dark:text-green-400 dark:border-green-800",
  info: "bg-blue-50 text-blue-800 border-blue-200 dark:bg-blue-900/20 dark:text-blue-400 dark:border-blue-800",
};

let container: HTMLDialogElement | null = null;

/** Lazily create (or recover) the single top-layer toast container. */
function getContainer(): HTMLDialogElement {
  if (container && document.body.contains(container)) return container;

  const dlg = document.createElement("dialog");
  dlg.id = "toast-layer";
  dlg.setAttribute("aria-live", "polite");
  dlg.setAttribute("aria-atomic", "true");
  // Neutralize the default <dialog> box and pin it top-right. `pointer-events:
  // none` lets clicks pass through the empty container; each toast re-enables
  // them for itself so its close button stays clickable.
  Object.assign(dlg.style, {
    position: "fixed",
    top: "1rem",
    right: "1rem",
    left: "auto",
    bottom: "auto",
    margin: "0",
    padding: "0",
    border: "0",
    background: "transparent",
    width: "auto",
    maxWidth: "28rem",
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
  toast.style.pointerEvents = "auto";
  toast.className = `mb-2 max-w-md p-4 rounded-lg border shadow-lg transition-all duration-300 ${VARIANT_CLASSES[v]}`;

  const row = document.createElement("div");
  row.className = "flex items-start gap-3";

  const text = document.createElement("div");
  text.className = "flex-1 text-sm font-medium";
  text.textContent = message;

  const closeBtn = document.createElement("button");
  closeBtn.type = "button";
  closeBtn.setAttribute("aria-label", "Close");
  closeBtn.className = "flex-shrink-0 text-gray-400 hover:text-gray-600";
  closeBtn.textContent = "✕";

  row.append(text, closeBtn);
  toast.appendChild(row);

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
    toast.style.transform = "translateX(100%)";
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

  setTimeout(dismiss, 5000);
}

/** Register `window.showToast` so existing handlers reach the top-layer toast. */
export function installGlobalToast(): void {
  if (typeof window !== "undefined") {
    (window as unknown as { showToast: typeof showToast }).showToast = showToast;
  }
}
