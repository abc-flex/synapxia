<script lang="ts">
  /**
   * InitiativeDetailTabs — the six tabs of Initiative Management's edit dialog
   * (specs/004-initiative-management): Core Fields, Diagnosis Questions,
   * Related Assets, Permissions, Discussion, History.
   *
   * Derived from AssetDetailTabs.svelte (same tab strip, pending-change dots and
   * diff-based `flush`), minus the characterization/versioning machinery.
   * Mounted manually by InitiativeDetailModal.astro, which drives it through the
   * exported controller methods (Svelte 5 `mount()` returns them).
   *
   * - Core Fields is an empty shell the parent re-parents its own <section> into.
   * - Diagnosis Questions and History are read-only; Discussion is interactive
   *   (Foro with the collaborations `api`) and saves each post on its own.
   * - Related Assets / Permissions stage edits and persist ONLY when the parent
   *   calls `flush()` for that tab (tab-scoped save).
   */
  import { onMount } from "svelte";
  import { getAssetsSelect, getAssetsWithAccess } from "@/lib/assets";
  import { getListItemsbyList } from "@/lib/list_items";
  import {
    getInitiativeDiagnostics,
    getInitiativeAssets,
    addInitiativeAsset,
    removeInitiativeAsset,
  } from "@/lib/initiatives";
  import {
    getInitPermissionsByInit,
    createInitPermission,
    deleteInitPermission,
  } from "@/lib/init_permissions";
  import { initiativeForoApi } from "@/lib/collaborations";
  import { getUsersSelect } from "@/lib/users";
  import { getRolesSelect } from "@/lib/roles";
  import { getTeamsSelect } from "@/lib/teams";
  import { getBusinessUnitsSelect } from "@/lib/business_units";
  import { getProjectsSelect } from "@/lib/projects";
  import { getUser } from "@/lib/auth";
  import { translate } from "@/utils/i18nClient";
  import Foro from "@/components/svelte/Foro.svelte";
  import type { DiagnosticRow } from "@/types/api";

  type TabName = "core" | "diagnosis" | "related" | "permissions" | "discussion" | "history";
  type SelectOption = { value: string; label: string };
  type StagedLink = {
    asset: number;
    assetLabel: string;
    type: string;
    typeLabel: string;
    rationale: string;
  };
  type StagedPermission = {
    id?: number;
    targetType: string;
    targetTypeLabel: string;
    targetCode: string;
    targetCodeLabel: string;
    access: string;
    accessLabel: string;
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

  const TARGET_LOADERS: Record<string, () => Promise<SelectOption[]>> = {
    USER: getUsersSelect,
    ROLE: getRolesSelect,
    TEAM: getTeamsSelect,
    UNIT: getBusinessUnitsSelect,
    PROJECT: getProjectsSelect,
  };
  // init_permissions stores PUBLIC grants with target_code "ALL" (seed convention).
  const PUBLIC_CODE = "ALL";

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
  const currentLang = (): string =>
    (typeof localStorage !== "undefined" && localStorage.getItem("lang")) === "es" ? "es" : "en";
  const langItems = (items: any[]): any[] => {
    const lang = currentLang();
    const byLang = items.filter((li) => li.lang === lang);
    return (byLang.length ? byLang : items.filter((li) => li.lang === "en")).sort(
      (a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0),
    );
  };

  // ── State ─────────────────────────────────────────────────────────────
  let rootEl = $state<HTMLElement | undefined>(undefined);
  let activeTab = $state<TabName>("core");
  let initId = $state<number | null>(null);
  let coreDirty = $state(false);

  // Diagnosis (read-only)
  let diagItems = $state<DiagnosticRow[]>([]);
  let diagTotals = $state<{ creator: number | null; creatorN: number; reviewer: number | null; reviewerN: number }>({
    creator: null, creatorN: 0, reviewer: null, reviewerN: 0,
  });
  // Rationale per criterion is collapsed by default (Show / Hide switch).
  let rationaleOpen = $state<Record<string, boolean>>({});
  let diagLoading = $state(false);
  let diagError = $state("");

  // Related assets
  let stagedLinks = $state<StagedLink[]>([]);
  // Keyed by (asset, relation type): the same asset may be linked once per type.
  const linkKey = (asset: number, type: string): string => `${asset}:${type}`;
  let initialLinkByKey = $state(new Map<string, { asset: number; type: string; rationale: string }>());
  let assetOptions = $state<SelectOption[]>([]);
  let relTypeOptions = $state<SelectOption[]>([]);
  let relTarget = $state("");
  let relType = $state("");
  let relRationale = $state("");
  let relError = $state("");

  // Permissions
  let stagedPermissions = $state<StagedPermission[]>([]);
  let initialPermById = $state(new Map<number, any>());
  let targetTypeOptions = $state<SelectOption[]>([]);
  let accessOptions = $state<SelectOption[]>([]);
  let targetTypeLabels = new Map<string, string>();
  let accessLabels = new Map<string, string>();
  let permType = $state("");
  let permCode = $state("");
  let permAccess = $state("");
  let permCodeOptions = $state<SelectOption[]>([]);
  let permCodeDisabled = $state(false);
  let permError = $state("");

  const listItemsCache = new Map<string, any[]>();
  const targetOptCache = new Map<string, SelectOption[]>();

  $effect(() => {
    onTabChange?.(activeTab);
  });

  export function setCoreDirty(dirty: boolean): void {
    coreDirty = dirty;
  }

  export function activateTab(name: TabName): void {
    activeTab = name;
  }

  // ── Dirty tracking ────────────────────────────────────────────────────
  export function relationsDirty(): boolean {
    const staged = new Set(stagedLinks.map((l) => linkKey(l.asset, l.type)));
    for (const [key] of initialLinkByKey) if (!staged.has(key)) return true;
    for (const l of stagedLinks) {
      const initial = initialLinkByKey.get(linkKey(l.asset, l.type));
      if (!initial || initial.rationale !== l.rationale) return true;
    }
    return false;
  }

  export function permissionsDirty(): boolean {
    const stagedIds = new Set(stagedPermissions.filter((p) => p.id != null).map((p) => p.id));
    for (const [pid] of initialPermById) if (!stagedIds.has(pid)) return true;
    return stagedPermissions.some((p) => p.id == null);
  }

  const pendingLinkKeys = $derived.by(() => {
    const set = new Set<string>();
    for (const l of stagedLinks) {
      const key = linkKey(l.asset, l.type);
      const initial = initialLinkByKey.get(key);
      if (!initial || initial.rationale !== l.rationale) set.add(key);
    }
    return set;
  });
  const tabDirty = $derived<Partial<Record<TabName, boolean>>>({
    core: coreDirty,
    related: relationsDirty(),
    permissions: permissionsDirty(),
  });

  export function focusFirstPending(): void {
    rootEl
      ?.querySelector<HTMLElement>(`[data-tabpanel="${activeTab}"] [data-pending="1"]`)
      ?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  // ── Tabs ──────────────────────────────────────────────────────────────
  const tabOrder: TabName[] = ["core", "diagnosis", "related", "permissions", "discussion", "history"];
  const tabLabel = (name: TabName): string => {
    const keys: Record<TabName, [string, string]> = {
      core: ["initiative_detail_modal.tab_core", "Core Fields"],
      diagnosis: ["initiative_detail_modal.tab_diagnosis", "Diagnosis Questions"],
      related: ["initiative_detail_modal.tab_related", "Related Assets"],
      permissions: ["initiative_detail_modal.tab_permissions", "Permissions"],
      discussion: ["initiative_detail_modal.tab_discussion", "Discussion"],
      history: ["initiative_detail_modal.tab_history", "History"],
    };
    return t(keys[name][0], keys[name][1]);
  };
  const tabCount = (name: TabName): number | null =>
    name === "related" ? stagedLinks.length : name === "permissions" ? stagedPermissions.length : null;
  const tabClass = (name: TabName): string =>
    "whitespace-nowrap border-b-2 px-1 pb-3 " +
    (activeTab === name
      ? "border-indigo-600 text-indigo-600 dark:text-indigo-400"
      : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200");

  function onTabKeydown(e: KeyboardEvent): void {
    const idx = tabOrder.indexOf(activeTab);
    let next = -1;
    if (e.key === "ArrowRight") next = (idx + 1) % tabOrder.length;
    else if (e.key === "ArrowLeft") next = (idx - 1 + tabOrder.length) % tabOrder.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = tabOrder.length - 1;
    if (next >= 0) {
      e.preventDefault();
      activeTab = tabOrder[next];
      rootEl?.querySelector<HTMLButtonElement>(`[data-tab="${tabOrder[next]}"]`)?.focus();
    }
  }

  // ── Options ───────────────────────────────────────────────────────────
  async function listItems(code: string): Promise<any[]> {
    let items = listItemsCache.get(code);
    if (!items) {
      items = await getListItemsbyList(code);
      listItemsCache.set(code, items);
    }
    return items;
  }

  async function loadOptions(): Promise<void> {
    // Only offer assets the owner can see (the API refuses the rest anyway);
    // fall back to the plain picker for accounts without Asset Management.
    try {
      const rows = await getAssetsWithAccess();
      assetOptions = rows.map((a: any) => ({ value: String(a.id), label: a.name }));
    } catch {
      try {
        assetOptions = await getAssetsSelect();
      } catch {
        assetOptions = [];
      }
    }
    try {
      relTypeOptions = langItems(await listItems("RELATION_TYPE")).map((li) => ({ value: li.value, label: li.label || li.value }));
    } catch {
      relTypeOptions = [];
    }
    try {
      const li = langItems(await listItems("TARGET_TYPE"));
      targetTypeOptions = li.map((x) => ({ value: x.value, label: x.label || x.value }));
      targetTypeLabels = new Map(li.map((x) => [x.value, x.label || x.value]));
    } catch {
      targetTypeOptions = [];
    }
    try {
      const li = langItems(await listItems("ACCESS_LEVEL"));
      accessOptions = li.map((x) => ({ value: x.value, label: x.label || x.value }));
      accessLabels = new Map(li.map((x) => [x.value, x.label || x.value]));
    } catch {
      accessOptions = [];
    }
  }

  async function targetOptions(targetType: string): Promise<SelectOption[]> {
    const loader = TARGET_LOADERS[targetType];
    if (!loader) return [];
    let opts = targetOptCache.get(targetType);
    if (!opts) {
      try {
        opts = await loader();
      } catch {
        opts = [];
      }
      targetOptCache.set(targetType, opts);
    }
    return opts;
  }

  async function resolveTargetLabel(targetType: string, targetCode: string): Promise<string> {
    if (targetType === "PUBLIC") return t("initiative_detail_modal.perm_public", "Public");
    return (await targetOptions(targetType)).find((o) => o.value === targetCode)?.label || targetCode;
  }

  // ── Diagnosis ─────────────────────────────────────────────────────────
  async function loadDiagnosis(id: number): Promise<void> {
    diagLoading = true;
    diagError = "";
    try {
      const res = await getInitiativeDiagnostics(id, currentLang());
      if (initId !== id) return;
      diagItems = res.items;
      diagTotals = {
        creator: res.creator_total ?? null, creatorN: res.creator_answered ?? 0,
        reviewer: res.reviewer_total ?? null, reviewerN: res.reviewer_answered ?? 0,
      };
      rationaleOpen = {};
    } catch {
      diagItems = [];
      diagError = t("initiative_detail_modal.error_diagnosis", "Could not load the diagnosis.");
    } finally {
      diagLoading = false;
    }
  }

  // ── Related assets ────────────────────────────────────────────────────
  function addLink(): void {
    relError = "";
    const asset = Number(relTarget);
    if (!asset || !relType) {
      relError = t("initiative_detail_modal.related_missing_fields", "Pick an asset and a relation type.");
      return;
    }
    if (stagedLinks.some((l) => l.asset === asset && l.type === relType)) {
      relError = t("initiative_detail_modal.related_duplicate", "This asset is already related with that relation type.");
      return;
    }
    stagedLinks = [
      ...stagedLinks,
      {
        asset,
        assetLabel: assetOptions.find((a) => Number(a.value) === asset)?.label || String(asset),
        type: relType,
        typeLabel: relTypeOptions.find((o) => o.value === relType)?.label || relType,
        rationale: relRationale.trim(),
      },
    ];
    relTarget = "";
    relType = "";
    relRationale = "";
  }
  function removeLink(idx: number): void {
    stagedLinks = stagedLinks.filter((_, i) => i !== idx);
  }

  // ── Permissions ───────────────────────────────────────────────────────
  async function onPermTypeChange(): Promise<void> {
    permCode = "";
    permCodeOptions = [];
    permCodeDisabled = permType === "PUBLIC";
    if (!permType || permType === "PUBLIC") return;
    permCodeOptions = await targetOptions(permType);
  }

  function addPermission(): void {
    permError = "";
    if (!permType || !permAccess) {
      permError = t("initiative_detail_modal.perm_missing_fields", "Pick a target type, target and access level.");
      return;
    }
    let targetCode: string;
    let targetCodeLabel: string;
    if (permType === "PUBLIC") {
      targetCode = PUBLIC_CODE;
      targetCodeLabel = t("initiative_detail_modal.perm_public", "Public");
    } else {
      targetCode = permCode;
      if (!targetCode) {
        permError = t("initiative_detail_modal.perm_missing_fields", "Pick a target type, target and access level.");
        return;
      }
      targetCodeLabel = permCodeOptions.find((o) => o.value === targetCode)?.label || targetCode;
    }
    if (stagedPermissions.some((p) => p.targetType === permType && p.targetCode === targetCode && p.access === permAccess)) {
      permError = t("initiative_detail_modal.perm_duplicate", "This target already has that access.");
      return;
    }
    stagedPermissions = [
      ...stagedPermissions,
      {
        targetType: permType,
        targetTypeLabel: targetTypeLabels.get(permType) || permType,
        targetCode,
        targetCodeLabel,
        access: permAccess,
        accessLabel: accessLabels.get(permAccess) || permAccess,
      },
    ];
    permType = "";
    permCode = "";
    permCodeOptions = [];
    permAccess = "";
  }

  // Revoking one's own MANAGE grant can lock the caller out — confirm first.
  function removePermission(idx: number): void {
    const p = stagedPermissions[idx];
    const me = getUser() as { id?: number } | null;
    const isOwnManage =
      p?.id != null && p.access === "MANAGE" && p.targetType === "USER" &&
      me && (me.id || me.id === 0) && String(me.id) === p.targetCode;
    if (isOwnManage && !window.confirm(t(
      "initiative_detail_modal.perm_self_revoke_confirm",
      "You are about to revoke your own manage access. Continue?",
    ))) return;
    stagedPermissions = stagedPermissions.filter((_, i) => i !== idx);
  }

  // ── hydrate / flush / reset ───────────────────────────────────────────
  export async function hydrate(id: number): Promise<void> {
    initId = id;
    await loadOptions();
    void loadDiagnosis(id);

    const [links, permissions] = await Promise.all([
      getInitiativeAssets(id).catch(() => {
        reportError(t("initiative_detail_modal.error_relations", "Could not load related assets."));
        return [] as any[];
      }),
      getInitPermissionsByInit(id).catch(() => {
        reportError(t("initiative_detail_modal.error_permissions", "Could not load permissions."));
        return [] as any[];
      }),
    ]);
    if (initId !== id) return;

    initialLinkByKey = new Map(
      links.map((l: any) => [linkKey(l.asset, l.type), { asset: l.asset, type: l.type, rationale: l.rationale ?? "" }]),
    );
    stagedLinks = links.map((l: any) => ({
      asset: l.asset,
      assetLabel: l.asset_name || String(l.asset),
      type: l.type,
      typeLabel: relTypeOptions.find((o) => o.value === l.type)?.label || l.type,
      rationale: l.rationale ?? "",
    }));

    initialPermById = new Map(permissions.map((p: any) => [p.id, p]));
    stagedPermissions = await Promise.all(
      permissions.map(async (p: any) => ({
        id: p.id,
        targetType: p.target_type,
        targetTypeLabel: targetTypeLabels.get(p.target_type) || p.target_type,
        targetCode: p.target_code,
        targetCodeLabel: await resolveTargetLabel(p.target_type, p.target_code),
        access: p.access_level,
        accessLabel: accessLabels.get(p.access_level) || p.access_level,
      })),
    );
  }

  export async function flush(
    id: number,
    opts?: { skipRelations?: boolean; skipPermissions?: boolean },
  ): Promise<void> {
    // 1. Related assets, keyed by (asset, type). There is no update route: a
    //    changed rationale is remove + add (the API restores the same row).
    if (!opts?.skipRelations) {
      const staged = new Map(stagedLinks.map((l) => [linkKey(l.asset, l.type), l]));
      for (const [key, initial] of initialLinkByKey) {
        const next = staged.get(key);
        if (!next || next.rationale !== initial.rationale) {
          await removeInitiativeAsset(id, initial.asset, initial.type);
        }
      }
      for (const l of stagedLinks) {
        const initial = initialLinkByKey.get(linkKey(l.asset, l.type));
        if (!initial || initial.rationale !== l.rationale) {
          await addInitiativeAsset(id, { asset: l.asset, type: l.type, rationale: l.rationale || null });
        }
      }
      initialLinkByKey = new Map(
        stagedLinks.map((l) => [linkKey(l.asset, l.type), { asset: l.asset, type: l.type, rationale: l.rationale }]),
      );
    }

    // 2. Permissions: revoke removed grants, create new ones.
    if (!opts?.skipPermissions) {
      const stagedIds = new Set(stagedPermissions.filter((p) => p.id != null).map((p) => p.id));
      for (const [pid] of initialPermById) {
        if (!stagedIds.has(pid)) await deleteInitPermission(pid);
      }
      for (const p of stagedPermissions) {
        if (p.id != null) continue;
        const created = await createInitPermission({
          init: id,
          target_type: p.targetType,
          target_code: p.targetCode,
          access_level: p.access,
        });
        p.id = created.id;
      }
      stagedPermissions = [...stagedPermissions];
      initialPermById = new Map(
        stagedPermissions
          .filter((p) => p.id != null)
          .map((p) => [p.id as number, { target_type: p.targetType, target_code: p.targetCode, access_level: p.access }]),
      );
    }
  }

  export function reset(): void {
    initId = null;
    activeTab = "core";
    coreDirty = false;
    diagItems = [];
    diagTotals = { creator: null, creatorN: 0, reviewer: null, reviewerN: 0 };
    rationaleOpen = {};
    diagError = "";
    stagedLinks = [];
    initialLinkByKey = new Map();
    relTarget = "";
    relType = "";
    relRationale = "";
    relError = "";
    stagedPermissions = [];
    initialPermById = new Map();
    permType = "";
    permCode = "";
    permCodeOptions = [];
    permCodeDisabled = false;
    permAccess = "";
    permError = "";
  }

  onMount(() => {
    const onLang = () => {
      langTick += 1;
      if (initId != null) void loadDiagnosis(initId);
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
  const answerClass = "text-sm text-gray-800 dark:text-gray-200";
  const mutedClass = "text-sm italic text-gray-400 dark:text-gray-500";
  const answeredLabel = (n: number): string =>
    t("initiative_detail_modal.diag_answered", "{n} of {m} answered")
      .replace("{n}", String(n))
      .replace("{m}", String(diagItems.length));
</script>

<div bind:this={rootEl}>
  {#snippet pendingDot()}
    <span
      class="ml-1 inline-block h-1.5 w-1.5 rounded-full bg-amber-500"
      title={t("initiative_detail_modal.unsaved_indicator", "Unsaved changes")}
      aria-hidden="true"
    ></span>
  {/snippet}
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
  {#snippet removeIcon()}
    <svg class="w-4 h-4" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" /></svg>
  {/snippet}

  <div class="border-b border-gray-200 dark:border-gray-800">
    <div role="tablist" aria-label="Initiative detail sections" class="-mb-px flex flex-nowrap gap-4 overflow-x-auto no-scrollbar text-sm font-medium sm:gap-6">
      {#each tabOrder as name (name)}
        <button
          type="button"
          role="tab"
          data-tab={name}
          aria-selected={activeTab === name}
          tabindex={activeTab === name ? 0 : -1}
          class={tabClass(name)}
          onclick={() => (activeTab = name)}
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

  <!-- Core Fields (empty shell — the parent re-parents its <section> here) -->
  <div data-tabpanel="core" role="tabpanel" class="pt-4" class:hidden={activeTab !== "core"}>
    <section id={`${idPrefix}-core`}></section>
  </div>

  <!-- Diagnosis Questions (read-only) -->
  <div data-tabpanel="diagnosis" role="tabpanel" class="pt-4 space-y-4" class:hidden={activeTab !== "diagnosis"}>
    {#if diagLoading}
      <div class="text-sm text-gray-400">{t("initiative_detail_modal.diag_loading", "Loading diagnosis…")}</div>
    {:else if diagError}
      <div class="text-sm text-red-600 dark:text-red-400">{diagError}</div>
    {:else if diagItems.length === 0}
      <div class={emptyClass}>{t("initiative_detail_modal.diag_empty", "No diagnosis criteria are configured.")}</div>
    {:else}
      <!-- Overall score, one card per party (same tints as their table columns). -->
      <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div class="rounded-lg border border-indigo-200 bg-indigo-50 px-4 py-3 dark:border-indigo-500/30 dark:bg-indigo-500/10">
          <p class="text-xs font-semibold uppercase tracking-wide text-indigo-700 dark:text-indigo-300">{t("initiative_detail_modal.diag_score_creator", "Proposer's overall score")}</p>
          <p class="mt-1 text-2xl font-bold text-indigo-700 dark:text-indigo-200">{diagTotals.creator ?? "—"}</p>
          <p class="text-xs text-indigo-600/80 dark:text-indigo-300/80">{answeredLabel(diagTotals.creatorN)}</p>
        </div>
        <div class="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 dark:border-emerald-500/30 dark:bg-emerald-500/10">
          <p class="text-xs font-semibold uppercase tracking-wide text-emerald-700 dark:text-emerald-300">{t("initiative_detail_modal.diag_score_reviewer", "Reviewer's overall score")}</p>
          <p class="mt-1 text-2xl font-bold text-emerald-700 dark:text-emerald-200">{diagTotals.reviewer ?? "—"}</p>
          <p class="text-xs text-emerald-700/80 dark:text-emerald-300/80">
            {diagTotals.reviewer == null ? t("initiative_detail_modal.diag_pending", "Pending diagnosis") : answeredLabel(diagTotals.reviewerN)}
          </p>
        </div>
      </div>

      <div class="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-800">
        <table class="w-full min-w-[640px] text-left text-sm">
          <thead>
            <tr class="border-b border-gray-200 text-xs font-semibold uppercase tracking-wide dark:border-gray-800">
              <th class="px-3 py-2 text-gray-500 dark:text-gray-400">{t("initiative_detail_modal.diag_criterion", "Criterion")}</th>
              <th class="w-[30%] bg-indigo-50 px-3 py-2 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-300">{t("initiative_detail_modal.diag_creator", "Proposer's answer")}</th>
              <th class="w-[30%] bg-emerald-50 px-3 py-2 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300">{t("initiative_detail_modal.diag_reviewer", "Reviewer's answer")}</th>
            </tr>
          </thead>
          <tbody>
            {#each diagItems as row (row.criteria)}
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
                  {#if row.rationale}
                    <div class="mt-2 flex justify-end">
                      {@render rationaleToggle(row.criteria)}
                    </div>
                  {/if}
                </td>
                <td class="bg-indigo-50/40 px-3 py-3 dark:bg-indigo-500/5">
                  {@render answerCell(row.creator_score, row.creator_label, t("initiative_detail_modal.diag_not_answered", "Not answered"), "indigo")}
                </td>
                <td class="bg-emerald-50/40 px-3 py-3 dark:bg-emerald-500/5">
                  {@render answerCell(
                    row.reviewer_score,
                    row.reviewer_label,
                    row.creator_label ? t("initiative_detail_modal.diag_pending", "Pending diagnosis") : t("initiative_detail_modal.diag_not_answered", "Not answered"),
                    "emerald",
                  )}
                </td>
              </tr>
              {#if row.rationale && rationaleOpen[row.criteria]}
                <tr class="border-b border-gray-100 last:border-0 dark:border-gray-800/60">
                  <td colspan="3" class="bg-gray-50 px-3 py-2 dark:bg-white/[0.02]">
                    <p class="text-[11px] font-semibold uppercase tracking-wide text-gray-400">{t("initiative_detail_modal.diag_rationale", "Rationale")}</p>
                    <p class="text-sm text-gray-700 dark:text-gray-300">{row.rationale}</p>
                  </td>
                </tr>
              {/if}
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </div>

  <!-- Related Assets -->
  <div data-tabpanel="related" role="tabpanel" class="pt-4 space-y-4" class:hidden={activeTab !== "related"}>
    <section>
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div>
          <label for={`${idPrefix}-rel-target`} class={labelClass}>{t("initiative_detail_modal.related_target", "Asset")}</label>
          <select id={`${idPrefix}-rel-target`} bind:value={relTarget} class={fieldClass}>
            <option value="">{t("initiative_detail_modal.related_choose_asset", "— choose asset —")}</option>
            {#each assetOptions as a (a.value)}
              <option value={a.value}>{a.label}</option>
            {/each}
          </select>
        </div>
        <div>
          <label for={`${idPrefix}-rel-type`} class={labelClass}>{t("initiative_detail_modal.related_type", "Relation type")}</label>
          <select id={`${idPrefix}-rel-type`} bind:value={relType} class={fieldClass}>
            <option value="">{t("initiative_detail_modal.choose_type", "— choose type —")}</option>
            {#each relTypeOptions as o (o.value)}
              <option value={o.value}>{o.label}</option>
            {/each}
          </select>
        </div>
        <div class="md:col-span-2">
          <label for={`${idPrefix}-rel-rationale`} class={labelClass}>{t("initiative_detail_modal.related_rationale", "Rationale")}</label>
          <div class="flex gap-2">
            <input id={`${idPrefix}-rel-rationale`} type="text" bind:value={relRationale} placeholder={t("initiative_detail_modal.related_rationale_placeholder", "Why is this asset related? (optional)")} class={`flex-1 ${fieldClass}`} />
            <button type="button" class={addBtnClass} onclick={addLink}>{t("initiative_detail_modal.related_add", "Add asset")}</button>
          </div>
        </div>
      </div>
      {#if relError}
        <p class="mt-2 text-xs text-red-600 dark:text-red-400">{relError}</p>
      {/if}
    </section>
    <section>
      {#if stagedLinks.length === 0}
        <div class={emptyClass}>{t("initiative_detail_modal.related_empty", "No related assets yet.")}</div>
      {:else}
        <ul class="space-y-2">
          {#each stagedLinks as link, idx (linkKey(link.asset, link.type))}
            <li
              class={pendingLinkKeys.has(linkKey(link.asset, link.type)) ? `${rowClass} ring-2 ring-amber-400` : rowClass}
              data-pending={pendingLinkKeys.has(linkKey(link.asset, link.type)) ? "1" : undefined}
            >
              <span class="min-w-0 flex-1 truncate text-sm font-semibold text-gray-800 dark:text-gray-200" title={link.assetLabel}>{link.assetLabel}</span>
              <span class="shrink-0 rounded-full bg-indigo-50 px-2 py-0.5 text-[11px] font-semibold text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300">{link.typeLabel || link.type}</span>
              {#if link.rationale}
                <span class="hidden md:block max-w-[220px] truncate text-xs text-gray-500 dark:text-gray-400" title={link.rationale}>{link.rationale}</span>
              {/if}
              <button type="button" class="shrink-0 rounded-md p-1 text-gray-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/30" title={t("initiative_detail_modal.related_remove", "Remove")} aria-label={t("initiative_detail_modal.related_remove", "Remove")} onclick={() => removeLink(idx)}>
                {@render removeIcon()}
              </button>
            </li>
          {/each}
        </ul>
      {/if}
    </section>
  </div>

  <!-- Permissions -->
  <div data-tabpanel="permissions" role="tabpanel" class="pt-4 space-y-4" class:hidden={activeTab !== "permissions"}>
    <section>
      <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
        <div>
          <label for={`${idPrefix}-perm-target-type`} class={labelClass}>{t("initiative_detail_modal.perm_target_type", "Target type")}</label>
          <select id={`${idPrefix}-perm-target-type`} bind:value={permType} onchange={onPermTypeChange} class={fieldClass}>
            <option value="">{t("initiative_detail_modal.perm_choose_target_type", "— choose type —")}</option>
            {#each targetTypeOptions as o (o.value)}
              <option value={o.value}>{o.label}</option>
            {/each}
          </select>
        </div>
        <div>
          <label for={`${idPrefix}-perm-target-code`} class={labelClass}>{t("initiative_detail_modal.perm_target", "Target")}</label>
          <select id={`${idPrefix}-perm-target-code`} bind:value={permCode} disabled={permCodeDisabled} class={fieldClass}>
            <option value="">{t("initiative_detail_modal.perm_choose_target", "— choose target —")}</option>
            {#each permCodeOptions as o (o.value)}
              <option value={o.value}>{o.label}</option>
            {/each}
          </select>
        </div>
        <div>
          <label for={`${idPrefix}-perm-access`} class={labelClass}>{t("initiative_detail_modal.perm_access", "Access level")}</label>
          <select id={`${idPrefix}-perm-access`} bind:value={permAccess} class={fieldClass}>
            <option value="">{t("initiative_detail_modal.perm_choose_access", "— choose access —")}</option>
            {#each accessOptions as o (o.value)}
              <option value={o.value}>{o.label}</option>
            {/each}
          </select>
        </div>
        <div class="md:col-span-3 flex justify-end">
          <button type="button" class={addBtnClass} onclick={addPermission}>{t("initiative_detail_modal.perm_add", "Add permission")}</button>
        </div>
      </div>
      {#if permError}
        <p class="mt-2 text-xs text-red-600 dark:text-red-400">{permError}</p>
      {/if}
    </section>
    <section>
      {#if stagedPermissions.length === 0}
        <div class={emptyClass}>{t("initiative_detail_modal.perm_empty", "No permissions yet.")}</div>
      {:else}
        <ul class="space-y-2">
          {#each stagedPermissions as p, idx (p.id ?? `${p.targetType}:${p.targetCode}:${p.access}`)}
            <li
              class={p.id == null ? `${rowClass} ring-2 ring-amber-400` : rowClass}
              data-pending={p.id == null ? "1" : undefined}
            >
              <span class="shrink-0 rounded-full bg-gray-100 px-2 py-0.5 text-[11px] font-semibold text-gray-600 dark:bg-gray-700 dark:text-gray-300">{p.targetTypeLabel || p.targetType}</span>
              <span class="min-w-0 flex-1 truncate text-sm font-semibold text-gray-800 dark:text-gray-200" title={p.targetCodeLabel}>{p.targetCodeLabel}</span>
              <span class="shrink-0 rounded-full bg-indigo-50 px-2 py-0.5 text-[11px] font-semibold text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300">{p.accessLabel || p.access}</span>
              <button type="button" class="shrink-0 rounded-md p-1 text-gray-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/30" title={t("initiative_detail_modal.perm_remove", "Revoke")} aria-label={t("initiative_detail_modal.perm_remove", "Revoke")} onclick={() => removePermission(idx)}>
                {@render removeIcon()}
              </button>
            </li>
          {/each}
        </ul>
      {/if}
    </section>
  </div>

  <!-- Discussion (interactive, like Edit Asset) — the Foro island loads the opened initiative's
       thread off the same [data-modal-open] trigger (data-init-id). -->
  <div data-tabpanel="discussion" role="tabpanel" class="pt-4" class:hidden={activeTab !== "discussion"}>
    <Foro modalId={idPrefix} api={initiativeForoApi} idAttr="initId" />
  </div>

  <!-- History (read-only) — hydrated by mountHistory from the parent .astro. -->
  <div data-tabpanel="history" role="tabpanel" class="pt-4" class:hidden={activeTab !== "history"}>
    <section id={`${idPrefix}-history`}>
      <p data-history-status class="hidden text-sm text-gray-400 dark:text-gray-500"></p>
      <div data-history-list></div>
    </section>
  </div>
</div>
