/**
 * Shared form styling + validation helpers.
 *
 * These live in a `.ts` (not an `.astro` frontmatter const) so BOTH server-side
 * `.astro` frontmatter AND bundled client islands can import the exact same
 * strings — the island can't read a page's frontmatter consts, which is why
 * pages used to duplicate `inputClass`/`labelClass` inside their `<script>`.
 */

/** Standard text input / select / textarea class. */
export const inputClass =
  "w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-indigo-500 focus:outline-none dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100";

/** Standard field label class. */
export const labelClass =
  "mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300";

/** Inline error-message class (used by FormField's `<p>`). */
export const fieldErrorClass = "mt-1 hidden text-xs text-red-600 dark:text-red-400";

/**
 * Toggle a field's invalid state: swap the neutral border for red and reveal
 * the field's inline error message. Reusable across any form that renders a
 * control + a sibling error `<p>` (e.g. FormField).
 */
export function setFieldInvalid(
  el: HTMLElement | null,
  err: HTMLElement | null,
  invalid: boolean,
): void {
  if (el) {
    el.classList.toggle("border-gray-300", !invalid);
    el.classList.toggle("dark:border-gray-700", !invalid);
    el.classList.toggle("border-red-500", invalid);
    el.classList.toggle("dark:border-red-500", invalid);
    el.setAttribute("aria-invalid", String(invalid));
  }
  err?.classList.toggle("hidden", !invalid);
}
