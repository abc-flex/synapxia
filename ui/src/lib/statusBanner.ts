/**
 * statusBanner — shared behavior for the inline "save confirmation" banners
 * used by modals/pages that show a message next to the form instead of a
 * floating toast (AssetDetailModal, the catalog create/edit modal, the
 * profile page). Gives every one of them the same close button + 5s
 * auto-dismiss the floating toast system (`lib/toast.ts`) already has,
 * instead of each screen re-implementing (or forgetting) it.
 */

export type StatusKind = "ok" | "error" | "info";

const TONE: Record<StatusKind, string> = {
  ok: "bg-green-50 text-green-800 border border-green-200 dark:bg-green-900/30 dark:text-green-300 dark:border-green-700",
  error: "bg-red-50 text-red-800 border border-red-200 dark:bg-red-900/30 dark:text-red-300 dark:border-red-700",
  info: "bg-blue-50 text-blue-800 border border-blue-200 dark:bg-blue-950 dark:text-blue-200 dark:border-blue-800",
};

const CLOSE_ICON =
  `<svg class="w-4 h-4" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" /></svg>`;

const AUTO_DISMISS_MS = 5000;

export interface StatusBanner {
  show(message: string, kind?: StatusKind): void;
  clear(): void;
}

/**
 * Wraps a hidden `<div>` (role="status", initially `class="hidden ..."`) into
 * a closable, self-dismissing banner. `baseClass` is whatever layout classes
 * the div already carries (margins differ between a modal banner and a
 * page-level one) — the tone classes are appended to it on every `show()`.
 */
export function createStatusBanner(
  el: HTMLElement | null,
  baseClass = "rounded-lg p-3 text-sm",
): StatusBanner {
  let timer: ReturnType<typeof setTimeout> | null = null;

  const clear = () => {
    el?.classList.add("hidden");
    if (timer) {
      clearTimeout(timer);
      timer = null;
    }
  };

  const show = (message: string, kind: StatusKind = "ok") => {
    if (!el) return;
    if (timer) {
      clearTimeout(timer);
      timer = null;
    }
    el.className = `${baseClass} ${TONE[kind] ?? TONE.ok}`;
    el.innerHTML = "";

    const row = document.createElement("div");
    row.className = "flex items-start gap-2";

    const text = document.createElement("div");
    text.className = "flex-1";
    text.textContent = message;

    const closeBtn = document.createElement("button");
    closeBtn.type = "button";
    closeBtn.setAttribute("aria-label", "Close");
    closeBtn.className =
      "shrink-0 -mr-1 -mt-1 rounded p-1 opacity-70 transition-opacity hover:opacity-100";
    closeBtn.innerHTML = CLOSE_ICON;
    closeBtn.addEventListener("click", clear);

    row.append(text, closeBtn);
    el.appendChild(row);
    el.classList.remove("hidden");

    timer = setTimeout(clear, AUTO_DISMISS_MS);
  };

  return { show, clear };
}
