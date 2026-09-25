<script lang="ts">
  /**
   * InitiativeModify — Modify Initiative (HU-IN16, specs/005-explore-initiatives
   * US7). The proposer opens a change request (`/inits/modify?collab={id}`),
   * reads the reviewer's feedback, edits the core fields and their own
   * diagnosis answers, and resubmits to the same reviewer. Opening writes
   * nothing; only changed core fields are sent, with the full answer set.
   */
  import { onMount } from "svelte";
  import DiagnosisTable from "@/components/svelte/DiagnosisTable.svelte";
  import { getCollaboration } from "@/lib/collaborations";
  import { getDiagnosisForm, getInitiativeDiagnostics, resubmitInitiative } from "@/lib/initiatives";
  import { loadInitiativeLists, labelOf, currentLang, type InitiativeLists } from "@/lib/initiativeLists";
  import { notifyChanged } from "@/lib/notificationsStore";
  import { apiErrorDetail } from "@/lib/api";
  import { translate } from "@/utils/i18nClient";
  import { showToast } from "@/lib/toast";
  import type {
    CollaborationDetail, DiagnosisAnswer, DiagnosticRow, InitiativeResubmitRequest, ScaleOption,
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
  let loading = $state(true);
  let notFound = $state(false);
  let submitting = $state(false);
  let invalid = $state<Set<string>>(new Set());
  let table = $state<{ validate(): string[]; getCreatorAnswers(): Record<string, DiagnosisAnswer> } | undefined>(undefined);

  // Editable core fields, seeded from the initiative.
  let form = $state({
    name: "", description: "", type: "", expected_impact: "", priority_level: "",
    reference: "", tags: "", detail: "",
  });
  let original = { ...form };

  const initiative = $derived(collab?.initiative ?? null);
  const blocked = $derived(
    !!collab && (collab.current_status !== "PENDING" || initiative?.status !== "FEEDBACK"),
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
      if (c.type !== "MODIFICATION" || !c.initiative) throw new Error("wrong type");
      collab = c;
      const i = c.initiative;
      form = {
        name: i.name ?? "",
        description: i.description ?? "",
        type: i.type ?? "",
        expected_impact: i.expected_impact ?? "",
        priority_level: i.priority_level ?? "",
        reference: i.reference ?? "",
        tags: Array.isArray(i.tags) ? (i.tags as string[]).join(", ") : "",
        detail: i.detail ?? "",
      };
      original = { ...form };
      const lang = currentLang();
      const [l, diag, f] = await Promise.all([
        loadInitiativeLists(lang), getInitiativeDiagnostics(c.init, lang), getDiagnosisForm(lang),
      ]);
      lists = l;
      rows = diag.items;
      scales = f.scales;
    } catch {
      notFound = true;
    } finally {
      loading = false;
    }
  }

  async function resubmit(): Promise<void> {
    if (!collab || submitting) return;
    const bad = new Set<string>();
    if (!form.name.trim()) bad.add("name");
    if (!form.expected_impact) bad.add("expected_impact");
    if (!form.priority_level) bad.add("priority_level");
    invalid = bad;
    const missing = table?.validate() ?? [];
    if (bad.size) {
      showToast(t("inits_propose.required", "Please complete the required fields."), "error");
      return;
    }
    if (missing.length) {
      showToast(t("inits_propose.answers_required", "Please answer every diagnosis question."), "error");
      return;
    }
    const payload: InitiativeResubmitRequest = { answers: table?.getCreatorAnswers() ?? {} };
    const text = (v: string) => v.trim() || null;
    if (form.name !== original.name) payload.name = form.name.trim();
    if (form.description !== original.description) payload.description = text(form.description);
    if (form.type !== original.type) payload.type = form.type || null;
    if (form.expected_impact !== original.expected_impact) payload.expected_impact = form.expected_impact;
    if (form.priority_level !== original.priority_level) payload.priority_level = form.priority_level;
    if (form.reference !== original.reference) payload.reference = text(form.reference);
    if (form.detail !== original.detail) payload.detail = text(form.detail);
    if (form.tags !== original.tags) {
      const tags = form.tags.split(",").map((x) => x.trim()).filter(Boolean);
      payload.tags = tags.length ? tags : null;
    }
    submitting = true;
    try {
      await resubmitInitiative(collab.init, payload);
      notifyChanged();
      window.location.href = "/inits/my_initiative_requests";
    } catch (err) {
      showToast(apiErrorDetail(err, t("inits_modify.error", "The initiative could not be resubmitted.")), "error");
      submitting = false;
    }
  }

  const label = "mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300";
  const input = (key: string) =>
    `w-full rounded-lg border px-3 py-2 text-sm focus:ring-2 dark:bg-gray-800 dark:text-white ${invalid.has(key)
      ? "border-red-500 focus:ring-red-200"
      : "border-gray-300 focus:border-indigo-500 focus:ring-indigo-200 dark:border-gray-700"}`;
  const clear = (key: string) => (invalid = new Set([...invalid].filter((k) => k !== key)));
</script>

<article class="overflow-hidden rounded-2xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900">
  <div class="flex items-start gap-4 bg-gradient-to-br from-indigo-500 to-indigo-600 px-6 py-5 text-white">
    <span class="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-white/20" aria-hidden="true">
      <svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L6.832 19.82a4.5 4.5 0 0 1-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 0 1 1.13-1.897L16.863 4.487Z" stroke-linecap="round" stroke-linejoin="round" /></svg>
    </span>
    <div class="min-w-0">
      <h1 class="truncate text-lg font-bold">{initiative?.name || (loading ? t("common.loading", "Loading…") : t("inits_modify.title", "Modify Initiative"))}</h1>
      <p class="mt-0.5 text-sm text-white/85">{t("inits_modify.subtitle", "Apply the reviewer's feedback and resubmit the initiative for diagnosis.")}</p>
    </div>
    {#if initiative}
      <span class="ml-auto shrink-0 rounded-full bg-white/20 px-2.5 py-0.5 text-xs font-medium">{labelOf(lists.status, initiative.status)}</span>
    {/if}
  </div>

  <div class="space-y-6 px-6 py-5">
    {#if loading}
      <p class="text-sm text-gray-400">{t("common.loading", "Loading…")}</p>
    {:else if notFound}
      <p class="text-sm text-red-600 dark:text-red-400">{t("inits_modify.not_found", "This change request could not be found.")}</p>
      <a href="/inits/my_initiative_requests" class="text-sm font-medium text-indigo-600 hover:underline dark:text-indigo-400">{t("inits_diagnose.to_requests", "Go to My Initiative Requests")} →</a>
    {:else if collab}
      <section class="rounded-lg border border-amber-200 bg-amber-50 p-4 dark:border-amber-500/30 dark:bg-amber-500/10">
        <p class="text-xs font-semibold uppercase tracking-wide text-amber-700 dark:text-amber-300">{t("inits_modify.reviewer_feedback", "Reviewer feedback")}</p>
        <p class="mt-1 whitespace-pre-line text-sm text-amber-900 dark:text-amber-100">{collab.content || t("inits_modify.no_feedback", "The reviewer left no message.")}</p>
      </section>

      {#if blocked}
        <div class="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-500/40 dark:bg-amber-500/10 dark:text-amber-200">
          {t("inits_modify.blocked", "This change request is no longer pending.")}
          <a href="/inits/my_initiative_requests" class="ml-1 font-medium underline">{t("inits_diagnose.to_requests", "Go to My Initiative Requests")}</a>
        </div>
      {:else}
        <section class="space-y-4">
          <div>
            <label for="im-name" class={label}>{t("inits_propose.name", "Name")} <span class="text-red-500">*</span></label>
            <input id="im-name" type="text" maxlength="100" class={input("name")} bind:value={form.name} oninput={() => clear("name")} />
          </div>
          <div>
            <label for="im-description" class={label}>{t("inits_propose.description", "Description")}</label>
            <textarea id="im-description" rows="2" maxlength="500" class={input("description")} bind:value={form.description}></textarea>
          </div>
          <div class="grid gap-4 sm:grid-cols-3">
            <div>
              <label for="im-type" class={label}>{t("inits_propose.type", "Type")}</label>
              <select id="im-type" class={input("type")} bind:value={form.type}>
                <option value="">{t("inits_propose.choose", "— choose —")}</option>
                {#each lists.type as o (o.value)}<option value={o.value}>{o.label}</option>{/each}
              </select>
            </div>
            <div>
              <label for="im-impact" class={label}>{t("inits_propose.expected_impact", "Expected impact")} <span class="text-red-500">*</span></label>
              <select id="im-impact" class={input("expected_impact")} bind:value={form.expected_impact} onchange={() => clear("expected_impact")}>
                <option value="">{t("inits_propose.choose", "— choose —")}</option>
                {#each lists.impact as o (o.value)}<option value={o.value}>{o.label}</option>{/each}
              </select>
            </div>
            <div>
              <label for="im-priority" class={label}>{t("inits_propose.priority_level", "Priority")} <span class="text-red-500">*</span></label>
              <select id="im-priority" class={input("priority_level")} bind:value={form.priority_level} onchange={() => clear("priority_level")}>
                <option value="">{t("inits_propose.choose", "— choose —")}</option>
                {#each lists.priority as o (o.value)}<option value={o.value}>{o.label}</option>{/each}
              </select>
            </div>
          </div>
          <div>
            <label for="im-reference" class={label}>{t("inits_propose.reference", "Reference")}</label>
            <input id="im-reference" type="text" class={input("reference")} bind:value={form.reference} />
          </div>
          <div>
            <label for="im-tags" class={label}>{t("inits_propose.tags", "Tags")}</label>
            <input id="im-tags" type="text" class={input("tags")} bind:value={form.tags} placeholder={t("inits_propose.tags_placeholder", "Comma-separated, e.g. legal, contracts")} />
          </div>
          <div>
            <label for="im-detail" class={label}>{t("inits_propose.detail", "Detail")}</label>
            <textarea id="im-detail" rows="4" class={input("detail")} bind:value={form.detail}></textarea>
          </div>
        </section>

        <DiagnosisTable bind:this={table} items={rows} mode="modify" {scales} />
      {/if}
    {/if}
  </div>

  {#if !loading && !notFound && !blocked}
    <div class="flex flex-col gap-3 border-t border-gray-200 px-6 py-4 sm:flex-row sm:justify-end dark:border-gray-800">
      <button type="button" onclick={() => history.back()} class="inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-semibold text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800">{t("inits_modify.back", "Back")}</button>
      <button type="button" disabled={submitting} onclick={resubmit} class="inline-flex items-center justify-center rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60">{t("inits_modify.resubmit", "Resubmit for diagnosis")}</button>
    </div>
  {/if}
</article>
