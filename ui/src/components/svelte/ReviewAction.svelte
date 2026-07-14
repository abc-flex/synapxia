<script lang="ts">
  /**
   * ReviewAction — HU-Review as a Svelte island. The reviewer opens an assigned
   * PROPOSED asset (via `/lib/review?action={id}`), sees its details +
   * characterizations, leaves feedback, and Approves / Rejects / Requests
   * changes. On open it marks the REVIEW notification seen (ASSIGNED→NOTIFIED);
   * the decision posts to `reviewAsset` which flips the asset status and notifies
   * the proposer. Mirrors ShowAction's shell; reuses the existing services.
   */
  import { onMount } from "svelte";
  import { getAction } from "@/lib/actions";
  import { getAsset } from "@/lib/assets";
  import { getCharacterizationsByAsset } from "@/lib/characterizations";
  import { markNotified } from "@/lib/notifications";
  import { reviewAsset } from "@/lib/review";
  import { translate } from "@/utils/i18nClient";
  import { showToast } from "@/lib/toast";
  import { inputClass, labelClass, setFieldInvalid } from "@/lib/formClasses";
  import type { Characterization, ReviewDecision } from "@/types/api";

  const ICON_REVIEW =
    `<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" stroke-linecap="round"/><rect x="9" y="3" width="6" height="4" rx="1"/><path d="m9 14 2 2 4-4" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

  let langTick = $state(0);
  const t = (key: string, fallback: string): string => {
    void langTick;
    try {
      const v = translate(key);
      if (v && v !== key) return v;
    } catch {
      /* non-fatal */
    }
    return fallback;
  };

  let loading = $state(true);
  let error = $state("");
  let assetId = $state<number | null>(null);
  let assetName = $state("");
  let assetStatus = $state("");
  let assetDescription = $state("");
  let chars = $state<Characterization[]>([]);
  let feedback = $state("");
  let submitting = $state(false);
  let feedbackEl = $state<HTMLTextAreaElement | undefined>(undefined);

  const actionId = (): number =>
    Number(new URLSearchParams(window.location.search).get("action") || "");

  const charText = (c: Characterization): string =>
    (c.detail && c.detail.trim()) || (c.value && c.value.trim()) || "";
  const shownChars = $derived(chars.filter((c) => charText(c)));

  // Only a PROPOSED asset can be reviewed. The underlying REVIEW action stays
  // ASSIGNED forever (every workflow step is a new row, never an update), so this
  // page is still reachable for an already-decided asset via a direct URL / the
  // back button / a stale tab — where a decision would just 409. Guard the form
  // so we don't render dead buttons. Only block when we positively know the
  // status isn't PROPOSED (if the asset failed to load, fall through and let the
  // backend 409 be the fallback).
  const blocked = $derived(!!assetStatus && assetStatus !== "PROPOSED");

  function goHome(): void {
    if (window.history.length > 1) window.history.back();
    else window.location.href = "/";
  }

  async function decide(decision: ReviewDecision): Promise<void> {
    if (assetId == null || submitting) return;
    const fb = feedback.trim();
    // Feedback is required when rejecting or requesting changes (the proposer
    // needs to know why); optional on approve.
    if (decision !== "approve" && !fb) {
      setFieldInvalid(feedbackEl ?? null, null, true);
      feedbackEl?.focus();
      showToast(t("review.feedback_required", "Please add feedback for this decision."), "error");
      return;
    }
    submitting = true;
    try {
      await reviewAsset(assetId, decision, fb || undefined);
      const okKey =
        decision === "approve" ? "review.approved"
          : decision === "reject" ? "review.rejected"
            : "review.changes_requested";
      const okFallback =
        decision === "approve" ? "Asset published."
          : decision === "reject" ? "Asset rejected."
            : "Changes requested.";
      showToast(t(okKey, okFallback), "success");
      setTimeout(goHome, 700);
    } catch (err) {
      submitting = false;
      showToast(
        err instanceof Error ? err.message : t("review.error", "Could not submit the review"),
        "error",
      );
    }
  }

  onMount(() => {
    const onLang = () => (langTick += 1);
    window.addEventListener("languageChanged", onLang);

    void (async () => {
      const id = actionId();
      if (!id) {
        error = t("review.not_found", "This review could not be found.");
        loading = false;
        return;
      }
      let action: Awaited<ReturnType<typeof getAction>>;
      try {
        action = await getAction(id);
      } catch {
        error = t("review.not_found", "This review could not be found.");
        loading = false;
        return;
      }
      if ((action.type || "").toUpperCase() !== "REVIEW") {
        error = t("review.not_a_review", "This notification is not a review.");
        loading = false;
        return;
      }
      assetId = action.asset;
      try {
        const asset = await getAsset(action.asset);
        assetName = asset?.name || `#${action.asset}`;
        assetStatus = asset?.status || "";
        assetDescription = asset?.description || "";
      } catch {
        assetName = `#${action.asset}`;
      }
      try {
        chars = await getCharacterizationsByAsset(action.asset);
      } catch {
        chars = [];
      }
      loading = false;
      // Opening the review marks it seen (ASSIGNED→NOTIFIED); idempotent.
      try {
        await markNotified(id);
      } catch {
        /* not the owner / already past ASSIGNED — non-fatal */
      }
    })();

    return () => window.removeEventListener("languageChanged", onLang);
  });

  const btnBase =
    "inline-flex flex-1 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold text-white transition disabled:opacity-60";
</script>

<article class="overflow-hidden rounded-2xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900">
  <div class="flex items-start gap-4 bg-gradient-to-br from-amber-500 to-amber-600 px-6 py-5 text-white">
    <span class="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-white/20 text-white">
      {@html ICON_REVIEW}
    </span>
    <div class="min-w-0">
      <h1 class="text-lg font-semibold">{t("review.title", "Review asset")}</h1>
      <p class="mt-0.5 truncate text-sm text-white/85">{assetName}</p>
    </div>
    {#if assetStatus}
      <span class="ml-auto shrink-0 rounded-full bg-white/20 px-2.5 py-0.5 text-xs font-medium">
        {t(`asset_status.${assetStatus}`, assetStatus)}
      </span>
    {/if}
  </div>

  <div class="space-y-5 px-6 py-5">
    {#if loading}
      <p class="text-sm text-gray-400 dark:text-gray-500">{t("common.loading", "Loading…")}</p>
    {:else if error}
      <p class="text-sm text-red-600 dark:text-red-400">{error}</p>
    {:else}
      <p class="text-xs text-gray-500 dark:text-gray-400">
        {t("review.subtitle", "Review the proposed asset, then approve, request changes, or reject it.")}
      </p>

      {#if assetDescription}
        <p class="whitespace-pre-wrap text-sm text-gray-700 dark:text-gray-300">{assetDescription}</p>
      {/if}

      {#if shownChars.length > 0}
        <div class="space-y-3">
          {#each shownChars as c (c.feature)}
            <div class="rounded-lg border border-gray-200 bg-gray-50/50 p-3 dark:border-gray-800 dark:bg-white/[0.02]">
              <p class="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                {t(`feature.${c.feature}`, c.feature)}
              </p>
              <p class="whitespace-pre-wrap break-words text-sm text-gray-800 dark:text-gray-200">{charText(c)}</p>
            </div>
          {/each}
        </div>
      {/if}

      {#if blocked}
        <div class="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-500/40 dark:bg-amber-500/10 dark:text-amber-200">
          {t("review.not_actionable", "This asset is no longer awaiting review.")}
        </div>
      {:else}
        <div>
          <label for="review-feedback" class={labelClass}>{t("review.feedback_label", "Feedback")}</label>
          <textarea
            id="review-feedback"
            bind:this={feedbackEl}
            bind:value={feedback}
            rows="4"
            class={inputClass}
            placeholder={t("review.feedback_placeholder", "Explain your decision (required to reject or request changes)…")}
            oninput={() => setFieldInvalid(feedbackEl ?? null, null, false)}
          ></textarea>
        </div>
      {/if}
    {/if}
  </div>

  {#if !loading && !error && !blocked}
    <div class="flex flex-col gap-3 border-t border-gray-200 px-6 py-4 sm:flex-row dark:border-gray-800">
      <button type="button" disabled={submitting} onclick={() => decide("approve")} class={`${btnBase} bg-emerald-600 hover:bg-emerald-700`}>
        {t("review.approve", "Approve")}
      </button>
      <button type="button" disabled={submitting} onclick={() => decide("changes")} class={`${btnBase} bg-amber-600 hover:bg-amber-700`}>
        {t("review.request_changes", "Request changes")}
      </button>
      <button type="button" disabled={submitting} onclick={() => decide("reject")} class={`${btnBase} bg-red-600 hover:bg-red-700`}>
        {t("review.reject", "Reject")}
      </button>
    </div>
  {:else if !loading && !error && blocked}
    <div class="flex border-t border-gray-200 px-6 py-4 dark:border-gray-800">
      <button
        type="button"
        onclick={goHome}
        class="inline-flex items-center justify-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-50 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-white/5"
      >
        {t("review.back", "Back")}
      </button>
    </div>
  {/if}
</article>
