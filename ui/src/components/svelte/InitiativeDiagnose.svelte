<script lang="ts">
  /**
   * InitiativeDiagnose — Diagnosis of the Initiative (HU-IN15,
   * specs/005-explore-initiatives US6). The assigned reviewer opens it from the
   * bell or My Initiative Requests (`/inits/diagnose?collab={id}`), reads the
   * initiative and the proposer's answers, scores every criterion and accepts,
   * rejects or requests changes. Opening the page writes nothing.
   */
  import { onMount } from "svelte";
  import DiagnosisTable from "@/components/svelte/DiagnosisTable.svelte";
  import { getCollaboration } from "@/lib/collaborations";
  import {
    diagnoseInitiative, getDiagnosisForm, getInitiativeAssets, getInitiativeDiagnostics,
  } from "@/lib/initiatives";
  import { loadInitiativeLists, labelOf, currentLang, type InitiativeLists } from "@/lib/initiativeLists";
  import { notifyChanged } from "@/lib/notificationsStore";
  import { apiErrorDetail } from "@/lib/api";
  import { translate } from "@/utils/i18nClient";
  import { showToast } from "@/lib/toast";
  import type {
    CollaborationDetail, DiagnosisDecision, DiagnosticRow, InitiativeAsset, ScaleOption,
  } from "@/types/api";

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

  let collab = $state<CollaborationDetail | null>(null);
  let lists = $state<InitiativeLists>({ type: [], impact: [], priority: [], status: [] });
  let rows = $state<DiagnosticRow[]>([]);
  let scales = $state<Record<string, ScaleOption[]>>({});
  let assets = $state<InitiativeAsset[]>([]);
  let loading = $state(true);
  let notFound = $state(false);
  let feedback = $state("");
  let feedbackInvalid = $state(false);
  let submitting = $state(false);
  let table = $state<{ validate(): string[]; getReviewerAnswers(): Record<string, number> } | undefined>(undefined);

  const initiative = $derived(collab?.initiative ?? null);
  const blocked = $derived(
    !!collab && (collab.current_status !== "PENDING" || initiative?.status !== "ACTIVATED"),
  );

  onMount(() => {
    const onLang = () => (langTick += 1);
    window.addEventListener("languageChanged", onLang);
    void load();
    return () => window.removeEventListener("languageChanged", onLang);
  });

  async function load(): Promise<void> {
    const id = Number(new URLSearchParams(location.search).get("collab"));
    try {
      if (!id) throw new Error("missing");
      const c = await getCollaboration(id);
      if (c.type !== "DIAGNOSIS" || !c.initiative) throw new Error("wrong type");
      collab = c;
      const lang = currentLang();
      const [l, diag, form, links] = await Promise.all([
        loadInitiativeLists(lang),
        getInitiativeDiagnostics(c.init, lang),
        getDiagnosisForm(lang),
        getInitiativeAssets(c.init).catch(() => [] as InitiativeAsset[]),
      ]);
      lists = l;
      rows = diag.items;
      scales = form.scales;
      assets = links;
    } catch {
      notFound = true;
    } finally {
      loading = false;
    }
  }

  async function decide(decision: DiagnosisDecision): Promise<void> {
    if (!collab || submitting) return;
    const fb = feedback.trim();
    feedbackInvalid = decision !== "accept" && !fb;
    const missing = table?.validate() ?? [];
    if (missing.length) {
      showToast(t("inits_diagnose.answers_required", "Answer every diagnosis question first."), "error");
      return;
    }
    if (feedbackInvalid) {
      showToast(t("inits_diagnose.feedback_required", "Feedback is required to reject or request changes."), "error");
      return;
    }
    submitting = true;
    try {
      await diagnoseInitiative(collab.init, {
        decision,
        feedback: fb || null,
        answers: table?.getReviewerAnswers() ?? {},
      });
      notifyChanged();
      window.location.href = "/inits/my_initiative_requests";
    } catch (err) {
      showToast(apiErrorDetail(err, t("inits_diagnose.error", "The decision could not be saved.")), "error");
      submitting = false;
    }
  }

  const field = "text-xs font-semibold uppercase tracking-wide text-gray-400";
  const value = "mt-1 whitespace-pre-line break-words text-sm text-gray-800 dark:text-gray-200";
  const btnBase =
    "inline-flex flex-1 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold text-white transition disabled:opacity-60";
</script>

<article class="overflow-hidden rounded-2xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900">
  <div class="flex items-start gap-4 bg-gradient-to-br from-amber-500 to-orange-500 px-6 py-5 text-white">
    <span class="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-white/20" aria-hidden="true">
      <svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" stroke-linecap="round" stroke-linejoin="round" /></svg>
    </span>
    <div class="min-w-0">
      <h1 class="truncate text-lg font-bold">{initiative?.name || (loading ? t("common.loading", "Loading…") : t("inits_diagnose.title", "Diagnose Initiative"))}</h1>
      <p class="mt-0.5 text-sm text-white/85">{t("inits_diagnose.subtitle", "Score the initiative on every criterion, then accept it, reject it or request changes.")}</p>
    </div>
    {#if initiative}
      <span class="ml-auto shrink-0 rounded-full bg-white/20 px-2.5 py-0.5 text-xs font-medium">{labelOf(lists.status, initiative.status)}</span>
    {/if}
  </div>

  <div class="space-y-6 px-6 py-5">
    {#if loading}
      <p class="text-sm text-gray-400">{t("common.loading", "Loading…")}</p>
    {:else if notFound}
      <p class="text-sm text-red-600 dark:text-red-400">{t("inits_diagnose.not_found", "This diagnosis request could not be found.")}</p>
      <a href="/inits/my_initiative_requests" class="text-sm font-medium text-indigo-600 hover:underline dark:text-indigo-400">{t("inits_diagnose.to_requests", "Go to My Initiative Requests")} →</a>
    {:else if initiative}
      <section class="grid gap-4 sm:grid-cols-3">
        {#if initiative.description}
          <div class="sm:col-span-3"><p class={field}>{t("inits_explore.field_description", "Description")}</p><p class={value}>{initiative.description}</p></div>
        {/if}
        <div><p class={field}>{t("inits_explore.field_type", "Type")}</p><p class={value}>{labelOf(lists.type, initiative.type) || "—"}</p></div>
        <div><p class={field}>{t("inits_explore.field_impact", "Expected impact")}</p><p class={value}>{labelOf(lists.impact, initiative.expected_impact)}</p></div>
        <div><p class={field}>{t("inits_explore.field_priority", "Priority")}</p><p class={value}>{labelOf(lists.priority, initiative.priority_level)}</p></div>
        {#if initiative.reference}
          <div class="sm:col-span-3"><p class={field}>{t("inits_explore.field_reference", "Reference")}</p><p class={value}>{initiative.reference}</p></div>
        {/if}
        {#if initiative.detail}
          <div class="sm:col-span-3"><p class={field}>{t("inits_explore.field_detail", "Detail")}</p><p class={value}>{initiative.detail}</p></div>
        {/if}
        {#if assets.length}
          <div class="sm:col-span-3">
            <p class={field}>{t("inits_diagnose.related_assets", "Related assets")}</p>
            <div class="mt-1 flex flex-wrap gap-2">
              {#each assets as a (`${a.asset}:${a.type}`)}
                <span class="inline-flex items-center gap-1.5 rounded-full bg-gray-100 px-2.5 py-0.5 text-xs text-gray-700 dark:bg-gray-800 dark:text-gray-300">{a.asset_name ?? `#${a.asset}`}<span class="font-semibold text-indigo-600 dark:text-indigo-400">{a.type}</span></span>
              {/each}
            </div>
          </div>
        {/if}
      </section>

      {#if blocked}
        <div class="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-500/40 dark:bg-amber-500/10 dark:text-amber-200">
          {t("inits_diagnose.blocked", "This diagnosis is no longer pending.")}
          <a href="/inits/my_initiative_requests" class="ml-1 font-medium underline">{t("inits_diagnose.to_requests", "Go to My Initiative Requests")}</a>
        </div>
        <DiagnosisTable items={rows} mode="view" />
      {:else}
        <DiagnosisTable bind:this={table} items={rows} mode="review" {scales} />
        <div>
          <label for="diag-feedback" class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">{t("inits_diagnose.feedback", "Feedback for the proposer")}</label>
          <textarea
            id="diag-feedback"
            rows="4"
            maxlength="2000"
            bind:value={feedback}
            oninput={() => (feedbackInvalid = false)}
            placeholder={t("inits_diagnose.feedback_placeholder", "Required when rejecting or requesting changes")}
            aria-invalid={feedbackInvalid ? "true" : "false"}
            class={`w-full rounded-lg border px-3 py-2 text-sm focus:ring-2 dark:bg-gray-800 dark:text-white ${feedbackInvalid ? "border-red-500 focus:ring-red-200" : "border-gray-300 focus:border-indigo-500 focus:ring-indigo-200 dark:border-gray-700"}`}
          ></textarea>
        </div>
      {/if}
    {/if}
  </div>

  {#if !loading && !notFound && !blocked}
    <div class="flex flex-col gap-3 border-t border-gray-200 px-6 py-4 sm:flex-row dark:border-gray-800">
      <button type="button" disabled={submitting} onclick={() => decide("accept")} class={`${btnBase} bg-emerald-600 hover:bg-emerald-700`}>{t("inits_diagnose.accept", "Accept")}</button>
      <button type="button" disabled={submitting} onclick={() => decide("changes")} class={`${btnBase} bg-amber-600 hover:bg-amber-700`}>{t("inits_diagnose.changes", "Request changes")}</button>
      <button type="button" disabled={submitting} onclick={() => decide("reject")} class={`${btnBase} bg-red-600 hover:bg-red-700`}>{t("inits_diagnose.reject", "Reject")}</button>
    </div>
  {/if}
</article>
