<script lang="ts">
  /**
   * AssetDetailTabs — the editable Characterizations / Related Assets /
   * Permissions tabs of the Asset Repository detail modal, as a Svelte island.
   * Fourth migration; replaces the heaviest hand-rolled controller so far
   * (lib/assetDetailTabs.ts, 944 lines of innerHTML/createElement + DOM-scraping
   * on flush) with a declarative component whose 3 staged collections are $state.
   *
   * Keeps the SAME imperative controller API the parent orchestrates: the
   * consumer (AssetDetailModal.astro) mounts this and calls the exported
   * `loadOptions` / `loadChars` / `hydrate` / `flush` / `reset` (+ `counts` /
   * `activateTab`) — Svelte 5 `mount()` returns a component's `export`s, so the
   * parent's save flow (`await tabs.flush(id)` after saving the asset core) is
   * unchanged. The diff-based flush algorithm is preserved byte-for-byte; it now
   * reads the reactive `charValues` state instead of scraping the DOM.
   *
   * Reuses the existing lib/* services unchanged and reads i18n via translate()
   * (not data-i18n). User content renders through Svelte escaping (no innerHTML).
   */
  import { onMount, untrack } from "svelte";
  import { getAsset, getAssetsSelect } from "@/lib/assets";
  import { getSpecificationsbyCategory } from "@/lib/specifications";
  import { getFeature } from "@/lib/features";
  import { getListItemsbyList } from "@/lib/list_items";
  import {
    getCharacterizationsByAsset,
    createCharacterization,
    updateCharacterization,
    deleteCharacterization,
  } from "@/lib/characterizations";
  import {
    getAssetRelationsBySource,
    createAssetRelation,
    updateAssetRelation,
    deleteAssetRelation,
  } from "@/lib/asset_relations";
  import {
    getAssetPermissionsByAsset,
    createAssetPermission,
    updateAssetPermission,
    deleteAssetPermission,
  } from "@/lib/asset_permissions";
  import { getUsersSelect } from "@/lib/users";
  import { getRolesSelect } from "@/lib/roles";
  import { getTeamsSelect } from "@/lib/teams";
  import { getBusinessUnitsSelect } from "@/lib/business_units";
  import { getProjectsSelect } from "@/lib/projects";
  import { translate } from "@/utils/i18nClient";
  import Foro from "@/components/svelte/Foro.svelte";

  // Editable tabs first, then the read-only view tabs (Discussion/History/
  // Versions) surfaced from the gallery detail modal — view, not edit.
  type TabName = "chars" | "related" | "permissions" | "discussion" | "history" | "versions";
  const READONLY_TABS: TabName[] = ["discussion", "history", "versions"];
  interface TabCounts {
    chars: number;
    related: number;
    permissions: number;
  }
  type SelectOption = { value: string; label: string };
  type StagedRelation = {
    target: number;
    targetLabel: string;
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
  interface EnrichedSpec {
    feature: string;
    default_value?: string;
    required?: boolean;
    featureObj: { code: string; name?: string; description?: string; type?: string; list?: string | null };
    listItems: any[] | null;
  }

  let {
    idPrefix,
    assetId = null,
    onError,
    onCountsChange,
    onTabChange,
  }: {
    idPrefix: string;
    mode?: "modal" | "inline";
    assetId?: number | null;
    onError?: (msg: string) => void;
    onCountsChange?: (counts: TabCounts) => void;
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
    (typeof localStorage !== "undefined" && localStorage.getItem("lang")) || "en";
  const langItems = (items: any[]): any[] => {
    const lang = currentLang();
    const byLang = items.filter((li) => li.lang === lang);
    return (byLang.length ? byLang : items.filter((li) => li.lang === "en")).sort(
      (a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0),
    );
  };
  const isConflict = (err: unknown): boolean =>
    err instanceof Error && /\(409\)/.test(err.message);

  // ── State ─────────────────────────────────────────────────────────────
  let rootEl = $state<HTMLElement | undefined>(undefined);
  let activeTab = $state<TabName>("chars");

  // Characterizations
  let loadedSpecs = $state<EnrichedSpec[]>([]);
  let charValues = $state<Record<string, string>>({});
  let charsLoading = $state(false);
  let initialCharByFeature = new Map<string, any>();

  // Relations
  let stagedRelations = $state<StagedRelation[]>([]);
  let initialRelByTarget = new Map<number, any>();
  let assetOptions = $state<SelectOption[]>([]);
  let relTypeOptions = $state<SelectOption[]>([]);
  let relTarget = $state("");
  let relType = $state("");
  let relRationale = $state("");
  let relError = $state("");

  // Permissions
  let stagedPermissions = $state<StagedPermission[]>([]);
  let initialPermById = new Map<number, any>();
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

  // Seed from the prop's initial value only (it never changes after mount);
  // reset() re-reads it inside a closure, which is fine.
  let editingAssetId = $state<number | null>(untrack(() => assetId));

  // Caches (plain — not rendered directly)
  const featureCache = new Map<string, any>();
  const listItemsCache = new Map<string, any[]>();
  const targetOptCache = new Map<string, SelectOption[]>();

  // ── Counts ────────────────────────────────────────────────────────────
  const countsObj = $derived<TabCounts>({
    chars: loadedSpecs.length,
    related: stagedRelations.length,
    permissions: stagedPermissions.length,
  });
  $effect(() => {
    onCountsChange?.(countsObj);
  });
  // Notify the parent (the .astro footer) which tab is active so it can show
  // the version picker + "Save new version" for chars only, and "Save
  // related"/"Save permissions" (no version bump) for the other two tabs.
  $effect(() => {
    onTabChange?.(activeTab);
  });
  export function counts(): TabCounts {
    return {
      chars: loadedSpecs.length,
      related: stagedRelations.length,
      permissions: stagedPermissions.length,
    };
  }

  const relTargetOptions = $derived(
    assetOptions.filter((a) => !editingAssetId || Number(a.value) !== editingAssetId),
  );

  // ── Tabs ──────────────────────────────────────────────────────────────
  export function activateTab(name: TabName): void {
    activeTab = name;
  }
  // The read-only view tabs only make sense for an existing asset — hidden in
  // create mode. Keyboard nav walks the currently-visible set.
  const tabOrder = $derived<TabName[]>(
    editingAssetId != null
      ? ["chars", "related", "permissions", "discussion", "history", "versions"]
      : ["chars", "related", "permissions"],
  );
  const tabClass = (name: TabName): string =>
    "whitespace-nowrap border-b-2 px-1 pb-3 " +
    (activeTab === name
      ? "border-indigo-600 text-indigo-600 dark:text-indigo-400"
      : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200");

  function onTabKeydown(e: KeyboardEvent): void {
    const order = tabOrder;
    const idx = order.indexOf(activeTab);
    if (idx < 0) return;
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

  // ── Characterizations ─────────────────────────────────────────────────
  export async function loadChars(categoryCode: string): Promise<void> {
    loadedSpecs = [];
    charValues = {};
    if (!categoryCode) {
      charsLoading = false;
      return;
    }
    charsLoading = true;
    let specs: any[] = [];
    try {
      specs = await getSpecificationsbyCategory(categoryCode);
    } catch {
      reportError(t("asset_detail_modal.error_specs", "Could not load specifications."));
      charsLoading = false;
      return;
    }

    const enriched: EnrichedSpec[] = await Promise.all(
      specs.map(async (s) => {
        let featureObj = featureCache.get(s.feature);
        if (!featureObj) {
          try {
            featureObj = await getFeature(s.feature);
            featureCache.set(s.feature, featureObj);
          } catch {
            featureObj = { code: s.feature, name: s.feature, list: null };
          }
        }
        let listItems: any[] | null = null;
        if (featureObj.list) {
          listItems = listItemsCache.get(featureObj.list) ?? null;
          if (!listItems) {
            try {
              listItems = await getListItemsbyList(featureObj.list);
              listItemsCache.set(featureObj.list, listItems);
            } catch {
              listItems = [];
            }
          }
        }
        return { ...s, featureObj, listItems };
      }),
    );

    const values: Record<string, string> = {};
    for (const spec of enriched) {
      const existing = initialCharByFeature.get(spec.feature);
      values[spec.feature] = existing?.value ?? spec.default_value ?? "";
    }
    loadedSpecs = enriched;
    charValues = values;
    charsLoading = false;
  }

  // ── Relations ─────────────────────────────────────────────────────────
  function addRelation(): void {
    relError = "";
    const target = Number(relTarget);
    const type = relType;
    if (!target || !type) {
      relError = t("asset_detail_modal.related_missing_fields", "Pick a target asset and a relation type.");
      return;
    }
    if (stagedRelations.some((r) => r.target === target)) {
      relError = t("asset_detail_modal.related_duplicate", "This asset is already related.");
      return;
    }
    stagedRelations = [
      ...stagedRelations,
      {
        target,
        targetLabel: relTargetOptions.find((a) => Number(a.value) === target)?.label || String(target),
        type,
        typeLabel: relTypeOptions.find((o) => o.value === type)?.label || type,
        rationale: relRationale.trim(),
      },
    ];
    relTarget = "";
    relType = "";
    relRationale = "";
  }
  function removeRelation(idx: number): void {
    stagedRelations = stagedRelations.filter((_, i) => i !== idx);
  }

  async function loadRelationOptions(): Promise<void> {
    try {
      assetOptions = await getAssetsSelect();
    } catch {
      assetOptions = [];
    }
    try {
      let items = listItemsCache.get("RELATION_TYPE");
      if (!items) {
        items = await getListItemsbyList("RELATION_TYPE");
        listItemsCache.set("RELATION_TYPE", items);
      }
      relTypeOptions = langItems(items).map((li) => ({ value: li.value, label: li.label || li.value }));
    } catch {
      relTypeOptions = [];
    }
  }

  // ── Permissions ───────────────────────────────────────────────────────
  function addPermission(): void {
    permError = "";
    const targetType = permType;
    const access = permAccess;
    if (!targetType || !access) {
      permError = t("asset_detail_modal.perm_missing_fields", "Pick a target type, target and access level.");
      return;
    }
    let targetCode: string;
    let targetCodeLabel: string;
    if (targetType === "PUBLIC") {
      targetCode = "PUBLIC";
      targetCodeLabel = t("asset_detail_modal.perm_public", "Public");
    } else {
      targetCode = permCode;
      if (!targetCode) {
        permError = t("asset_detail_modal.perm_missing_fields", "Pick a target type, target and access level.");
        return;
      }
      targetCodeLabel = permCodeOptions.find((o) => o.value === targetCode)?.label || targetCode;
    }
    if (stagedPermissions.some((p) => p.targetType === targetType && p.targetCode === targetCode)) {
      permError = t("asset_detail_modal.perm_duplicate", "This target already has a permission.");
      return;
    }
    stagedPermissions = [
      ...stagedPermissions,
      {
        targetType,
        targetTypeLabel: targetTypeOptions.find((o) => o.value === targetType)?.label || targetType,
        targetCode,
        targetCodeLabel,
        access,
        accessLabel: accessOptions.find((o) => o.value === access)?.label || access,
      },
    ];
    permType = "";
    permCode = "";
    permCodeOptions = [];
    permAccess = "";
  }
  function removePermission(idx: number): void {
    stagedPermissions = stagedPermissions.filter((_, i) => i !== idx);
  }

  // Populate the target_code dropdown for the chosen target type.
  async function onPermTypeChange(): Promise<void> {
    permCode = "";
    permCodeOptions = [];
    const targetType = permType;
    if (!targetType || targetType === "PUBLIC") {
      permCodeDisabled = targetType === "PUBLIC";
      return;
    }
    permCodeDisabled = false;
    const loader = TARGET_LOADERS[targetType];
    if (!loader) return;
    let optList = targetOptCache.get(targetType);
    if (!optList) {
      try {
        optList = await loader();
      } catch {
        optList = [];
      }
      targetOptCache.set(targetType, optList);
    }
    permCodeOptions = optList;
  }

  async function loadPermissionOptions(): Promise<void> {
    try {
      let items = listItemsCache.get("TARGET_TYPE");
      if (!items) {
        items = await getListItemsbyList("TARGET_TYPE");
        listItemsCache.set("TARGET_TYPE", items);
      }
      const li = langItems(items);
      targetTypeOptions = li.map((x) => ({ value: x.value, label: x.label || x.value }));
      targetTypeLabels = new Map(li.map((x) => [x.value, x.label || x.value]));
    } catch {
      targetTypeOptions = [];
    }
    try {
      let items = listItemsCache.get("ACCESS_LEVEL");
      if (!items) {
        items = await getListItemsbyList("ACCESS_LEVEL");
        listItemsCache.set("ACCESS_LEVEL", items);
      }
      const li = langItems(items);
      accessOptions = li.map((x) => ({ value: x.value, label: x.label || x.value }));
      accessLabels = new Map(li.map((x) => [x.value, x.label || x.value]));
    } catch {
      accessOptions = [];
    }
  }

  // Resolve a hydrated permission's target_code → friendly label (cached).
  async function resolveTargetLabel(targetType: string, targetCode: string): Promise<string> {
    if (targetType === "PUBLIC") return t("asset_detail_modal.perm_public", "Public");
    const loader = TARGET_LOADERS[targetType];
    if (!loader) return targetCode;
    let optList = targetOptCache.get(targetType);
    if (!optList) {
      try {
        optList = await loader();
      } catch {
        optList = [];
      }
      targetOptCache.set(targetType, optList);
    }
    return optList.find((o) => o.value === targetCode)?.label || targetCode;
  }

  // ── options / hydrate / flush / reset ─────────────────────────────────
  export async function loadOptions(): Promise<void> {
    await Promise.all([loadRelationOptions(), loadPermissionOptions()]);
  }

  export async function hydrate(id: number, category?: string): Promise<void> {
    editingAssetId = id;
    await loadOptions();

    let cat = category;
    const [chars, relations, permissions] = await Promise.all([
      getCharacterizationsByAsset(id).catch(() => [] as any[]),
      getAssetRelationsBySource(id).catch(() => {
        reportError(t("asset_detail_modal.error_relations", "Could not load related assets."));
        return [] as any[];
      }),
      getAssetPermissionsByAsset(id).catch(() => {
        reportError(t("asset_detail_modal.error_permissions", "Could not load permissions."));
        return [] as any[];
      }),
    ]);

    if (cat === undefined) {
      try {
        cat = (await getAsset(id)).category ?? "";
      } catch {
        cat = "";
      }
    }

    // Relations
    initialRelByTarget = new Map(relations.map((r: any) => [r.target, r]));
    stagedRelations = relations.map((r: any) => ({
      target: r.target,
      targetLabel: assetOptions.find((a) => Number(a.value) === r.target)?.label || String(r.target),
      type: r.type,
      typeLabel: relTypeOptions.find((o) => o.value === r.type)?.label || r.type,
      rationale: r.rationale ?? "",
    }));

    // Permissions
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

    // Characterizations
    initialCharByFeature = new Map(chars.map((c: any) => [c.feature, c]));
    await loadChars(cat ?? "");
  }

  /** The staged characterization set (feature → trimmed value, blanks
   * omitted = deletes) — what a version save sends as `values` so the server
   * snapshots the whole set atomically instead of this component flushing
   * per-row (see AssetDetailModal's edit-mode save). */
  export function charSnapshot(): Record<string, string> {
    const snapshot: Record<string, string> = {};
    for (const spec of loadedSpecs) {
      const value = (charValues[spec.feature] ?? "").trim();
      if (value) snapshot[spec.feature] = value;
    }
    return snapshot;
  }

  export async function flush(
    id: number,
    opts?: { skipChars?: boolean; skipRelations?: boolean; skipPermissions?: boolean },
  ): Promise<void> {
    // Each slice is independently skippable so the modal can save one tab at a
    // time: chars save = version bump (chars snapshotted server-side, so
    // skipChars here); a "Save related" / "Save permissions" flush touches only
    // its own slice and never versions.
    // 1. Characterizations.
    if (!opts?.skipChars) {
      for (const spec of loadedSpecs) {
        const featureCode = spec.feature;
        const newValue = (charValues[featureCode] ?? "").trim();
        const existing = initialCharByFeature.get(featureCode);
        if (!newValue) {
          if (existing) {
            try {
              await deleteCharacterization(id, featureCode);
            } catch {
              /* already gone */
            }
          }
          continue;
        }
        if (existing) {
          if (existing.value !== newValue) {
            await updateCharacterization(id, featureCode, { value: newValue });
          }
        } else {
          await createCharacterization({ asset: id, feature: featureCode, value: newValue });
        }
      }
    }

    // 2. Relations (deletes first → re-add hits 409 → reactivate)
    if (!opts?.skipRelations) {
      const stagedTargets = new Set(stagedRelations.map((r) => r.target));
      for (const [target] of initialRelByTarget) {
        if (!stagedTargets.has(target)) {
          try {
            await deleteAssetRelation(id, target);
          } catch {
            /* already gone */
          }
        }
      }
      for (const rel of stagedRelations) {
        const initial = initialRelByTarget.get(rel.target);
        if (!initial) {
          try {
            await createAssetRelation({ source: id, target: rel.target, type: rel.type, rationale: rel.rationale || undefined });
          } catch {
            await updateAssetRelation(id, rel.target, { type: rel.type, rationale: rel.rationale || null, is_active: true });
          }
        } else if (initial.type !== rel.type || (initial.rationale ?? "") !== rel.rationale) {
          await updateAssetRelation(id, rel.target, { type: rel.type, rationale: rel.rationale || null });
        }
      }
    }

    // 3. Permissions (surrogate-id keyed)
    if (!opts?.skipPermissions) {
      const stagedIds = new Set(stagedPermissions.filter((p) => p.id != null).map((p) => p.id));
      for (const [pid] of initialPermById) {
        if (!stagedIds.has(pid)) {
          try {
            await deleteAssetPermission(pid);
          } catch {
            /* already gone */
          }
        }
      }
      for (const p of stagedPermissions) {
        if (p.id == null) {
          try {
            const created = await createAssetPermission({
              asset: id,
              target_type: p.targetType,
              target_code: p.targetCode,
              access_level: p.access,
            });
            p.id = created.id;
          } catch (err) {
            if (!isConflict(err)) throw err; // 409 = identical active grant already exists → skip
          }
        } else {
          const init = initialPermById.get(p.id);
          if (init && (init.target_type !== p.targetType || init.target_code !== p.targetCode || init.access_level !== p.access)) {
            await updateAssetPermission(p.id, { target_type: p.targetType, target_code: p.targetCode, access_level: p.access });
          }
        }
      }
    }

    // Re-seed the initial maps of the slices we actually persisted so a second
    // flush (no reload) diffs against the new baseline. Skipped slices keep
    // their old baseline (they weren't written this call).
    if (!opts?.skipChars) {
      const charSeed: [string, any][] = [];
      for (const s of loadedSpecs) {
        const v = (charValues[s.feature] ?? "").trim();
        if (v) charSeed.push([s.feature, { feature: s.feature, value: v }]);
      }
      initialCharByFeature = new Map(charSeed);
    }
    if (!opts?.skipRelations) {
      initialRelByTarget = new Map(
        stagedRelations.map((r) => [r.target, { target: r.target, type: r.type, rationale: r.rationale }]),
      );
    }
    if (!opts?.skipPermissions) {
      initialPermById = new Map(
        stagedPermissions
          .filter((p) => p.id != null)
          .map((p) => [p.id as number, { target_type: p.targetType, target_code: p.targetCode, access_level: p.access }]),
      );
    }
  }

  export function reset(): void {
    editingAssetId = assetId;
    loadedSpecs = [];
    charValues = {};
    charsLoading = false;
    initialCharByFeature = new Map();
    stagedRelations = [];
    initialRelByTarget = new Map();
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
    activeTab = "chars";
  }

  onMount(() => {
    const onLang = () => (langTick += 1);
    window.addEventListener("languageChanged", onLang);

    // Native constraint validation can't focus a control inside a hidden panel:
    // flip to the owning tab first. (No tab control is required today, so this is
    // defensive parity with the vanilla widget.)
    const form = rootEl?.closest("form");
    const onInvalid = (e: Event) => {
      const panel = (e.target as HTMLElement).closest?.("[data-tabpanel]") as HTMLElement | null;
      if (panel?.dataset.tabpanel && panel.classList.contains("hidden")) {
        activeTab = panel.dataset.tabpanel as TabName;
      }
    };
    form?.addEventListener("invalid", onInvalid, true);

    return () => {
      window.removeEventListener("languageChanged", onLang);
      form?.removeEventListener("invalid", onInvalid, true);
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
</script>

<div bind:this={rootEl}>
  <!-- Tabs header -->
  <div class="border-b border-gray-200 dark:border-gray-800">
    <div role="tablist" aria-label="Asset detail sections" class="-mb-px flex flex-nowrap gap-4 overflow-x-auto no-scrollbar text-sm font-medium sm:gap-6">
      <button
        type="button"
        role="tab"
        data-tab="chars"
        aria-selected={activeTab === "chars"}
        tabindex={activeTab === "chars" ? 0 : -1}
        class={tabClass("chars")}
        onclick={() => (activeTab = "chars")}
        onkeydown={(e) => onTabKeydown(e)}
      >
        <span>{t("asset_detail_modal.characterizations_section", "Characterization")}</span>
        {#if loadedSpecs.length > 0}
          <span class="ml-1 rounded-full bg-gray-100 px-1.5 py-0.5 text-[10px] font-semibold text-gray-600 dark:bg-gray-700 dark:text-gray-300">{loadedSpecs.length}</span>
        {/if}
      </button>
      <button
        type="button"
        role="tab"
        data-tab="related"
        aria-selected={activeTab === "related"}
        tabindex={activeTab === "related" ? 0 : -1}
        class={tabClass("related")}
        onclick={() => (activeTab = "related")}
        onkeydown={(e) => onTabKeydown(e)}
      >
        <span>{t("asset_detail_modal.tab_related", "Related Assets")}</span>
        {#if stagedRelations.length > 0}
          <span class="ml-1 rounded-full bg-indigo-100 px-1.5 py-0.5 text-[10px] font-semibold text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300">{stagedRelations.length}</span>
        {/if}
      </button>
      <button
        type="button"
        role="tab"
        data-tab="permissions"
        aria-selected={activeTab === "permissions"}
        tabindex={activeTab === "permissions" ? 0 : -1}
        class={tabClass("permissions")}
        onclick={() => (activeTab = "permissions")}
        onkeydown={(e) => onTabKeydown(e)}
      >
        <span>{t("asset_detail_modal.tab_permissions", "Permissions")}</span>
        {#if stagedPermissions.length > 0}
          <span class="ml-1 rounded-full bg-indigo-100 px-1.5 py-0.5 text-[10px] font-semibold text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300">{stagedPermissions.length}</span>
        {/if}
      </button>
      <!-- Read-only view tabs (Discussion / History / Versions) — only for an
           existing asset (nothing to view while creating). View, not edit. -->
      {#if editingAssetId != null}
        <button
          type="button"
          role="tab"
          data-tab="discussion"
          aria-selected={activeTab === "discussion"}
          tabindex={activeTab === "discussion" ? 0 : -1}
          class={tabClass("discussion")}
          onclick={() => (activeTab = "discussion")}
          onkeydown={(e) => onTabKeydown(e)}
        >
          <span>{t("asset_detail_modal.tab_discussion", "Discussion")}</span>
        </button>
        <button
          type="button"
          role="tab"
          data-tab="history"
          aria-selected={activeTab === "history"}
          tabindex={activeTab === "history" ? 0 : -1}
          class={tabClass("history")}
          onclick={() => (activeTab = "history")}
          onkeydown={(e) => onTabKeydown(e)}
        >
          <span>{t("asset_detail_modal.tab_history", "History")}</span>
        </button>
        <button
          type="button"
          role="tab"
          data-tab="versions"
          aria-selected={activeTab === "versions"}
          tabindex={activeTab === "versions" ? 0 : -1}
          class={tabClass("versions")}
          onclick={() => (activeTab = "versions")}
          onkeydown={(e) => onTabKeydown(e)}
        >
          <span>{t("asset_detail_modal.tab_versions", "Versions")}</span>
        </button>
      {/if}
    </div>
  </div>

  <!-- Characterizations panel -->
  <div data-tabpanel="chars" role="tabpanel" class="pt-4" class:hidden={activeTab !== "chars"}>
    {#if charsLoading}
      <div class="text-sm text-gray-400">{t("common.loading", "Loading…")}</div>
    {:else if loadedSpecs.length === 0}
      <div class={emptyClass}>
        {t("asset_detail_modal.characterizations_empty", "Select a category to load the required features.")}
      </div>
    {:else}
      <div class="space-y-4">
        {#each loadedSpecs as spec (spec.feature)}
          <div class="rounded-lg border border-gray-200 dark:border-gray-800 bg-gray-50/50 dark:bg-white/[0.02] p-3">
            <div class="flex flex-wrap items-baseline justify-between gap-x-2 mb-1.5">
              <label class="block min-w-0 break-words text-sm font-semibold text-gray-800 dark:text-gray-200" for={`${idPrefix}-char-${spec.feature}`}>
                {t(`features.${spec.feature}`, spec.featureObj.name || spec.feature)}{#if spec.required}<span class="ml-0.5 text-red-500" aria-hidden="true">*</span>{/if}
              </label>
              <span class="shrink-0 text-[10px] uppercase tracking-wide text-gray-400">{spec.featureObj.type || ""}</span>
            </div>
            {#if spec.featureObj.description}
              <p class="mb-2 text-xs text-gray-500 dark:text-gray-400 break-words">{spec.featureObj.description}</p>
            {/if}
            {#if spec.listItems && spec.listItems.length > 0}
              <select id={`${idPrefix}-char-${spec.feature}`} bind:value={charValues[spec.feature]} class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 dark:border-gray-700 dark:bg-gray-800 dark:text-white">
                <option value="">—</option>
                {#each langItems(spec.listItems) as li (li.value)}
                  <option value={li.value}>{li.label || li.value}</option>
                {/each}
              </select>
            {:else}
              <textarea id={`${idPrefix}-char-${spec.feature}`} bind:value={charValues[spec.feature]} rows="2" class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 dark:border-gray-700 dark:bg-gray-800 dark:text-white"></textarea>
            {/if}
          </div>
        {/each}
      </div>
    {/if}
  </div>

  <!-- Related Assets panel -->
  <div data-tabpanel="related" role="tabpanel" class="pt-4 space-y-4" class:hidden={activeTab !== "related"}>
    <section>
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div>
          <label for={`${idPrefix}-rel-target`} class={labelClass}>{t("asset_detail_modal.related_target", "Target asset")}</label>
          <select id={`${idPrefix}-rel-target`} bind:value={relTarget} class={fieldClass}>
            <option value="">{t("asset_detail_modal.related_choose_asset", "— choose asset —")}</option>
            {#each relTargetOptions as a (a.value)}
              <option value={a.value}>{a.label}</option>
            {/each}
          </select>
        </div>
        <div>
          <label for={`${idPrefix}-rel-type`} class={labelClass}>{t("asset_detail_modal.related_type", "Relation type")}</label>
          <select id={`${idPrefix}-rel-type`} bind:value={relType} class={fieldClass}>
            <option value="">{t("asset_detail_modal.related_choose_type", "— choose type —")}</option>
            {#each relTypeOptions as o (o.value)}
              <option value={o.value}>{o.label}</option>
            {/each}
          </select>
        </div>
        <div class="md:col-span-2">
          <label for={`${idPrefix}-rel-rationale`} class={labelClass}>{t("asset_detail_modal.related_rationale", "Rationale")}</label>
          <div class="flex gap-2">
            <input id={`${idPrefix}-rel-rationale`} type="text" bind:value={relRationale} placeholder={t("asset_detail_modal.related_rationale_placeholder", "Why are these related? (optional)")} class="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 dark:border-gray-700 dark:bg-gray-800 dark:text-white" />
            <button type="button" class={addBtnClass} onclick={addRelation}>{t("asset_detail_modal.related_add", "Add relation")}</button>
          </div>
        </div>
      </div>
      {#if relError}
        <p class="mt-2 text-xs text-red-600 dark:text-red-400">{relError}</p>
      {/if}
    </section>
    <section>
      {#if stagedRelations.length === 0}
        <div class={emptyClass}>{t("asset_detail_modal.related_empty", "No related assets yet.")}</div>
      {:else}
        <ul class="space-y-2">
          {#each stagedRelations as rel, idx (rel.target)}
            <li class={rowClass}>
              <span class="min-w-0 flex-1 truncate text-sm font-semibold text-gray-800 dark:text-gray-200" title={rel.targetLabel}>{rel.targetLabel}</span>
              <span class="shrink-0 rounded-full bg-indigo-50 px-2 py-0.5 text-[11px] font-semibold text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300">{rel.typeLabel || rel.type}</span>
              {#if rel.rationale}
                <span class="hidden md:block max-w-[200px] truncate text-xs text-gray-500 dark:text-gray-400" title={rel.rationale}>{rel.rationale}</span>
              {/if}
              <button type="button" class="shrink-0 rounded-md p-1 text-gray-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/30" title={t("asset_detail_modal.related_remove", "Remove")} onclick={() => removeRelation(idx)} aria-label={t("asset_detail_modal.related_remove", "Remove")}>
                <svg class="w-4 h-4" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" /></svg>
              </button>
            </li>
          {/each}
        </ul>
      {/if}
    </section>
  </div>

  <!-- Permissions panel -->
  <div data-tabpanel="permissions" role="tabpanel" class="pt-4 space-y-4" class:hidden={activeTab !== "permissions"}>
    <section>
      <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
        <div>
          <label for={`${idPrefix}-perm-target-type`} class={labelClass}>{t("asset_detail_modal.perm_target_type", "Target type")}</label>
          <select id={`${idPrefix}-perm-target-type`} bind:value={permType} onchange={onPermTypeChange} class={fieldClass}>
            <option value="">{t("asset_detail_modal.perm_choose_target_type", "— choose type —")}</option>
            {#each targetTypeOptions as o (o.value)}
              <option value={o.value}>{o.label}</option>
            {/each}
          </select>
        </div>
        <div>
          <label for={`${idPrefix}-perm-target-code`} class={labelClass}>{t("asset_detail_modal.perm_target", "Target")}</label>
          <select id={`${idPrefix}-perm-target-code`} bind:value={permCode} disabled={permCodeDisabled} class={fieldClass}>
            <option value="">{t("asset_detail_modal.perm_choose_target", "— choose target —")}</option>
            {#each permCodeOptions as o (o.value)}
              <option value={o.value}>{o.label}</option>
            {/each}
          </select>
        </div>
        <div>
          <label for={`${idPrefix}-perm-access`} class={labelClass}>{t("asset_detail_modal.perm_access", "Access level")}</label>
          <div class="flex gap-2">
            <select id={`${idPrefix}-perm-access`} bind:value={permAccess} class="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 dark:border-gray-700 dark:bg-gray-800 dark:text-white">
              <option value="">{t("asset_detail_modal.perm_choose_access", "— choose access —")}</option>
              {#each accessOptions as o (o.value)}
                <option value={o.value}>{o.label}</option>
              {/each}
            </select>
          </div>
        </div>
        <div class="md:col-span-3 flex justify-end">
          <button type="button" class={addBtnClass} onclick={addPermission}>{t("asset_detail_modal.perm_add", "Add permission")}</button>
        </div>
      </div>
      {#if permError}
        <p class="mt-2 text-xs text-red-600 dark:text-red-400">{permError}</p>
      {/if}
    </section>
    <section>
      {#if stagedPermissions.length === 0}
        <div class={emptyClass}>{t("asset_detail_modal.perm_empty", "No permissions yet.")}</div>
      {:else}
        <ul class="space-y-2">
          {#each stagedPermissions as p, idx (p.id ?? `${p.targetType}:${p.targetCode}`)}
            <li class={rowClass}>
              <span class="shrink-0 rounded-full bg-gray-100 px-2 py-0.5 text-[11px] font-semibold text-gray-600 dark:bg-gray-700 dark:text-gray-300">{p.targetTypeLabel || p.targetType}</span>
              <span class="min-w-0 flex-1 truncate text-sm font-semibold text-gray-800 dark:text-gray-200" title={p.targetCodeLabel}>{p.targetCodeLabel}</span>
              <span class="shrink-0 rounded-full bg-indigo-50 px-2 py-0.5 text-[11px] font-semibold text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300">{p.accessLabel || p.access}</span>
              <button type="button" class="shrink-0 rounded-md p-1 text-gray-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/30" title={t("asset_detail_modal.perm_remove", "Remove")} onclick={() => removePermission(idx)} aria-label={t("asset_detail_modal.perm_remove", "Remove")}>
                <svg class="w-4 h-4" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" /></svg>
              </button>
            </li>
          {/each}
        </ul>
      {/if}
    </section>
  </div>

  <!-- Discussion panel (read-only) — the Foro island self-loads the opened
       asset's thread off the same [data-modal-open] trigger. -->
  <div data-tabpanel="discussion" role="tabpanel" class="pt-4" class:hidden={activeTab !== "discussion"}>
    <Foro modalId={idPrefix} readonly />
  </div>

  <!-- History panel (read-only) — hydrated by mountHistory (lib/history.ts),
       wired from AssetDetailModal.astro; shell ids scoped by idPrefix. -->
  <div data-tabpanel="history" role="tabpanel" class="pt-4" class:hidden={activeTab !== "history"}>
    <section id={`${idPrefix}-history`}>
      <p data-history-status class="hidden text-sm text-gray-400 dark:text-gray-500"></p>
      <div data-history-list></div>
    </section>
  </div>

  <!-- Versions panel (read-only) — hydrated by mountVersions (lib/versions.ts),
       wired from AssetDetailModal.astro with the all-category section set. -->
  <div data-tabpanel="versions" role="tabpanel" class="pt-4" class:hidden={activeTab !== "versions"}>
    <section id={`${idPrefix}-versions`}>
      <p data-versions-status class="hidden text-sm text-gray-400 dark:text-gray-500"></p>
      <div data-versions-list class="space-y-2"></div>
    </section>
  </div>
</div>
