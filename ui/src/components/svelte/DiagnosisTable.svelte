<script lang="ts">
  /**
   * DiagnosisTable — one row per diagnosis criterion, the proposer's answer
   * beside the reviewer's, with an overall score card per party.
   *
   * Extracted from InitiativeDetailTabs.svelte (specs/004) so every initiative
   * surface renders the diagnosis the same way (specs/005 research R12):
   *
   *   mode        proposer column              reviewer column
   *   ─────────   ──────────────────────────   ───────────────────────────
   *   view        read                         read
   *   propose     editable (select+rationale)  hidden
   *   review      read (with rationale)        editable (select)
   *   modify      editable, prefilled          read ("Previous review")
   *
   * Editable modes need `scales` (list code → options). `validate()` returns
   * the criteria still unanswered in the editable column and marks them.
   */
  import { untrack } from "svelte";
  import { translate } from "@/utils/i18nClient";
  import type { DiagnosisAnswer, DiagnosticRow } from "@/types/api";

  type Mode = "view" | "propose" | "review" | "modify";
  type ScaleOption = { value: number; label: string };

  let {
    items = [],
    mode = "view",
    scales = {},
    onChange,
  }: {
    items?: DiagnosticRow[];
    mode?: Mode;
    scales?: Record<string, ScaleOption[]>;
    onChange?: (answers: { creator: Record<string, DiagnosisAnswer>; reviewer: Record<string, number> }) => void;
  } = $props();

  // ── i18n ──────────────────────────────────────────────────────────────
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
  $effect(() => {
    const bump = () => (langTick += 1);
    window.addEventListener("languageChanged", bump);
    document.addEventListener("synapxia:locale-changed", bump);
    return () => {
      window.removeEventListener("languageChanged", bump);
      document.removeEventListener("synapxia:locale-changed", bump);
    };
  });

  // ── Editable state, re-seeded whenever `items` changes ────────────────
  let creator = $state<Record<string, { score: number | null; rationale: string }>>({});
  let reviewer = $state<Record<string, number | null>>({});
  let rationaleOpen = $state<Record<string, boolean>>({});
  let invalid = $state<Set<string>>(new Set());

  $effect(() => {
    const rows = items;
    untrack(() => {
      const c: typeof creator = {};
      const r: typeof reviewer = {};
      for (const row of rows) {
        c[row.criteria] = { score: row.creator_score ?? null, rationale: row.rationale ?? "" };
        r[row.criteria] = mode === "review" ? null : row.reviewer_score ?? null;
      }
      creator = c;
      reviewer = r;
      rationaleOpen = {};
      invalid = new Set();
    });
  });

  const editsCreator = $derived(mode === "propose" || mode === "modify");
  const editsReviewer = $derived(mode === "review");
  const showReviewer = $derived(mode !== "propose");

  function emit(): void {
    if (!onChange) return;
    const c: Record<string, DiagnosisAnswer> = {};
    for (const [code, a] of Object.entries(creator)) {
      if (a.score != null) c[code] = { score: a.score, rationale: a.rationale.trim() || null };
    }
    const r: Record<string, number> = {};
    for (const [code, v] of Object.entries(reviewer)) if (v != null) r[code] = v;
    onChange({ creator: c, reviewer: r });
  }

  function setCreatorScore(code: string, raw: string): void {
    creator = { ...creator, [code]: { ...creator[code], score: raw === "" ? null : Number(raw) } };
    if (raw !== "") invalid = new Set([...invalid].filter((c) => c !== code));
    emit();
  }
  function setCreatorRationale(code: string, text: string): void {
    creator = { ...creator, [code]: { ...creator[code], rationale: text } };
    emit();
  }
  function setReviewerScore(code: string, raw: string): void {
    reviewer = { ...reviewer, [code]: raw === "" ? null : Number(raw) };
    if (raw !== "") invalid = new Set([...invalid].filter((c) => c !== code));
    emit();
  }

  /** Codes of active criteria still unanswered in the editable column (and
   *  marks them). Always `[]` in view mode. */
  export function validate(): string[] {
    if (!editsCreator && !editsReviewer) return [];
    const missing = items
      .filter((row) => row.is_active_criteria)
      .filter((row) => (editsCreator ? creator[row.criteria]?.score : reviewer[row.criteria]) == null)
      .map((row) => row.criteria);
    invalid = new Set(missing);
    return missing;
  }
  export function getCreatorAnswers(): Record<string, DiagnosisAnswer> {
    const out: Record<string, DiagnosisAnswer> = {};
    for (const row of items) {
      const a = creator[row.criteria];
      if (row.is_active_criteria && a?.score != null) {
        out[row.criteria] = { score: a.score, rationale: a.rationale.trim() || null };
      }
    }
    return out;
  }
  export function getReviewerAnswers(): Record<string, number> {
    const out: Record<string, number> = {};
    for (const row of items) {
      const v = reviewer[row.criteria];
      if (row.is_active_criteria && v != null) out[row.criteria] = v;
    }
    return out;
  }

  // ── Derived display ───────────────────────────────────────────────────
  const scaleFor = (row: DiagnosticRow): ScaleOption[] => scales[row.list || row.criteria] ?? [];
  const labelFor = (row: DiagnosticRow, score: number | null | undefined): string | null => {
    if (score == null) return null;
    return scaleFor(row).find((o) => o.value === score)?.label ?? null;
  };
  const creatorScore = (row: DiagnosticRow) => (editsCreator ? creator[row.criteria]?.score ?? null : row.creator_score ?? null);
  const creatorLabel = (row: DiagnosticRow) =>
    editsCreator ? labelFor(row, creator[row.criteria]?.score) : row.creator_label ?? null;
  const reviewerScore = (row: DiagnosticRow) => (editsReviewer ? reviewer[row.criteria] ?? null : row.reviewer_score ?? null);
  const reviewerLabel = (row: DiagnosticRow) =>
    editsReviewer ? labelFor(row, reviewer[row.criteria]) : row.reviewer_label ?? null;
  const rationaleOf = (row: DiagnosticRow) => (editsCreator ? creator[row.criteria]?.rationale ?? "" : row.rationale ?? "");

  const totals = $derived.by(() => {
    let cSum = 0, cN = 0, rSum = 0, rN = 0;
    for (const row of items) {
      const c = creatorScore(row);
      if (c != null) { cSum += c; cN += 1; }
      const r = reviewerScore(row);
      if (r != null) { rSum += r; rN += 1; }
    }
    return { creator: cN ? cSum : null, creatorN: cN, reviewer: rN ? rSum : null, reviewerN: rN };
  });

  const answeredLabel = (n: number): string =>
    t("initiative_detail_modal.diag_answered", "{n} of {m} answered")
      .replace("{n}", String(n))
      .replace("{m}", String(items.length));

  const answerClass = "text-sm text-gray-800 dark:text-gray-200";
  const mutedClass = "text-sm italic text-gray-400 dark:text-gray-500";
  const selectBase =
    "w-full rounded-lg border px-2 py-1.5 text-sm focus:outline-none focus:ring-2 dark:bg-gray-800 dark:text-white";
  const selectClass = (code: string) =>
    `${selectBase} ${invalid.has(code)
      ? "border-red-500 focus:ring-red-200 dark:border-red-500"
      : "border-gray-300 focus:border-indigo-500 focus:ring-indigo-200 dark:border-gray-700"}`;
  const reviewerHeader = $derived(
    mode === "modify"
      ? t("inits_diagnosis.previous_review", "Previous review")
      : t("initiative_detail_modal.diag_reviewer", "Reviewer's answer"),
  );
</script>

{#snippet answerCell(score: number | null | undefined, label: string | null | undefined, missing: string, tone: "indigo" | "emerald")}
  {#if label}
    <div class="flex items-start gap-2">
      <span class={`inline-flex h-6 min-w-6 shrink-0 items-center justify-center rounded-full px-1.5 text-xs font-bold text-white ${tone === "indigo" ? "bg-indigo-600" : "bg-emerald-600"}`}>{score}</span>
      <span class={answerClass}>{label}</span>
    </div>
  {:else}
    <span class={mutedClass}>{missing}</span>
  {/if}
{/snippet}
<!-- Same Show / Hide switch as the characteristic details in Edit Asset:
     icon + label + track, right-aligned, collapsed by default. -->
{#snippet rationaleToggle(key: string)}
  <button
    type="button"
    class="flex shrink-0 items-center gap-1.5 text-[11px] font-medium text-gray-500 hover:text-indigo-600 dark:text-gray-400 dark:hover:text-indigo-400"
    aria-pressed={rationaleOpen[key] ? "true" : "false"}
    onclick={() => (rationaleOpen = { ...rationaleOpen, [key]: !rationaleOpen[key] })}
  >
    {#if rationaleOpen[key]}
      <svg viewBox="0 0 20 20" fill="currentColor" class="h-3.5 w-3.5" aria-hidden="true">
        <path d="M2.53 2.47a.75.75 0 00-1.06 1.06l3.02 3.02C2.6 8.03 1.2 9.6.5 10.5c1.99 3 5.5 6.5 9.5 6.5 1.5 0 2.9-.35 4.15-.95l2.32 2.32a.75.75 0 101.06-1.06L2.53 2.47zM10 14.5a4.47 4.47 0 01-3.02-1.18l1.14-1.14A2.98 2.98 0 0010 13a3 3 0 003-3c0-.4-.08-.78-.22-1.12l1.14-1.14A4.47 4.47 0 0113.5 10 4.5 4.5 0 0110 14.5zM10 3.5c1.5 0 2.9.35 4.15.95l-1.24 1.24A6.98 6.98 0 0010 5.5a7 7 0 00-6.16 3.65L2.6 7.9C4.1 5.5 6.9 3.5 10 3.5z"></path>
      </svg>
    {:else}
      <svg viewBox="0 0 20 20" fill="currentColor" class="h-3.5 w-3.5" aria-hidden="true">
        <path d="M10 3.5c-4.5 0-8 3.5-9.5 6.5C1.99 13 5.5 16.5 10 16.5s8.01-3.5 9.5-6.5C18 7 14.5 3.5 10 3.5zm0 11a4.5 4.5 0 110-9 4.5 4.5 0 010 9z"></path>
        <circle cx="10" cy="10" r="2"></circle>
      </svg>
    {/if}
    <span>{rationaleOpen[key] ? t("initiative_detail_modal.diag_hide_rationale", "Hide rationale") : t("initiative_detail_modal.diag_show_rationale", "Show rationale")}</span>
    <span class={`relative inline-block h-4 w-7 shrink-0 rounded-full transition ${rationaleOpen[key] ? "bg-indigo-600" : "bg-gray-300 dark:bg-gray-600"}`}>
      <span class={`absolute top-0.5 left-0.5 h-3 w-3 rounded-full bg-white shadow transition ${rationaleOpen[key] ? "translate-x-3" : ""}`}></span>
    </span>
  </button>
{/snippet}
{#snippet scaleSelect(row: DiagnosticRow, value: number | null, onpick: (raw: string) => void)}
  <select
    class={selectClass(row.criteria)}
    aria-invalid={invalid.has(row.criteria) ? "true" : "false"}
    aria-label={row.name}
    value={value == null ? "" : String(value)}
    onchange={(e) => onpick((e.currentTarget as HTMLSelectElement).value)}
  >
    <option value="">{t("inits_diagnosis.choose", "— choose an answer —")}</option>
    {#each scaleFor(row) as opt (opt.value)}
      <option value={String(opt.value)}>{opt.value} · {opt.label}</option>
    {/each}
  </select>
  {#if invalid.has(row.criteria)}
    <p class="mt-1 text-xs text-red-600 dark:text-red-400">{t("inits_diagnosis.unanswered", "Answer this question.")}</p>
  {/if}
{/snippet}

<div class="space-y-4">
  <!-- Overall score, one card per party (same tints as their table columns). -->
  <div class={`grid grid-cols-1 gap-3 ${showReviewer ? "sm:grid-cols-2" : ""}`}>
    <div class="rounded-lg border border-indigo-200 bg-indigo-50 px-4 py-3 dark:border-indigo-500/30 dark:bg-indigo-500/10">
      <p class="text-xs font-semibold uppercase tracking-wide text-indigo-700 dark:text-indigo-300">{t("initiative_detail_modal.diag_score_creator", "Proposer's overall score")}</p>
      <p class="mt-1 text-2xl font-bold text-indigo-700 dark:text-indigo-200">{totals.creator ?? "—"}</p>
      <p class="text-xs text-indigo-600/80 dark:text-indigo-300/80">{answeredLabel(totals.creatorN)}</p>
    </div>
    {#if showReviewer}
      <div class="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 dark:border-emerald-500/30 dark:bg-emerald-500/10">
        <p class="text-xs font-semibold uppercase tracking-wide text-emerald-700 dark:text-emerald-300">{t("initiative_detail_modal.diag_score_reviewer", "Reviewer's overall score")}</p>
        <p class="mt-1 text-2xl font-bold text-emerald-700 dark:text-emerald-200">{totals.reviewer ?? "—"}</p>
        <p class="text-xs text-emerald-700/80 dark:text-emerald-300/80">
          {totals.reviewer == null ? t("initiative_detail_modal.diag_pending", "Pending diagnosis") : answeredLabel(totals.reviewerN)}
        </p>
      </div>
    {/if}
  </div>

  <div class="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-800">
    <table class={`w-full text-left text-sm ${showReviewer ? "min-w-[640px]" : ""}`}>
      <thead>
        <tr class="border-b border-gray-200 text-xs font-semibold uppercase tracking-wide dark:border-gray-800">
          <th class="px-3 py-2 text-gray-500 dark:text-gray-400">{t("initiative_detail_modal.diag_criterion", "Criterion")}</th>
          <th class={`${showReviewer ? "w-[30%]" : "w-[45%]"} bg-indigo-50 px-3 py-2 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-300`}>{t("initiative_detail_modal.diag_creator", "Proposer's answer")}</th>
          {#if showReviewer}
            <th class="w-[30%] bg-emerald-50 px-3 py-2 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300">{reviewerHeader}</th>
          {/if}
        </tr>
      </thead>
      <tbody>
        {#each items as row (row.criteria)}
          <tr class="border-b border-gray-100 align-top last:border-0 dark:border-gray-800/60">
            <td class="px-3 py-3">
              <div class="flex flex-wrap items-baseline gap-2">
                <span class="font-semibold text-gray-800 dark:text-gray-200">{row.name}</span>
                {#if !row.is_active_criteria}
                  <span class="rounded-full bg-gray-200 px-2 py-0.5 text-[10px] font-semibold uppercase text-gray-600 dark:bg-gray-700 dark:text-gray-300">{t("initiative_detail_modal.diag_inactive", "Retired criterion")}</span>
                {/if}
              </div>
              {#if row.description}
                <p class="mt-0.5 text-xs text-gray-500 dark:text-gray-400">{row.description}</p>
              {/if}
              {#if editsCreator || rationaleOf(row)}
                <div class="mt-2 flex justify-end">
                  {@render rationaleToggle(row.criteria)}
                </div>
              {/if}
            </td>
            <td class="bg-indigo-50/40 px-3 py-3 dark:bg-indigo-500/5">
              {#if editsCreator && row.is_active_criteria}
                {@render scaleSelect(row, creator[row.criteria]?.score ?? null, (raw) => setCreatorScore(row.criteria, raw))}
              {:else}
                {@render answerCell(creatorScore(row), creatorLabel(row), t("initiative_detail_modal.diag_not_answered", "Not answered"), "indigo")}
              {/if}
            </td>
            {#if showReviewer}
              <td class="bg-emerald-50/40 px-3 py-3 dark:bg-emerald-500/5">
                {#if editsReviewer && row.is_active_criteria}
                  {@render scaleSelect(row, reviewer[row.criteria] ?? null, (raw) => setReviewerScore(row.criteria, raw))}
                {:else}
                  {@render answerCell(
                    reviewerScore(row),
                    reviewerLabel(row),
                    creatorLabel(row) ? t("initiative_detail_modal.diag_pending", "Pending diagnosis") : t("initiative_detail_modal.diag_not_answered", "Not answered"),
                    "emerald",
                  )}
                {/if}
              </td>
            {/if}
          </tr>
          {#if rationaleOpen[row.criteria] && (editsCreator || rationaleOf(row))}
            <tr class="border-b border-gray-100 last:border-0 dark:border-gray-800/60">
              <td colspan={showReviewer ? 3 : 2} class="bg-gray-50 px-3 py-2 dark:bg-white/[0.02]">
                <p class="text-[11px] font-semibold uppercase tracking-wide text-gray-400">{t("initiative_detail_modal.diag_rationale", "Rationale")}</p>
                {#if editsCreator}
                  <textarea
                    rows="2"
                    maxlength="2000"
                    class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                    placeholder={t("inits_diagnosis.rationale_placeholder", "Why this answer? (optional)")}
                    value={creator[row.criteria]?.rationale ?? ""}
                    oninput={(e) => setCreatorRationale(row.criteria, (e.currentTarget as HTMLTextAreaElement).value)}
                  ></textarea>
                {:else}
                  <p class="text-sm text-gray-700 dark:text-gray-300">{rationaleOf(row)}</p>
                {/if}
              </td>
            </tr>
          {/if}
        {/each}
      </tbody>
    </table>
  </div>
</div>
