/**
 * showAckDialog — open an `AckDialog.astro` and resolve only when the user
 * presses its button. Esc is blocked (the `cancel` event is prevented), so the
 * message cannot be dismissed unread. Resolves immediately if the markup is
 * missing, so a flow is never stuck.
 */

export type AckVariant = "success" | "error";

// Same success/warning treatment as the toast variants (`lib/toast.ts`).
const ACK_ICONS: Record<AckVariant, string> = {
  success:
    `<svg class="h-5 w-5 text-green-600 dark:text-green-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9" /><path d="M8.5 12.5l2.5 2.5 4.5-5" stroke-linecap="round" stroke-linejoin="round" /></svg>`,
  error:
    `<svg class="h-5 w-5 text-amber-500 dark:text-amber-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 9v4M12 16.5h.01" stroke-linecap="round" /><path d="M10.29 3.86 1.82 18a1.5 1.5 0 0 0 1.3 2.25h17.76a1.5 1.5 0 0 0 1.3-2.25L13.71 3.86a1.5 1.5 0 0 0-2.42 0Z" stroke-linejoin="round" /></svg>`,
};

const blocked = new WeakSet<HTMLDialogElement>();

export function showAckDialog(
  dialogId: string,
  message: string,
  variant: AckVariant,
  title?: string,
): Promise<void> {
  return new Promise((resolve) => {
    const dialog = document.getElementById(dialogId) as HTMLDialogElement | null;
    const msg = document.getElementById(`${dialogId}-message`);
    const ok = document.getElementById(`${dialogId}-ok`) as HTMLButtonElement | null;
    if (!dialog || !msg || !ok) {
      resolve();
      return;
    }
    if (!blocked.has(dialog)) {
      dialog.addEventListener("cancel", (e) => e.preventDefault());
      blocked.add(dialog);
    }
    msg.textContent = message;
    const icon = document.getElementById(`${dialogId}-icon`);
    if (icon) icon.innerHTML = ACK_ICONS[variant];
    const titleEl = document.getElementById(`${dialogId}-title`);
    if (titleEl && title) titleEl.textContent = title;
    const onOk = () => {
      ok.removeEventListener("click", onOk);
      dialog.close();
      resolve();
    };
    ok.addEventListener("click", onOk);
    dialog.showModal();
  });
}
