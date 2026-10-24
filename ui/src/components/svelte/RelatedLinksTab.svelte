<script module lang="ts">
  export type LinkOption = { value: string; label: string };
  export type LinkRow = {
    target: string;
    targetLabel: string;
    type: string;
    rationale: string;
    inactive?: boolean;
    incoming?: boolean;
  };
</script>

<script lang="ts">
  /**
   * RelatedLinksTab — one "Related …" tab: a list of typed links plus an add
   * row (target, relation type, rationale). Markup, classes and messages are
   * taken from AssetDetailTabs' Related Assets panel, so every Related tab in
   * the app looks and behaves the same (specs/009-process-management, R10).
   *
   * The tab only STAGES changes. The parent reads `staged()` and saves the
   * whole set in one call; `hydrate()` reseeds the dirty baseline afterwards.
   *
   * Values are strings (a process code or a numeric id as text); links are
   * keyed by `target:type`, so the same pair may be linked once per type.
   * `filterTarget(type, option)` narrows the target picker for a chosen type
   * (Process Management's SUPPORTS / PRECEDES rules); a picked target that the
   * chosen type does not allow blocks Add with `incompatibleMessage(type)`.
   */
  import { onMount } from "svelte";
  import { translate } from "@/utils/i18nClient";

  type Kind = "process" | "asset" | "init";

  let {
    idPrefix,
    kind,
    targetOptions = [],
    typeOptions = [],
    filterTarget,
    incompatibleMessage,
    readonly = false,
    highlight = true,
  }: {
    idPrefix: string;
    kind: Kind;
    targetOptions?: LinkOption[];
    typeOptions?: LinkOption[];
    filterTarget?: (type: string, option: LinkOption) => boolean;
    incompatibleMessage?: (type: string) => string;
    readonly?: boolean;
    /** Ring the pending rows (edit mode); off while creating, where every row is new. */
    highlight?: boolean;
  } = $props();

  // ── i18n ──────────────────────────────────────────────────────────────
  let langTick = $state(0);
  const t = (key: string, fallback: string): string => {
    void langTick;
    try {
      const v = translate(`related_links.${key}`);
      if (v && v !== `related_links.${key}`) return v;
    } catch {
      /* non-fatal */
    }
    return fallback;
  };
  const TEXT: Record<Kind, Record<string, [string, string]>> = {
    process: {
      target: ["target_process", "Process"],
      choose: ["choose_process", "— choose process —"],
      empty: ["empty_process", "No related processes yet."],
      duplicate: ["duplicate_process", "This process is already related with that relation type."],
      missing: ["missing_process", "Pick a process and a relation type."],
      add: ["add_process", "Add process"],
      placeholder: ["rationale_placeholder_process", "Why are these processes related? (optional)"],
    },
    asset: {
      target: ["target_asset", "Asset"],
      choose: ["choose_asset", "— choose asset —"],
      empty: ["empty_asset", "No related assets yet."],
      duplicate: ["duplicate_asset", "This asset is already related with that relation type."],
      missing: ["missing_asset", "Pick an asset and a relation type."],
      add: ["add_asset", "Add asset"],
      placeholder: ["rationale_placeholder_asset", "Why is this asset related? (optional)"],
    },
    init: {
      target: ["target_init", "Initiative"],
      choose: ["choose_init", "— choose initiative —"],
      empty: ["empty_init", "No related initiatives yet."],
      duplicate: ["duplicate_init", "This initiative is already related with that relation type."],
      missing: ["missing_init", "Pick an initiative and a relation type."],
      add: ["add_init", "Add initiative"],
      placeholder: ["rationale_placeholder_init", "Why is this initiative related? (optional)"],
    },
  };
  const tx = (name: string): string => t(TEXT[kind][name][0], TEXT[kind][name][1]);

  // ── State ─────────────────────────────────────────────────────────────
  const linkKey = (target: string, type: string): string => `${target}:${type}`;
  let rows = $state<LinkRow[]>([]);
  // Baseline of the last hydrate: key → rationale.
  let initial = $state(new Map<string, string>());
  let target = $state("");
  let type = $state("");
  let rationale = $state("");
  let error = $state("");

  const typeLabel = (value: string): string =>
    typeOptions.find((o) => o.value === value)?.label || value;

  const visibleTargets = $derived(
    type && filterTarget ? targetOptions.filter((o) => filterTarget(type, o)) : targetOptions,
  );
  const incompatible = $derived(
    !!(target && type && filterTarget) &&
      !targetOptions.some((o) => o.value === target && filterTarget!(type, o)),
  );
  // A target that leaves the list because of the chosen type stays selected,
  // so the user sees why Add is blocked instead of a silent reset.
  const targetChoices = $derived(
    incompatible ? [...visibleTargets, ...targetOptions.filter((o) => o.value === target)] : visibleTargets,
  );

  const incompatibleText = (): string =>
    incompatibleMessage?.(type) ?? t("incompatible", "This relation type is not allowed for that process.");
  // A type change that invalidates the picked target is explained at once.
  const shownError = $derived(incompatible ? incompatibleText() : error);

  const pendingKeys = $derived.by(() => {
    const set = new Set<string>();
    for (const r of rows) {
      const key = linkKey(r.target, r.type);
      if (!initial.has(key) || initial.get(key) !== r.rationale) set.add(key);
    }
    return set;
  });

  // ── Controller API ────────────────────────────────────────────────────
  export function hydrate(next: LinkRow[]): void {
    rows = next.map((r) => ({ ...r, rationale: r.rationale ?? "" }));
    initial = new Map(rows.map((r) => [linkKey(r.target, r.type), r.rationale]));
    clearForm();
  }

  export function staged(): { target: string; type: string; rationale: string | null }[] {
    return rows.map((r) => ({ target: r.target, type: r.type, rationale: r.rationale || null }));
  }

  export function dirty(): boolean {
    if (rows.length !== initial.size) return true;
    return pendingKeys.size > 0;
  }

  export function count(): number {
    return rows.length;
  }

  export function reset(): void {
    rows = [];
    initial = new Map();
    clearForm();
  }

  function clearForm(): void {
    target = "";
    type = "";
    rationale = "";
    error = "";
  }

  function add(): void {
    error = "";
    if (!target || !type) {
      error = tx("missing");
      return;
    }
    if (incompatible) {
      error = incompatibleText();
      return;
    }
    if (rows.some((r) => r.target === target && r.type === type)) {
      error = tx("duplicate");
      return;
    }
    rows = [
      ...rows,
      {
        target,
        targetLabel: targetOptions.find((o) => o.value === target)?.label || target,
        type,
        rationale: rationale.trim(),
      },
    ];
    clearForm();
  }

  function remove(idx: number): void {
    rows = rows.filter((_, i) => i !== idx);
  }

  onMount(() => {
    const onLang = () => {
      langTick += 1;
    };
    window.addEventListener("languageChanged", onLang);
    document.addEventListener("synapxia:locale-changed", onLang);
    return () => {
      window.removeEventListener("languageChanged", onLang);
      document.removeEventListener("synapxia:locale-changed", onLang);
    };
  });

  const fieldClass =
    "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 dark:border-gray-700 dark:bg-gray-800 dark:text-white";
  const labelClass = "block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1";
  const addBtnClass =
    "shrink-0 rounded-lg border border-indigo-600 px-4 py-2 text-sm font-semibold text-indigo-600 hover:bg-indigo-50 dark:text-indigo-400 dark:hover:bg-indigo-900/30";
  const rowClass =
    "flex items-center gap-3 rounded-lg border border-gray-200 dark:border-gray-800 bg-gray-50/50 dark:bg-white/[0.02] px-3 py-2";
  const emptyClass =
    "rounded-lg border border-dashed border-gray-300 dark:border-gray-700 p-6 text-center text-sm text-gray-500 dark:text-gray-400";
  const badgeClass =
    "shrink-0 rounded-full bg-gray-100 px-2 py-0.5 text-[11px] font-semibold text-gray-600 dark:bg-gray-700 dark:text-gray-300";
</script>

<div class="space-y-4">
  {#if !readonly}
    <section>
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div>
          <label for={`${idPrefix}-${kind}-link-target`} class={labelClass}>{tx("target")}</label>
          <select id={`${idPrefix}-${kind}-link-target`} bind:value={target} class={fieldClass}>
            <option value="">{tx("choose")}</option>
            {#each targetChoices as o (o.value)}
              <option value={o.value}>{o.label}</option>
            {/each}
          </select>
        </div>
        <div>
          <label for={`${idPrefix}-${kind}-link-type`} class={labelClass}>{t("type", "Relation type")}</label>
          <select id={`${idPrefix}-${kind}-link-type`} bind:value={type} class={fieldClass}>
            <option value="">{t("choose_type", "— choose type —")}</option>
            {#each typeOptions as o (o.value)}
              <option value={o.value}>{o.label}</option>
            {/each}
          </select>
        </div>
        <div class="md:col-span-2">
          <label for={`${idPrefix}-${kind}-link-rationale`} class={labelClass}>{t("rationale", "Rationale")}</label>
          <div class="flex gap-2">
            <input id={`${idPrefix}-${kind}-link-rationale`} type="text" bind:value={rationale} placeholder={tx("placeholder")} class="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 dark:border-gray-700 dark:bg-gray-800 dark:text-white" />
            <button type="button" class={addBtnClass} onclick={add}>{tx("add")}</button>
          </div>
        </div>
      </div>
      {#if shownError}
        <p class="mt-2 text-xs text-red-600 dark:text-red-400" role="alert">{shownError}</p>
      {/if}
    </section>
  {/if}
  <section>
    {#if rows.length === 0}
      <div class={emptyClass}>{tx("empty")}</div>
    {:else}
      <ul class="space-y-2">
        {#each rows as row, idx (linkKey(row.target, row.type))}
          <li
            class={highlight && pendingKeys.has(linkKey(row.target, row.type)) ? `${rowClass} ring-1 ring-amber-400` : rowClass}
            data-pending={pendingKeys.has(linkKey(row.target, row.type)) ? "1" : undefined}
          >
            <span class="min-w-0 flex-1 truncate text-sm font-semibold text-gray-800 dark:text-gray-200" title={row.targetLabel}>{row.targetLabel}</span>
            {#if row.incoming}
              <span class={badgeClass} title={t("incoming_hint", "Recorded from the other process; it applies both ways.")}>{t("incoming", "Both ways")}</span>
            {/if}
            {#if row.inactive}
              <span class={badgeClass}>{t("inactive", "Removed")}</span>
            {/if}
            <span class="shrink-0 rounded-full bg-indigo-50 px-2 py-0.5 text-[11px] font-semibold text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300">{typeLabel(row.type)}</span>
            {#if row.rationale}
              <span class="hidden md:block max-w-[200px] truncate text-xs text-gray-500 dark:text-gray-400" title={row.rationale}>{row.rationale}</span>
            {/if}
            {#if !readonly}
              <button type="button" class="shrink-0 rounded-md p-1 text-gray-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/30" title={t("remove", "Remove")} onclick={() => remove(idx)} aria-label={t("remove", "Remove")}>
                <svg class="w-4 h-4" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" /></svg>
              </button>
            {/if}
          </li>
        {/each}
      </ul>
    {/if}
  </section>
</div>
