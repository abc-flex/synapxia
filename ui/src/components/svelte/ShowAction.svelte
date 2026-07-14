<script lang="ts">
  /**
   * ShowAction — HU-Show Action as a Svelte island (the first framework pilot).
   * Read-only view of a PUBLICATION / REJECTION outcome action for the current
   * user: fetches the action (+ asset name), renders a branded card, marks the
   * notification seen on open, and offers Back / Dismiss.
   *
   * Reuses the EXISTING vanilla services unchanged (getAction / getAsset /
   * markNotified / dismissNotification / showToast / translate) — only the
   * render + state layer is Svelte. Mounted `client:load` from show-action.astro.
   */
  import { onMount } from "svelte";
  import { getAction } from "@/lib/actions";
  import { getAsset } from "@/lib/assets";
  import { dismissNotification, markNotified } from "@/lib/notifications";
  import { formatRelative } from "@/lib/datatable";
  import { translate } from "@/utils/i18nClient";
  import { showToast } from "@/lib/toast";

  const ICON_CHECK =
    `<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9" /><path d="M8.5 12.5l2.5 2.5 4.5-5" stroke-linecap="round" stroke-linejoin="round" /></svg>`;
  const ICON_X =
    `<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9" /><path d="M15 9l-6 6M9 9l6 6" stroke-linecap="round" /></svg>`;
  const ICON_INFO =
    `<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9" /><path d="M12 11v5M12 8h.01" stroke-linecap="round" /></svg>`;

  type Theme = { grad: string; icon: string; titleKey: string };
  const THEMES: Record<string, Theme> = {
    PUBLICATION: { grad: "from-emerald-500 to-emerald-600", icon: ICON_CHECK, titleKey: "show_action.outcome_published" },
    REJECTION: { grad: "from-red-500 to-red-600", icon: ICON_X, titleKey: "show_action.outcome_rejected" },
  };
  const THEME_DEFAULT: Theme = { grad: "from-indigo-500 to-indigo-600", icon: ICON_INFO, titleKey: "show_action.title" };

  // Bump on language switch so the `t()` calls in the markup re-run.
  let langTick = $state(0);
  const t = (key: string, fallback: string): string => {
    void langTick; // reactive dep
    try {
      const v = translate(key);
      if (v && v !== key) return v;
    } catch {
      /* non-fatal */
    }
    return fallback;
  };

  let theme = $state<Theme>(THEME_DEFAULT);
  let assetName = $state("");
  let message = $state("");
  let hasMessage = $state(false);
  let timeAgo = $state("");
  let dismissing = $state(false);

  const actionId = (): number =>
    Number(new URLSearchParams(window.location.search).get("action") || "");
  const locale = (): string => localStorage.getItem("lang") || "en";

  function goBack(): void {
    if (window.history.length > 1) window.history.back();
    else window.location.href = "/";
  }

  async function dismiss(): Promise<void> {
    const id = actionId();
    if (!id) return goBack();
    dismissing = true;
    try {
      await dismissNotification(id);
      showToast(t("show_action.dismissed", "Notification dismissed"), "success");
      setTimeout(goBack, 600);
    } catch {
      dismissing = false;
      showToast(t("notifications.error", "Could not update the notification"), "error");
    }
  }

  onMount(() => {
    const onLang = () => (langTick += 1);
    window.addEventListener("languageChanged", onLang);

    void (async () => {
      const id = actionId();
      if (!id) {
        message = t("show_action.not_found", "This notification could not be found.");
        return;
      }
      let action: Awaited<ReturnType<typeof getAction>>;
      try {
        action = await getAction(id);
      } catch {
        theme = THEME_DEFAULT;
        message = t("show_action.not_found", "This notification could not be found.");
        return;
      }

      theme = THEMES[(action.type || "").toUpperCase()] || THEME_DEFAULT;

      assetName = `#${action.asset}`;
      try {
        const asset = await getAsset(action.asset);
        if (asset && asset.name) assetName = asset.name;
      } catch {
        /* keep the #id fallback */
      }

      const msg = (action.content || action.detail || "").trim();
      hasMessage = !!msg;
      message = msg || t("show_action.no_message", "No message provided.");
      if (action.created_at) timeAgo = formatRelative(action.created_at, locale());

      // Opening the outcome marks it seen (ASSIGNED → NOTIFIED); idempotent.
      try {
        await markNotified(id);
      } catch {
        /* not the owner / already past ASSIGNED — non-fatal */
      }
    })();

    return () => window.removeEventListener("languageChanged", onLang);
  });
</script>

<article class="overflow-hidden rounded-2xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900">
  <div class={`flex items-start gap-4 bg-gradient-to-br ${theme.grad} px-6 py-5 text-white`}>
    <span class="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-white/20 text-white">
      {@html theme.icon}
    </span>
    <div class="min-w-0">
      <h1 class="text-lg font-semibold">{t(theme.titleKey, "Action")}</h1>
      <p class="mt-0.5 truncate text-sm text-white/85">{assetName}</p>
    </div>
  </div>

  <div class="space-y-4 px-6 py-5">
    <div>
      <p class="mb-1 text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
        {t("show_action.message", "Message")}
      </p>
      <p class={`whitespace-pre-wrap text-sm ${hasMessage ? "text-gray-800 dark:text-gray-200" : "italic text-gray-400"}`}>
        {message}
      </p>
    </div>
    {#if timeAgo}
      <p class="text-xs text-gray-400 dark:text-gray-500">{timeAgo}</p>
    {/if}
  </div>

  <div class="flex items-center justify-end gap-3 border-t border-gray-200 px-6 py-4 dark:border-gray-800">
    <button
      type="button"
      onclick={goBack}
      class="inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
    >{t("show_action.back", "Back")}</button>
    <button
      type="button"
      onclick={dismiss}
      disabled={dismissing}
      class="inline-flex items-center justify-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-50 disabled:opacity-60 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800"
    >{t("show_action.dismiss", "Dismiss")}</button>
  </div>
</article>
