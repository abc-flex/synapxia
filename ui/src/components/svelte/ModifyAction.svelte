<script lang="ts">
  /**
   * ModifyAction — HU-Modify as a Svelte island. The proposer opens a
   * MODIFICATION notification (`/lib/modify?action={id}`), reads the reviewer's
   * feedback, edits the asset (name/description) + its characterizations, and
   * resubmits for re-review. On open it marks the MODIFICATION notification seen
   * (ASSIGNED→NOTIFIED); Resubmit posts to `resubmitAsset`, which flips the asset
   * back to PROPOSED and re-arms the original reviewer. Mirrors ReviewAction's
   * shell; the characterization inputs mirror the Propose form but are prefilled
   * from the asset's existing values.
   */
  import { onMount } from "svelte";
  import { getAction } from "@/lib/actions";
  import { getAsset } from "@/lib/assets";
  import { getCharacterizationsByAsset } from "@/lib/characterizations";
  import { getSpecificationsbyCategory } from "@/lib/specifications";
  import { markNotified } from "@/lib/notifications";
  import { resubmitAsset } from "@/lib/modify";
  import { translate } from "@/utils/i18nClient";
  import { showToast } from "@/lib/toast";
  import { inputClass, labelClass, setFieldInvalid } from "@/lib/formClasses";
  import type { Characterization, Specification } from "@/types/api";

  const ICON_MODIFY =
    `<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 20h9" stroke-linecap="round"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

  // Features whose value is long-form → render as a textarea (mirrors propose.astro).
  const RICH_FEATURES = new Set([
    "PROMPT_TEMPLATE", "EXAMPLE_OUTPUT", "OVERVIEW",
    "CONTENT", "TOOLS", "SERVER_CONFIG", "INSTRUCTIONS",
  ]);

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
  const locale = (): string =>
    (typeof localStorage !== "undefined" && localStorage.getItem("lang")) || "en";

  let loading = $state(true);
  let error = $state("");
  let assetId = $state<number | null>(null);
  let category = $state("");
  let assetStatus = $state("");
  let feedback = $state("");
  let feedbackAt = $state("");

  let name = $state("");
  let description = $state("");
  let specs = $state<Specification[]>([]);
  let charValues = $state<Record<string, string>>({});
  let submitting = $state(false);
  let nameEl = $state<HTMLInputElement | undefined>(undefined);

  const actionId = (): number =>
    Number(new URLSearchParams(window.location.search).get("action") || "");

  const isRich = (feature: string): boolean => RICH_FEATURES.has(feature);
  const charId = (feature: string): string => `modify-char-${feature}`;

  // Only a FEEDBACK asset can be resubmitted. The MODIFICATION action stays
  // ASSIGNED forever (new row per transition), so this page is reachable for an
  // asset that already moved on (e.g. resubmitted, or approved/rejected) via a
  // direct URL / back button / stale tab — where a resubmit would just 409.
  // Guard the form; only block when we positively know the status isn't FEEDBACK.
  const blocked = $derived(!!assetStatus && assetStatus !== "FEEDBACK");

  function goHome(): void {
    if (window.history.length > 1) window.history.back();
    else window.location.href = "/";
  }

  function fmtDate(iso: string): string {
    try {
      return new Date(iso).toLocaleString(locale());
    } catch {
      return "";
    }
  }

  async function resubmit(): Promise<void> {
    if (assetId == null || submitting) return;

    // Name is required.
    if (!name.trim()) {
      setFieldInvalid(nameEl ?? null, null, true);
      nameEl?.focus();
      showToast(t("modify.name_required", "Please enter a name."), "error");
      return;
    }
    // Required characterizations must be filled.
    for (const spec of specs) {
      if (spec.required && !(charValues[spec.feature] ?? "").trim()) {
        const el = document.getElementById(charId(spec.feature)) as
          | HTMLInputElement
          | HTMLTextAreaElement
          | null;
        setFieldInvalid(el, null, true);
        el?.focus();
        showToast(
          t("modify.characterization_required", "Please fill in all required fields."),
          "error",
        );
        return;
      }
    }

    // Send every visible characterization (trimmed) so edits + clears both apply.
    const values: Record<string, string> = {};
    for (const spec of specs) values[spec.feature] = (charValues[spec.feature] ?? "").trim();

    submitting = true;
    try {
      await resubmitAsset(assetId, {
        name: name.trim(),
        description: description.trim() || undefined,
        values: Object.keys(values).length ? values : undefined,
      });
      showToast(t("modify.resubmitted", "Asset resubmitted for review."), "success");
      setTimeout(goHome, 700);
    } catch (err) {
      submitting = false;
      showToast(
        err instanceof Error ? err.message : t("modify.error", "Could not resubmit the asset"),
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
        error = t("modify.not_found", "This modification could not be found.");
        loading = false;
        return;
      }
      let action: Awaited<ReturnType<typeof getAction>>;
      try {
        action = await getAction(id);
      } catch {
        error = t("modify.not_found", "This modification could not be found.");
        loading = false;
        return;
      }
      if ((action.type || "").toUpperCase() !== "MODIFICATION") {
        error = t("modify.not_a_modification", "This notification is not a modification request.");
        loading = false;
        return;
      }
      feedback = (action.content || action.detail || "").trim();
      feedbackAt = action.created_at ? fmtDate(action.created_at) : "";
      assetId = action.asset;

      try {
        const asset = await getAsset(action.asset);
        name = asset?.name || "";
        description = asset?.description || "";
        category = asset?.category || "";
        assetStatus = asset?.status || "";
      } catch {
        /* keep blanks */
      }

      // Build the characterization editor from the category specs, prefilled with
      // the asset's existing values (fall back to the spec default).
      let existing: Characterization[] = [];
      try {
        existing = await getCharacterizationsByAsset(action.asset);
      } catch {
        existing = [];
      }
      const byFeature = new Map(existing.map((c) => [c.feature, c]));
      if (category) {
        try {
          const list = await getSpecificationsbyCategory(category, 0, 1000);
          specs = list;
          const seed: Record<string, string> = {};
          for (const spec of list) {
            const cur = byFeature.get(spec.feature);
            seed[spec.feature] =
              (cur?.value ?? "") || (spec.default_value ?? "") || "";
          }
          charValues = seed;
        } catch {
          specs = [];
        }
      }

      loading = false;
      // Opening the modify view marks it seen (ASSIGNED→NOTIFIED); idempotent.
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
  <div class="flex items-start gap-4 bg-gradient-to-br from-indigo-500 to-indigo-600 px-6 py-5 text-white">
    <span class="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-white/20 text-white">
      {@html ICON_MODIFY}
    </span>
    <div class="min-w-0">
      <h1 class="text-lg font-semibold">{t("modify.title", "Edit & resubmit")}</h1>
      <p class="mt-0.5 truncate text-sm text-white/85">{name}</p>
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
        {t("modify.subtitle", "Address the reviewer's feedback, then resubmit for review.")}
      </p>

      <!-- Reviewer feedback (read-only) -->
      <div class="rounded-lg border border-amber-300 bg-amber-50 p-3 dark:border-amber-500/40 dark:bg-amber-500/10">
        <p class="mb-1 text-xs font-semibold uppercase tracking-wide text-amber-700 dark:text-amber-300">
          {t("modify.feedback_label", "Reviewer feedback")}
        </p>
        <p class={`whitespace-pre-wrap break-words text-sm ${feedback ? "text-gray-800 dark:text-gray-200" : "italic text-gray-400"}`}>
          {feedback || t("modify.no_feedback", "No feedback was provided.")}
        </p>
        {#if feedbackAt}
          <p class="mt-1 text-xs text-gray-400 dark:text-gray-500">{feedbackAt}</p>
        {/if}
      </div>

      {#if blocked}
        <div class="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-500/40 dark:bg-amber-500/10 dark:text-amber-200">
          {t("modify.not_actionable", "This asset is no longer awaiting changes.")}
        </div>
      {:else}
        <!-- Editable name + description -->
        <div>
          <label for="modify-name" class={labelClass}>{t("modify.name", "Name")}</label>
          <input
            id="modify-name"
            bind:this={nameEl}
            bind:value={name}
            type="text"
            class={inputClass}
            oninput={() => setFieldInvalid(nameEl ?? null, null, false)}
          />
        </div>
        <div>
          <label for="modify-description" class={labelClass}>{t("modify.description", "Description")}</label>
          <textarea id="modify-description" bind:value={description} rows="3" class={inputClass}></textarea>
        </div>

        <!-- Editable characterizations -->
        {#if specs.length > 0}
          <div class="space-y-3">
            <p class="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
              {t("modify.characterizations", "Characterization")}
            </p>
            {#each specs as spec (spec.feature)}
              <div>
                <label for={charId(spec.feature)} class={labelClass}>
                  <span>{t(`feature.${spec.feature}`, spec.feature)}</span>{#if spec.required}<span class="ml-0.5 text-red-500">*</span>{/if}
                </label>
                {#if isRich(spec.feature)}
                  <textarea
                    id={charId(spec.feature)}
                    bind:value={charValues[spec.feature]}
                    rows="4"
                    class={inputClass}
                    oninput={(e) => setFieldInvalid(e.currentTarget, null, false)}
                  ></textarea>
                {:else}
                  <input
                    id={charId(spec.feature)}
                    bind:value={charValues[spec.feature]}
                    type="text"
                    class={inputClass}
                    oninput={(e) => setFieldInvalid(e.currentTarget, null, false)}
                  />
                {/if}
              </div>
            {/each}
          </div>
        {/if}
      {/if}
    {/if}
  </div>

  {#if !loading && !error && !blocked}
    <div class="flex flex-col gap-3 border-t border-gray-200 px-6 py-4 sm:flex-row dark:border-gray-800">
      <button
        type="button"
        disabled={submitting}
        onclick={resubmit}
        class="inline-flex flex-1 items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:opacity-60"
      >
        {t("modify.resubmit", "Resubmit for review")}
      </button>
      <button
        type="button"
        disabled={submitting}
        onclick={goHome}
        class="inline-flex items-center justify-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-50 disabled:opacity-60 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-white/5"
      >
        {t("modify.cancel", "Cancel")}
      </button>
    </div>
  {:else if !loading && !error && blocked}
    <div class="flex border-t border-gray-200 px-6 py-4 dark:border-gray-800">
      <button
        type="button"
        onclick={goHome}
        class="inline-flex items-center justify-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-50 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-white/5"
      >
        {t("modify.cancel", "Back")}
      </button>
    </div>
  {/if}
</article>
