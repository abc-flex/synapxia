<script lang="ts">
  /**
   * DashboardDetailTabs — the three tabs of Dashboard Management's edit dialog
   * (specs/006-dashboard-management): Core Fields, Parameters, Permissions.
   *
   * Mounted manually by DashboardDetailModal.astro, which drives it through
   * the exported controller methods (Svelte 5 `mount()` returns them).
   *
   * - Core Fields is an empty shell the parent re-parents its own <section> into.
   * - Parameters and Permissions stage edits and persist ONLY when the parent
   *   calls `flushParameters()` / `flushPermissions()` (tab-scoped save).
   * - While a dashboard is being created (no id yet) only Core Fields is usable.
   *
   * A parameter's value source is one of: bound to a grant (value fixed to the
   * grant's recipient), from a list (the viewer picks a value), or entered by
   * the viewer. The run-time parameters window belongs to HU-AN05 Execute.
   */
  import { onMount } from "svelte";
  import { getListItemsbyList } from "@/lib/list_items";
  import { labelsByValue, listLabel, toListOptions } from "@/lib/listLang";
  import { getParameterLists } from "@/lib/dashboards";
  import {
    createParameter, deleteParameter, getParameters, updateParameter,
  } from "@/lib/dashboard_parameters";
  import {
    createDashboardPermission, getDashboardPermissions, revokeDashboardPermission,
  } from "@/lib/dashboard_permissions";
  import {
    PUBLIC_TARGET, resolveTargetLabel, type PermissionsApi, type SelectOption,
  } from "@/lib/permissionTargets";
  import { translate } from "@/utils/i18nClient";
  import PermissionsTab from "@/components/svelte/PermissionsTab.svelte";
  import type { DashboardParameter, ParameterValueSource } from "@/types/api";

  type TabName = "core" | "parameters" | "permissions";
  type StagedParam = {
    name: string;
    label: string;
    data_type: string;
    is_required: boolean;
    default_value: string | null;
    list: string | null;
    context_binding: number | null;
    bindingLabel: string | null;
  };

  let {
    idPrefix,
    onError,
    onTabChange,
  }: {
    idPrefix: string;
    onError?: (msg: string) => void;
    onTabChange?: (name: TabName) => void;
  } = $props();

  const reportError = (m: string) => (onError ? onError(m) : console.error(m));
  const P = "dashboard_detail_modal";

  const dashboardPermissionsApi: PermissionsApi = {
    list: (id) => getDashboardPermissions(id),
    create: (id, body) => createDashboardPermission({ dashboard: id, ...body }),
    revoke: (grantId) => revokeDashboardPermission(grantId),
  };

  // ── i18n ──────────────────────────────────────────────────────────────
  let langTick = $state(0);
  const t = (key: string, fallback: string): string => {
    void langTick;
    try {
      const v = translate(`${P}.${key}`);
      if (v && v !== `${P}.${key}`) return v;
    } catch {
      /* non-fatal */
    }
    return fallback;
  };
  const currentLang = (): string =>
    (typeof localStorage !== "undefined" && localStorage.getItem("lang")) === "es" ? "es" : "en";
  // list code → every language's items (PARAM_TYPE, TARGET_TYPE, and each
  // allowed-values list a parameter uses).
  let listRaw = $state<Record<string, any[]>>({});
  const listOpts = (code: string | null | undefined): SelectOption[] => {
    void langTick;
    return code ? toListOptions(listRaw[code] ?? [], currentLang()) : [];
  };
  const listText = (code: string, value: string | null | undefined): string => {
    void langTick;
    return value ? listLabel(labelsByValue(listRaw[code] ?? []), value, currentLang()) : "";
  };

  async function ensureList(code: string | null | undefined): Promise<void> {
    if (!code || listRaw[code]) return;
    let items: any[] = [];
    try {
      items = await getListItemsbyList(code);
    } catch {
      items = [];
    }
    listRaw = { ...listRaw, [code]: items };
  }

  // ── State ─────────────────────────────────────────────────────────────
  let rootEl = $state<HTMLElement | undefined>(undefined);
  let activeTab = $state<TabName>("core");
  let dashId = $state<number | null>(null);
  let readonly = $state(false);
  let coreDirty = $state(false);
  let permTab = $state<any>(undefined);

  // Parameters
  let staged = $state<StagedParam[]>([]);
  let initialByName = $state(new Map<string, string>());
  let paramLists = $state<SelectOption[]>([]);
  // Live non-PUBLIC grants the parameter may be bound to.
  let grantOptions = $state<SelectOption[]>([]);
  let paramsLoading = $state(false);

  // Parameter form
  let editingName = $state<string | null>(null);
  let fName = $state("");
  let fLabel = $state("");
  let fType = $state("");
  let fRequired = $state(false);
  let fSource = $state<ParameterValueSource>("INPUT");
  let fList = $state("");
  let fBinding = $state("");
  let fDefault = $state("");
  let fError = $state("");

  const typeOptions = $derived(listOpts("PARAM_TYPE"));
  // The list whose values the default (and the viewer) pick from: the chosen
  // list for LIST, the optional fallback list for GRANT, none for INPUT.
  const effectiveList = $derived(fSource === "INPUT" ? "" : fList);
  const defaultValueOptions = $derived(listOpts(effectiveList));

  $effect(() => {
    onTabChange?.(activeTab);
  });
  $effect(() => {
    if (effectiveList) void ensureList(effectiveList);
  });

  const snapshot = (p: StagedParam): string =>
    JSON.stringify([p.label, p.data_type, p.is_required, p.default_value, p.list, p.context_binding]);
  const sourceOf = (p: { list: string | null; context_binding: number | null }): ParameterValueSource =>
    p.context_binding != null ? "GRANT" : p.list ? "LIST" : "INPUT";

  // ── Controller API ────────────────────────────────────────────────────
  export function setCoreDirty(dirty: boolean): void {
    coreDirty = dirty;
  }

  export function activateTab(name: TabName): void {
    if (dashId == null && name !== "core") return;
    activeTab = name;
  }

  export function parametersDirty(): boolean {
    const names = new Set(staged.map((p) => p.name));
    for (const [name] of initialByName) if (!names.has(name)) return true;
    return staged.some((p) => initialByName.get(p.name) !== snapshot(p));
  }

  export function permissionsDirty(): boolean {
    return permTab?.dirty() ?? false;
  }

  const pendingNames = $derived.by(() => {
    const set = new Set<string>();
    for (const p of staged) if (initialByName.get(p.name) !== snapshot(p)) set.add(p.name);
    return set;
  });
  const tabDirty = $derived<Partial<Record<TabName, boolean>>>({
    core: coreDirty,
    parameters: parametersDirty(),
    permissions: permissionsDirty(),
  });

  export function focusFirstPending(): void {
    rootEl
      ?.querySelector<HTMLElement>(`[data-tabpanel="${activeTab}"] [data-pending="1"]`)
      ?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  // ── Tabs ──────────────────────────────────────────────────────────────
  const tabOrder: TabName[] = ["core", "parameters", "permissions"];
  const tabLabel = (name: TabName): string => {
    const keys: Record<TabName, [string, string]> = {
      core: ["tab_core", "Core Fields"],
      parameters: ["tab_parameters", "Parameters"],
      permissions: ["tab_permissions", "Permissions"],
    };
    return t(keys[name][0], keys[name][1]);
  };
  const tabCount = (name: TabName): number | null =>
    name === "parameters" ? staged.length : name === "permissions" ? (permTab?.count() ?? 0) : null;
  const tabDisabled = (name: TabName): boolean => dashId == null && name !== "core";
  const tabClass = (name: TabName): string =>
    "whitespace-nowrap border-b-2 px-1 pb-3 " +
    (tabDisabled(name)
      ? "border-transparent text-gray-300 cursor-not-allowed dark:text-gray-600"
      : activeTab === name
        ? "border-indigo-600 text-indigo-600 dark:text-indigo-400"
        : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200");

  function onTabKeydown(e: KeyboardEvent): void {
    const order = tabOrder.filter((n) => !tabDisabled(n));
    const idx = order.indexOf(activeTab);
    let next = -1;
    if (e.key === "ArrowRight") next = (idx + 1) % order.length;
    else if (e.key === "ArrowLeft") next = (idx - 1 + order.length) % order.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = order.length - 1;
    if (next >= 0) {
      e.preventDefault();
      activeTab = order[next];
      rootEl?.querySelector<HTMLButtonElement>(`[data-tab="${order[next]}"]`)?.focus();
    }
  }

  // ── Parameters: loading ───────────────────────────────────────────────
  async function loadGrantOptions(id: number): Promise<void> {
    let grants: any[] = [];
    try {
      grants = await getDashboardPermissions(id);
    } catch {
      grants = [];
    }
    if (dashId !== id) return;
    const opts = await Promise.all(
      grants
        .filter((g) => g.target_type !== PUBLIC_TARGET)
        .map(async (g) => ({
          value: String(g.id),
          label: `${listText("TARGET_TYPE", g.target_type) || g.target_type} · ${await resolveTargetLabel(g.target_type, g.target_code)}`,
        })),
    );
    if (dashId === id) grantOptions = opts;
  }

  async function loadParameters(id: number): Promise<void> {
    paramsLoading = true;
    let rows: DashboardParameter[] = [];
    try {
      rows = await getParameters(id);
    } catch {
      reportError(t("error_parameters", "Could not load the parameters."));
    } finally {
      paramsLoading = false;
    }
    if (dashId !== id) return;
    staged = rows.map((r) => ({
      name: r.name,
      label: r.label,
      data_type: r.data_type,
      is_required: !!r.is_required,
      default_value: r.default_value ?? null,
      list: r.list ?? null,
      context_binding: r.context_binding ?? null,
      bindingLabel: r.binding_label ?? null,
    }));
    initialByName = new Map(staged.map((p) => [p.name, snapshot(p)]));
    await Promise.all(staged.map((p) => ensureList(p.list)));
  }

  const bindingText = (p: StagedParam): string => {
    const target =
      grantOptions.find((o) => o.value === String(p.context_binding))?.label ||
      p.bindingLabel || `#${p.context_binding}`;
    return t(
      "param_binding_sentence",
      "Bound to the grant for {target}: value fixed for viewers who reach the dashboard through it.",
    ).replace("{target}", target);
  };
  const SOURCES: ParameterValueSource[] = ["INPUT", "LIST", "GRANT"];
  const sourceHelp = (s: ParameterValueSource): string =>
    s === "GRANT"
      ? t("param_source_grant_help", "Viewers who reach the dashboard through the grant get its recipient as the value; everyone else is asked for it.")
      : s === "LIST"
        ? t("param_source_list_help", "The viewer picks one of the list's values in the parameters window before the dashboard runs.")
        : t("param_source_input_help", "The viewer types the value in the parameters window before the dashboard runs.");
  const sourceLabel = (s: ParameterValueSource): string =>
    s === "GRANT"
      ? t("param_source_grant", "Bound to a grant")
      : s === "LIST"
        ? t("param_source_list", "From a list")
        : t("param_source_input", "Entered by the viewer");
  const listName = (code: string | null): string =>
    (code && paramLists.find((l) => l.value === code)?.label) || code || "";
  const defaultText = (p: StagedParam): string => {
    if (p.default_value == null || p.default_value === "") return "—";
    if (p.list) return listText(p.list, p.default_value) || p.default_value;
    if (p.data_type === "BOOLEAN") {
      return p.default_value === "true" ? t("param_true", "True") : t("param_false", "False");
    }
    return p.default_value;
  };

  // ── Parameters: form ──────────────────────────────────────────────────
  const NAME_RE = /^[a-z][a-z0-9_]*$/;
  const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

  function validDate(v: string): boolean {
    if (!DATE_RE.test(v)) return false;
    const d = new Date(`${v}T00:00:00Z`);
    return !Number.isNaN(d.getTime()) && d.toISOString().slice(0, 10) === v;
  }

  function validateForm(): string | null {
    const name = fName.trim();
    if (editingName == null) {
      if (!NAME_RE.test(name) || name.length > 100) {
        return t("param_err_name", "Use lowercase letters, digits and _, starting with a letter (at most 100).");
      }
      if (staged.some((p) => p.name === name)) {
        return t("param_err_duplicate", "This dashboard already has a parameter with that name.");
      }
    }
    if (!fLabel.trim()) return t("param_err_label", "The label is required.");
    if (!fType) return t("param_err_type", "Choose a data type.");
    if (fSource === "LIST" && !fList) return t("param_err_list", "Choose the allowed values list.");
    if (fSource === "GRANT" && !fBinding) return t("param_err_binding", "Choose the grant to bind to.");
    const d = fDefault.trim();
    if (d) {
      if (effectiveList) {
        if (!(listRaw[effectiveList] ?? []).some((i: any) => i.value === d)) {
          return t("param_err_default_list", "The default must be one of the list's values.");
        }
      } else if (fType === "NUMBER" && !/^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$/.test(d)) {
        return t("param_err_default_number", "The default must be a number (e.g. 10 or 1.5).");
      } else if (fType === "BOOLEAN" && d !== "true" && d !== "false") {
        return t("param_err_default_boolean", "The default must be true or false.");
      } else if (fType === "DATE" && !validDate(d)) {
        return t("param_err_default_date", "The default must be a valid date (YYYY-MM-DD).");
      }
    }
    return null;
  }

  function clearForm(): void {
    editingName = null;
    fName = "";
    fLabel = "";
    fType = "";
    fRequired = false;
    fSource = "INPUT";
    fList = "";
    fBinding = "";
    fDefault = "";
    fError = "";
  }

  function commitParam(): void {
    fError = validateForm() ?? "";
    if (fError) return;
    const binding = fSource === "GRANT" ? Number(fBinding) : null;
    const next: StagedParam = {
      name: editingName ?? fName.trim(),
      label: fLabel.trim(),
      data_type: fType,
      is_required: fRequired,
      default_value: fDefault.trim() || null,
      list: fSource === "INPUT" ? null : fList || null,
      context_binding: binding,
      bindingLabel: binding != null ? grantOptions.find((o) => o.value === String(binding))?.label ?? null : null,
    };
    staged = editingName != null
      ? staged.map((p) => (p.name === editingName ? next : p))
      : [...staged, next];
    clearForm();
  }

  function editParam(p: StagedParam): void {
    editingName = p.name;
    fName = p.name;
    fLabel = p.label;
    fType = p.data_type;
    fRequired = p.is_required;
    fSource = sourceOf(p);
    fList = p.list ?? "";
    fBinding = p.context_binding != null ? String(p.context_binding) : "";
    fDefault = p.default_value ?? "";
    fError = "";
  }

  function removeParam(name: string): void {
    staged = staged.filter((p) => p.name !== name);
    if (editingName === name) clearForm();
  }

  // ── hydrate / flush / reset ───────────────────────────────────────────
  /** Edit (or view) an existing dashboard. */
  export async function hydrate(id: number, viewOnly = false): Promise<void> {
    dashId = id;
    readonly = viewOnly;
    await Promise.all([ensureList("PARAM_TYPE"), ensureList("TARGET_TYPE")]);
    try {
      paramLists = await getParameterLists();
    } catch {
      paramLists = [];
    }
    await Promise.all([loadParameters(id), loadGrantOptions(id), permTab?.hydrate(id)]);
  }

  export async function flushParameters(id: number): Promise<void> {
    const byName = new Map(staged.map((p) => [p.name, p]));
    for (const [name] of initialByName) {
      if (!byName.has(name)) await deleteParameter(id, name);
    }
    for (const p of staged) {
      const before = initialByName.get(p.name);
      const body = {
        label: p.label,
        data_type: p.data_type,
        is_required: p.is_required,
        default_value: p.default_value,
        list: p.list,
        context_binding: p.context_binding,
      };
      if (before === undefined) await createParameter(id, { name: p.name, ...body });
      else if (before !== snapshot(p)) await updateParameter(id, p.name, body);
    }
    await loadParameters(id);
  }

  /** Save the Permissions tab; the grant choices for bindings follow. */
  export async function flushPermissions(id: number): Promise<any[]> {
    const revoked = (await permTab?.flush(id)) ?? [];
    await loadGrantOptions(id);
    return revoked;
  }

  // Revoking a grant a parameter is bound to: warn that the binding stops applying.
  function revokeWarning(grantId: number): string | null {
    const names = staged.filter((p) => p.context_binding === grantId).map((p) => p.name);
    if (!names.length) return null;
    return t(
      "perm_revoke_bound_warning",
      "This grant is used by the parameter(s) {names}; their binding will stop applying. Continue?",
    ).replace("{names}", names.join(", "));
  }

  export function reset(): void {
    dashId = null;
    readonly = false;
    activeTab = "core";
    coreDirty = false;
    staged = [];
    initialByName = new Map();
    grantOptions = [];
    clearForm();
    permTab?.reset();
  }

  onMount(() => {
    void ensureList("PARAM_TYPE");
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

  // Compact controls for the Parameters form (spec US3-12: keep the list in view).
  const compactFieldClass =
    "w-full rounded-lg border border-gray-300 px-2.5 py-1.5 text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 disabled:bg-gray-100 disabled:cursor-not-allowed dark:border-gray-700 dark:bg-gray-800 dark:text-white dark:disabled:bg-gray-800";
  const miniLabelClass = "block text-xs font-medium text-gray-600 dark:text-gray-400 mb-0.5 truncate";
  const compactAddBtnClass =
    "w-full whitespace-nowrap rounded-lg border border-indigo-600 px-3 py-1.5 text-sm font-semibold text-indigo-600 hover:bg-indigo-50 dark:text-indigo-400 dark:hover:bg-indigo-900/30";
  const rowClass =
    "flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg border border-gray-200 dark:border-gray-800 bg-gray-50/50 dark:bg-white/[0.02] px-3 py-2";
  const emptyClass =
    "rounded-lg border border-dashed border-gray-300 dark:border-gray-700 p-6 text-center text-sm text-gray-500 dark:text-gray-400";
  const chipClass =
    "shrink-0 rounded-full bg-gray-100 px-2 py-0.5 text-[11px] font-semibold text-gray-600 dark:bg-gray-700 dark:text-gray-300";
  const sourceChipClass: Record<ParameterValueSource, string> = {
    GRANT: "shrink-0 rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300",
    LIST: "shrink-0 rounded-full bg-indigo-50 px-2 py-0.5 text-[11px] font-semibold text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300",
    INPUT: "shrink-0 rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
  };
</script>

<div bind:this={rootEl}>
  {#snippet pendingDot()}
    <span
      class="ml-1 inline-block h-1.5 w-1.5 rounded-full bg-amber-500"
      title={t("unsaved_indicator", "Unsaved changes")}
      aria-hidden="true"
    ></span>
  {/snippet}

  <div class="border-b border-gray-200 dark:border-gray-800">
    <div role="tablist" aria-label="Dashboard detail sections" class="-mb-px flex flex-nowrap gap-4 overflow-x-auto no-scrollbar text-sm font-medium sm:gap-6">
      {#each tabOrder as name (name)}
        <button
          type="button"
          role="tab"
          data-tab={name}
          aria-selected={activeTab === name}
          aria-disabled={tabDisabled(name)}
          tabindex={activeTab === name ? 0 : -1}
          title={tabDisabled(name) ? t("create_first_hint", "Save the dashboard first to add parameters and permissions.") : undefined}
          class={tabClass(name)}
          onclick={() => activateTab(name)}
          onkeydown={(e) => onTabKeydown(e)}
        >
          <span>{tabLabel(name)}</span>
          {#if tabCount(name)}
            <span class="ml-1 rounded-full bg-indigo-100 px-1.5 py-0.5 text-[10px] font-semibold text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300">{tabCount(name)}</span>
          {/if}
          {#if tabDirty[name]}{@render pendingDot()}{/if}
        </button>
      {/each}
    </div>
  </div>
  {#if dashId == null}
    <p class="pt-3 text-xs text-gray-500 dark:text-gray-400">{t("create_first_hint", "Save the dashboard first to add parameters and permissions.")}</p>
  {/if}

  <!-- Core Fields (empty shell — the parent re-parents its <section> here) -->
  <div data-tabpanel="core" role="tabpanel" class="pt-4" class:hidden={activeTab !== "core"}>
    <section id={`${idPrefix}-core`}></section>
  </div>

  <!-- Parameters -->
  <div data-tabpanel="parameters" role="tabpanel" class="pt-4 space-y-4" class:hidden={activeTab !== "parameters"}>
    {#if !readonly}
      <!-- Compact add/edit form: two dense rows + one help line, so the declared
           parameters stay in view below it (spec US3-12). -->
      <section class="rounded-lg border border-gray-200 dark:border-gray-800 px-3 py-2.5">
        <div class="grid grid-cols-2 gap-x-3 gap-y-2 md:grid-cols-12">
          <div class="md:col-span-3">
            <label for={`${idPrefix}-param-name`} class={miniLabelClass}>{t("param_name", "Name")}</label>
            <input
              id={`${idPrefix}-param-name`} type="text" maxlength="100" bind:value={fName}
              disabled={editingName != null} placeholder="date_from"
              title={editingName != null
                ? t("param_name_immutable_hint", "The name cannot be changed. Remove the parameter and add it again instead.")
                : t("param_name_hint", "Lowercase letters, digits and _, starting with a letter (e.g. date_from).")}
              class={compactFieldClass}
            />
          </div>
          <div class="md:col-span-3">
            <label for={`${idPrefix}-param-label`} class={miniLabelClass}>{t("param_label", "Label")}</label>
            <input id={`${idPrefix}-param-label`} type="text" maxlength="100" bind:value={fLabel} class={compactFieldClass} />
          </div>
          <div class="md:col-span-2">
            <label for={`${idPrefix}-param-type`} class={miniLabelClass}>{t("param_type", "Data type")}</label>
            <select id={`${idPrefix}-param-type`} bind:value={fType} class={compactFieldClass}>
              <option value="">{t("choose", "— choose —")}</option>
              {#each typeOptions as o (o.value)}
                <option value={o.value}>{o.label}</option>
              {/each}
            </select>
          </div>
          <div class="flex items-end pb-1.5 md:col-span-2">
            <label class="inline-flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
              <input type="checkbox" bind:checked={fRequired} class="rounded border-gray-300" />
              {t("param_required", "Required")}
            </label>
          </div>
          <div class="col-span-2 flex items-end justify-end gap-1.5 md:col-span-2">
            {#if editingName != null}
              <button type="button" class="rounded-lg px-3 py-1.5 text-sm font-semibold text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-800" onclick={clearForm}>{t("param_cancel_edit", "Cancel")}</button>
            {/if}
            <button type="button" class={compactAddBtnClass} onclick={commitParam}>
              {editingName != null ? t("param_update", "Update parameter") : t("param_add", "Add parameter")}
            </button>
          </div>

          <div class="col-span-2 md:col-span-5">
            <!-- A real radio group: each option is a card with a visible radio
                 circle, so it reads as "pick exactly one". Native radios keep
                 arrow-key navigation and screen-reader semantics. -->
            <!-- Framed group: the legend sits on the frame's top edge, so the
                 three options visibly belong to "Value source". -->
            <fieldset class="rounded-lg border border-gray-300 bg-gray-50/60 px-2 pb-2 pt-0.5 dark:border-gray-700 dark:bg-white/[0.02]">
              <legend class="px-1 text-xs font-medium text-gray-600 dark:text-gray-400">
                {t("param_source", "Value source")}
                <span class="font-normal text-gray-400 dark:text-gray-500">· {t("param_source_pick", "choose one")}</span>
              </legend>
              <div class="grid grid-cols-3 gap-1.5">
                {#each SOURCES as src (src)}
                  <label
                    class="flex cursor-pointer items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-2 py-1.5 text-xs font-medium leading-tight text-gray-600 transition-colors hover:border-indigo-400 hover:bg-indigo-50/50 has-[:checked]:border-indigo-600 has-[:checked]:bg-indigo-50 has-[:checked]:font-semibold has-[:checked]:text-indigo-700 has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-indigo-300 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-indigo-900/20 dark:has-[:checked]:border-indigo-400 dark:has-[:checked]:bg-indigo-900/40 dark:has-[:checked]:text-indigo-200"
                    title={sourceHelp(src)}
                  >
                    <input
                      type="radio"
                      name={`${idPrefix}-param-source`}
                      value={src}
                      bind:group={fSource}
                      class="h-3.5 w-3.5 shrink-0 accent-indigo-600 focus:outline-none"
                    />
                    <svg class="h-3.5 w-3.5 shrink-0 opacity-70" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      {#if src === "INPUT"}
                        <!-- pencil: the viewer types it -->
                        <path d="M13.5 3.5l3 3L7 16H4v-3l9.5-9.5z" />
                      {:else if src === "LIST"}
                        <!-- list: the viewer picks from it -->
                        <path d="M7 5h10M7 10h10M7 15h10M3.5 5h.01M3.5 10h.01M3.5 15h.01" />
                      {:else}
                        <!-- key: fixed by the grant -->
                        <circle cx="6.5" cy="13.5" r="3" /><path d="M8.6 11.4L16 4m-2.5 2.5L15.5 8.5M12 8l1.5 1.5" />
                      {/if}
                    </svg>
                    <span>{sourceLabel(src)}</span>
                  </label>
                {/each}
              </div>
            </fieldset>
          </div>
          {#if fSource === "GRANT"}
            <div class="md:col-span-3">
              <label for={`${idPrefix}-param-binding`} class={miniLabelClass}>{t("param_binding", "Grant")}</label>
              <select id={`${idPrefix}-param-binding`} bind:value={fBinding} class={compactFieldClass}>
                <option value="">{t("param_choose_binding", "— choose grant —")}</option>
                {#each grantOptions as o (o.value)}
                  <option value={o.value}>{o.label}</option>
                {/each}
              </select>
            </div>
          {/if}
          {#if fSource !== "INPUT"}
            <div class={fSource === "GRANT" ? "md:col-span-2" : "md:col-span-3"}>
              <label for={`${idPrefix}-param-list`} class={miniLabelClass} title={fSource === "GRANT" ? t("param_fallback_list", "Fallback list (optional)") : undefined}>
                {fSource === "GRANT" ? t("param_fallback_list", "Fallback list (optional)") : t("param_list", "Allowed values list")}
              </label>
              <select id={`${idPrefix}-param-list`} bind:value={fList} onchange={() => (fDefault = "")} class={compactFieldClass}>
                <option value="">{t("param_choose_list", "— choose list —")}</option>
                {#each paramLists as o (o.value)}
                  <option value={o.value}>{o.label}</option>
                {/each}
              </select>
            </div>
          {/if}
          <div class={fSource === "GRANT" ? "md:col-span-2" : fSource === "LIST" ? "md:col-span-4" : "md:col-span-7"}>
            <label for={`${idPrefix}-param-default`} class={miniLabelClass}>{t("param_default", "Default value")}</label>
            <div class="flex gap-2">
              {#if effectiveList}
                <select id={`${idPrefix}-param-default`} bind:value={fDefault} class={compactFieldClass}>
                  <option value="">{t("param_default_none", "— no default —")}</option>
                  {#each defaultValueOptions as o (o.value)}
                    <option value={o.value}>{o.label}</option>
                  {/each}
                </select>
              {:else if fType === "BOOLEAN"}
                <select id={`${idPrefix}-param-default`} bind:value={fDefault} class={compactFieldClass}>
                  <option value="">{t("param_default_none", "— no default —")}</option>
                  <option value="true">{t("param_true", "True")}</option>
                  <option value="false">{t("param_false", "False")}</option>
                </select>
              {:else if fType === "DATE"}
                <input id={`${idPrefix}-param-default`} type="date" bind:value={fDefault} class={compactFieldClass} />
              {:else}
                <input id={`${idPrefix}-param-default`} type="text" inputmode={fType === "NUMBER" ? "decimal" : "text"} bind:value={fDefault} class={compactFieldClass} />
              {/if}
            </div>
          </div>
        </div>
        <!-- One line of context: the error if any, else the active source's help. -->
        {#if fError}
          <p class="mt-1.5 text-xs text-red-600 dark:text-red-400" role="alert">{fError}</p>
        {:else if fSource === "GRANT" && grantOptions.length === 0}
          <p class="mt-1.5 text-xs text-amber-600 dark:text-amber-400">{t("param_no_grants", "This dashboard has no grant to a user, role, project, team or unit yet.")}</p>
        {:else}
          <p class="mt-1.5 truncate text-xs text-gray-500 dark:text-gray-400" title={sourceHelp(fSource)}>{sourceHelp(fSource)}</p>
        {/if}
      </section>
    {/if}

    <section>
      {#if paramsLoading}
        <div class="text-sm text-gray-400">…</div>
      {:else if staged.length === 0}
        <div class={emptyClass}>{t("param_empty", "No parameters yet.")}</div>
      {:else}
        <ul class="space-y-2">
          {#each staged as p (p.name)}
            <li
              class={pendingNames.has(p.name) ? `${rowClass} ring-2 ring-amber-400` : rowClass}
              data-pending={pendingNames.has(p.name) ? "1" : undefined}
            >
              <span class="min-w-0 flex-1">
                <span class="block truncate text-sm font-semibold text-gray-800 dark:text-gray-200">
                  {p.label} <code class="ml-1 text-xs font-normal text-gray-500 dark:text-gray-400">{p.name}</code>
                  {#if p.is_required}<span class="ml-1 text-red-500" title={t("param_required", "Required")}>*</span>{/if}
                </span>
                <span class="block truncate text-xs text-gray-500 dark:text-gray-400">
                  {#if sourceOf(p) === "GRANT"}
                    {bindingText(p)}
                  {:else if sourceOf(p) === "LIST"}
                    {t("param_list", "Allowed values list")}: {listName(p.list)}
                  {:else}
                    {t("param_source_input_help", "The viewer types the value in the parameters window before the dashboard runs.")}
                  {/if}
                </span>
              </span>
              <span class={chipClass}>{listText("PARAM_TYPE", p.data_type) || p.data_type}</span>
              <span class="shrink-0 text-xs text-gray-500 dark:text-gray-400" title={t("param_default", "Default value")}>{defaultText(p)}</span>
              <span class={sourceChipClass[sourceOf(p)]}>{sourceLabel(sourceOf(p))}</span>
              {#if !readonly}
                <button type="button" class="shrink-0 rounded-md px-2 py-1 text-xs font-semibold text-indigo-600 hover:bg-indigo-50 dark:text-indigo-400 dark:hover:bg-indigo-900/30" onclick={() => editParam(p)}>{t("param_edit", "Edit")}</button>
                <button type="button" class="shrink-0 rounded-md p-1 text-gray-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/30" title={t("param_remove", "Remove")} aria-label={t("param_remove", "Remove")} onclick={() => removeParam(p.name)}>
                  <svg class="w-4 h-4" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" /></svg>
                </button>
              {/if}
            </li>
          {/each}
        </ul>
      {/if}
    </section>
  </div>

  <!-- Permissions — the shared PermissionsTab island (bound to dashboard_permissions). -->
  <div data-tabpanel="permissions" role="tabpanel" class="pt-4 space-y-4" class:hidden={activeTab !== "permissions"}>
    <PermissionsTab
      bind:this={permTab}
      {idPrefix}
      api={dashboardPermissionsApi}
      i18nPrefix={P}
      {readonly}
      onError={reportError}
      onRevokeWarning={revokeWarning}
    />
  </div>
</div>
