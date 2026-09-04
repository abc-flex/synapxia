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
    getAssetInitsByAsset,
    createAssetInit,
    updateAssetInit,
    deleteAssetInit,
  } from "@/lib/asset_inits";
  import { getInitiativesSelect } from "@/lib/initiatives";
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

  // "core" (the asset's core fields, hydrated/saved by the parent .astro — see
  // the empty-shell panel below) comes first, then the editable collections,
  // then the tabs surfaced from the gallery detail modal: Discussion is fully
  // interactive (same Foro island, same as Explore/gallery browsing), while
  // History/Versions stay read-only view tabs.
  type TabName = "core" | "chars" | "related" | "related_inits" | "permissions" | "discussion" | "history" | "versions";
  const READONLY_TABS: TabName[] = ["history", "versions"];
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
  type StagedInit = {
    init: number;
    initLabel: string;
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
  let activeTab = $state<TabName>("core");

  // Characterizations
  let loadedSpecs = $state<EnrichedSpec[]>([]);
  let charValues = $state<Record<string, string>>({});
  // Optional free-text elaboration per feature, additional to `value` (DB
  // column `detail`). Hidden by default per field — revealed via the
  // "+ Add detail" disclosure button — and auto-expanded on load when a
  // value already exists, so existing content is never silently hidden.
  let charDetails = $state<Record<string, string>>({});
  let charDetailExpanded = $state<Record<string, boolean>>({});
  let charsLoading = $state(false);
  // $state (not a plain let): reassigned wholesale by hydrate()/flush()/
  // commitCharsBaseline() to reseed the dirty-check baseline — needs to be
  // reactive so charsDirty()/charChanged (and the tab dot) actually notice
  // the reseed instead of holding onto a stale pre-save computation.
  let initialCharByFeature = $state(new Map<string, any>());
  // Feature → true while its required value is missing (set by validateChars,
  // cleared as soon as the user edits that field).
  let charInvalid = $state<Record<string, boolean>>({});

  // Relations
  let stagedRelations = $state<StagedRelation[]>([]);
  let initialRelByTarget = $state(new Map<number, any>());
  let assetOptions = $state<SelectOption[]>([]);
  let relTypeOptions = $state<SelectOption[]>([]);
  let relTarget = $state("");
  let relType = $state("");
  let relRationale = $state("");
  let relError = $state("");

  // Related Inits — same shape as Relations, but the target is an initiative
  // (asset_inits table) instead of another asset. Reuses relTypeOptions (both
  // tables share the RELATION_TYPE list).
  let stagedInits = $state<StagedInit[]>([]);
  let initialInitByInit = $state(new Map<number, any>());
  let initOptions = $state<SelectOption[]>([]);
  let initTarget = $state("");
  let initType = $state("");
  let initRationale = $state("");
  let initError = $state("");

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

  // Core Fields lives in the parent .astro (plain DOM inputs, re-parented
  // into the "core" panel below) — it reports its own dirty state here via
  // setCoreDirty() so the tab strip's pending-changes dot stays accurate.
  let coreDirty = $state(false);
  export function setCoreDirty(dirty: boolean): void {
    coreDirty = dirty;
  }

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

  // ── Pending-changes indicators ──────────────────────────────────────────
  // Live diff against each slice's last-hydrated/flushed baseline — feeds the
  // tab strip's "unsaved" dot and the per-item amber highlight the "Keep
  // editing" flow (AssetDetailModal.astro) jumps to. Fully derived, so it
  // self-clears the moment a slice's baseline is reseeded by flush()/
  // commitCharsBaseline() — no manual bookkeeping needed.
  const charChanged = $derived.by(() => {
    const set = new Set<string>();
    for (const spec of loadedSpecs) {
      const initial = initialCharByFeature.get(spec.feature);
      const initialValue = initial?.value ?? "";
      const initialDetail = initial?.detail ?? "";
      if ((charValues[spec.feature] ?? "").trim() !== initialValue) set.add(spec.feature);
      else if ((charDetails[spec.feature] ?? "").trim() !== initialDetail) set.add(spec.feature);
    }
    return set;
  });
  const pendingRelationTargets = $derived.by(() => {
    const set = new Set<number>();
    for (const rel of stagedRelations) {
      const initial = initialRelByTarget.get(rel.target);
      if (!initial || initial.type !== rel.type || (initial.rationale ?? "") !== rel.rationale) set.add(rel.target);
    }
    return set;
  });
  const pendingInitIds = $derived.by(() => {
    const set = new Set<number>();
    for (const rel of stagedInits) {
      const initial = initialInitByInit.get(rel.init);
      if (!initial || initial.type !== rel.type || (initial.rationale ?? "") !== rel.rationale) set.add(rel.init);
    }
    return set;
  });
  const permPendingKey = (p: StagedPermission): string => (p.id != null ? String(p.id) : `${p.targetType}:${p.targetCode}`);
  const pendingPermissionKeys = $derived.by(() => {
    const set = new Set<string>();
    for (const p of stagedPermissions) {
      const initial = p.id != null ? initialPermById.get(p.id) : null;
      if (!initial || initial.target_type !== p.targetType || initial.target_code !== p.targetCode || initial.access_level !== p.access) {
        set.add(permPendingKey(p));
      }
    }
    return set;
  });
  // Tab-dot indicator: reuses the same charsDirty()/relationsDirty()/
  // initsDirty()/permissionsDirty() the save flow already relies on (defined
  // below, hoisted) rather than re-deriving from the pending-row sets above —
  // those only see rows still present in the staged list, so they miss a
  // pending REMOVAL (the row is simply gone, nothing left to flag), while
  // e.g. relationsDirty() also checks for a baseline entry with no staged
  // counterpart.
  const tabDirty = $derived<Partial<Record<TabName, boolean>>>({
    core: coreDirty,
    chars: charsDirty(),
    related: relationsDirty(),
    related_inits: initsDirty(),
    permissions: permissionsDirty(),
  });

  // ── Tabs ──────────────────────────────────────────────────────────────
  export function activateTab(name: TabName): void {
    activeTab = name;
  }

  /** Called right after activateTab() lands on a tab with pending changes
   * (the "Keep editing" flow) — focuses/scrolls to the first item that
   * differs from its saved baseline so the highlight is easy to find. Core
   * Fields is handled by the parent .astro itself (its inputs aren't in this
   * component). */
  export function focusFirstPending(): void {
    if (activeTab === "chars") {
      const feature = loadedSpecs.find((s) => charChanged.has(s.feature))?.feature;
      if (feature) rootEl?.querySelector<HTMLElement>(`#${idPrefix}-char-${feature}`)?.focus();
    } else if (activeTab === "related" || activeTab === "related_inits" || activeTab === "permissions") {
      rootEl
        ?.querySelector<HTMLElement>(`[data-tabpanel="${activeTab}"] [data-pending="1"]`)
        ?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }
  // The read-only view tabs only make sense for an existing asset — hidden in
  // create mode. Keyboard nav walks the currently-visible set.
  const tabOrder = $derived<TabName[]>(
    editingAssetId != null
      ? ["core", "chars", "related", "related_inits", "permissions", "discussion", "history", "versions"]
      : ["core", "chars", "related", "related_inits", "permissions"],
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
    charDetails = {};
    charDetailExpanded = {};
    charInvalid = {};
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
    const details: Record<string, string> = {};
    for (const spec of enriched) {
      const existing = initialCharByFeature.get(spec.feature);
      values[spec.feature] = existing?.value ?? spec.default_value ?? "";
      details[spec.feature] = existing?.detail ?? "";
    }
    loadedSpecs = enriched;
    charValues = values;
    charDetails = details;
    // Always start collapsed — even for features that already carry a
    // detail — so the panel stays visually light by default; the toggle's
    // icon/label reflect the (always-false) initial state.
    charDetailExpanded = {};
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

  // ── Related Inits ─────────────────────────────────────────────────────
  function addInit(): void {
    initError = "";
    const init = Number(initTarget);
    const type = initType;
    if (!init || !type) {
      initError = t("asset_detail_modal.related_inits_missing_fields", "Pick a target initiative and a relation type.");
      return;
    }
    if (stagedInits.some((r) => r.init === init)) {
      initError = t("asset_detail_modal.related_inits_duplicate", "This initiative is already related.");
      return;
    }
    stagedInits = [
      ...stagedInits,
      {
        init,
        initLabel: initOptions.find((o) => Number(o.value) === init)?.label || String(init),
        type,
        typeLabel: relTypeOptions.find((o) => o.value === type)?.label || type,
        rationale: initRationale.trim(),
      },
    ];
    initTarget = "";
    initType = "";
    initRationale = "";
  }
  function removeInit(idx: number): void {
    stagedInits = stagedInits.filter((_, i) => i !== idx);
  }

  async function loadInitOptions(): Promise<void> {
    try {
      initOptions = await getInitiativesSelect();
    } catch {
      initOptions = [];
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
    await Promise.all([loadRelationOptions(), loadPermissionOptions(), loadInitOptions()]);
  }

  export async function hydrate(id: number, category?: string): Promise<void> {
    editingAssetId = id;
    await loadOptions();

    let cat = category;
    const [chars, relations, inits, permissions] = await Promise.all([
      getCharacterizationsByAsset(id).catch(() => [] as any[]),
      getAssetRelationsBySource(id).catch(() => {
        reportError(t("asset_detail_modal.error_relations", "Could not load related assets."));
        return [] as any[];
      }),
      getAssetInitsByAsset(id).catch(() => {
        reportError(t("asset_detail_modal.error_inits", "Could not load related initiatives."));
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

    // Related Inits
    initialInitByInit = new Map(inits.map((r: any) => [r.init, r]));
    stagedInits = inits.map((r: any) => ({
      init: r.init,
      initLabel: initOptions.find((o) => Number(o.value) === r.init)?.label || String(r.init),
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

  /** Companion to `charSnapshot()` for the `detail` column — sent alongside
   * `values` on a version save so a detail-only edit (no value change)
   * still reaches the server. A blank entry means "no detail" for that
   * feature (the server clears it), mirroring how a blank `value` entry
   * means "not carried forward". */
  export function charDetailSnapshot(): Record<string, string> {
    const snapshot: Record<string, string> = {};
    for (const spec of loadedSpecs) {
      snapshot[spec.feature] = (charDetails[spec.feature] ?? "").trim();
    }
    return snapshot;
  }

  /** Marks every required-but-empty characterization field invalid (red
   * border) and returns whether the set is save-worthy. Mirrors the Propose
   * page's required-spec gate (`specifications.required`) so a version save
   * can't silently drop a required feature the same way an omitted-optional
   * one is dropped by `charSnapshot()`. */
  export function validateChars(): boolean {
    const invalid: Record<string, boolean> = {};
    let firstBad: string | null = null;
    for (const spec of loadedSpecs) {
      if (!spec.required) continue;
      const bad = !(charValues[spec.feature] ?? "").trim();
      invalid[spec.feature] = bad;
      if (bad && !firstBad) firstBad = spec.feature;
    }
    charInvalid = invalid;
    if (firstBad) {
      rootEl
        ?.querySelector<HTMLElement>(`#${idPrefix}-char-${firstBad}`)
        ?.focus();
      return false;
    }
    return true;
  }

  /** Re-seeds the characterizations baseline from the currently staged
   * values — call after a successful version save (which persists via
   * `createAssetVersion` directly, bypassing `flush()`'s own reseed) so
   * `charsDirty()` reports clean again instead of comparing against the
   * pre-save snapshot forever. */
  export function commitCharsBaseline(): void {
    const seed: [string, any][] = [];
    for (const spec of loadedSpecs) {
      const value = (charValues[spec.feature] ?? "").trim();
      const detail = (charDetails[spec.feature] ?? "").trim();
      if (value) seed.push([spec.feature, { feature: spec.feature, value, detail }]);
    }
    initialCharByFeature = new Map(seed);
  }

  /** Whether the staged characterization set differs from what was last
   * hydrated/flushed — mirrors `charSnapshot()` vs `initialCharByFeature`, the
   * same comparison a version save would act on. Lets the parent skip an
   * empty "Save new version" (a no-op save shouldn't still bump the version). */
  export function charsDirty(): boolean {
    const current = charSnapshot();
    const initial: Record<string, string> = {};
    for (const [feature, c] of initialCharByFeature) {
      if (c?.value) initial[feature] = c.value;
    }
    const keys = new Set([...Object.keys(current), ...Object.keys(initial)]);
    for (const k of keys) {
      if ((current[k] ?? "") !== (initial[k] ?? "")) return true;
    }
    // A detail-only edit (value unchanged) is still a pending change.
    for (const spec of loadedSpecs) {
      const initialDetail = initialCharByFeature.get(spec.feature)?.detail ?? "";
      if ((charDetails[spec.feature] ?? "").trim() !== initialDetail) return true;
    }
    return false;
  }

  /** Whether the staged relations differ from the last hydrated/flushed
   * baseline — same diff `flush()` would act on, without performing it. */
  export function relationsDirty(): boolean {
    const stagedTargets = new Set(stagedRelations.map((r) => r.target));
    for (const [target] of initialRelByTarget) {
      if (!stagedTargets.has(target)) return true; // a pending delete
    }
    for (const rel of stagedRelations) {
      const initial = initialRelByTarget.get(rel.target);
      if (!initial) return true; // a pending create
      if (initial.type !== rel.type || (initial.rationale ?? "") !== rel.rationale) return true; // a pending update
    }
    return false;
  }

  /** Same as `relationsDirty()`, for the Related Inits tab. */
  export function initsDirty(): boolean {
    const stagedInitIds = new Set(stagedInits.map((r) => r.init));
    for (const [initId] of initialInitByInit) {
      if (!stagedInitIds.has(initId)) return true;
    }
    for (const rel of stagedInits) {
      const initial = initialInitByInit.get(rel.init);
      if (!initial) return true;
      if (initial.type !== rel.type || (initial.rationale ?? "") !== rel.rationale) return true;
    }
    return false;
  }

  /** Same as `relationsDirty()`, for the Permissions tab (surrogate-id keyed). */
  export function permissionsDirty(): boolean {
    const stagedIds = new Set(stagedPermissions.filter((p) => p.id != null).map((p) => p.id));
    for (const [pid] of initialPermById) {
      if (!stagedIds.has(pid)) return true;
    }
    for (const p of stagedPermissions) {
      if (p.id == null) return true;
      const initial = initialPermById.get(p.id);
      if (initial && (initial.target_type !== p.targetType || initial.target_code !== p.targetCode || initial.access_level !== p.access)) {
        return true;
      }
    }
    return false;
  }

  export async function flush(
    id: number,
    opts?: { skipChars?: boolean; skipRelations?: boolean; skipInits?: boolean; skipPermissions?: boolean },
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
        const newDetail = (charDetails[featureCode] ?? "").trim();
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
          const patch: { value?: string; detail?: string } = {};
          if (existing.value !== newValue) patch.value = newValue;
          if ((existing.detail ?? "") !== newDetail) patch.detail = newDetail;
          if (Object.keys(patch).length) {
            await updateCharacterization(id, featureCode, patch);
          }
        } else {
          await createCharacterization({ asset: id, feature: featureCode, value: newValue, detail: newDetail || undefined });
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
          } catch (err) {
            if (!isConflict(err)) throw err; // 409 = a logically-deleted row for this pair — reactivate it
            await updateAssetRelation(id, rel.target, { type: rel.type, rationale: rel.rationale || null, is_active: true });
          }
        } else if (initial.type !== rel.type || (initial.rationale ?? "") !== rel.rationale) {
          await updateAssetRelation(id, rel.target, { type: rel.type, rationale: rel.rationale || null });
        }
      }
    }

    // 3. Related Inits (same deletes-first → re-add-reactivates pattern)
    if (!opts?.skipInits) {
      const stagedInitIds = new Set(stagedInits.map((r) => r.init));
      for (const [initId] of initialInitByInit) {
        if (!stagedInitIds.has(initId)) {
          try {
            await deleteAssetInit(id, initId);
          } catch {
            /* already gone */
          }
        }
      }
      for (const rel of stagedInits) {
        const initial = initialInitByInit.get(rel.init);
        if (!initial) {
          try {
            await createAssetInit({ asset: id, init: rel.init, type: rel.type, rationale: rel.rationale || undefined });
          } catch (err) {
            if (!isConflict(err)) throw err; // 409 = a logically-deleted row for this pair — reactivate it
            await updateAssetInit(id, rel.init, { type: rel.type, rationale: rel.rationale || null, is_active: true });
          }
        } else if (initial.type !== rel.type || (initial.rationale ?? "") !== rel.rationale) {
          await updateAssetInit(id, rel.init, { type: rel.type, rationale: rel.rationale || null });
        }
      }
    }

    // 4. Permissions (surrogate-id keyed)
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
    if (!opts?.skipInits) {
      initialInitByInit = new Map(
        stagedInits.map((r) => [r.init, { init: r.init, type: r.type, rationale: r.rationale }]),
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
    charDetails = {};
    charDetailExpanded = {};
    charInvalid = {};
    charsLoading = false;
    initialCharByFeature = new Map();
    stagedRelations = [];
    initialRelByTarget = new Map();
    relTarget = "";
    relType = "";
    relRationale = "";
    relError = "";
    stagedInits = [];
    initialInitByInit = new Map();
    initTarget = "";
    initType = "";
    initRationale = "";
    initError = "";
    stagedPermissions = [];
    initialPermById = new Map();
    permType = "";
    permCode = "";
    permCodeOptions = [];
    permCodeDisabled = false;
    permAccess = "";
    permError = "";
    coreDirty = false;
    activeTab = "core";
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

  // A required characterization control swaps its neutral border for red once
  // validateChars() has flagged it empty; typing/choosing a value clears the
  // flag again (re-validated for real on the next save attempt).
  const charSelectClass =
    "w-full rounded-md border px-3 py-2 text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 dark:bg-gray-800 dark:text-white";
  const charTextareaClass =
    "w-full rounded-md border px-3 py-2 text-sm font-mono focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 dark:bg-gray-800 dark:text-white";
  const charDetailTextareaClass =
    "w-full rounded-md border border-gray-300 dark:border-gray-700 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 dark:bg-gray-800 dark:text-white";
  const charBorderClass = (feature: string): string => {
    if (charInvalid[feature]) return "border-red-500 dark:border-red-500";
    if (charChanged.has(feature)) return "border-amber-400 dark:border-amber-500";
    return "border-gray-300 dark:border-gray-700";
  };
  const clearCharInvalid = (feature: string): void => {
    if (charInvalid[feature]) charInvalid = { ...charInvalid, [feature]: false };
  };

  // ── Characterization "detail" disclosure ────────────────────────────────
  // A Show/Hide switch per field, collapsed by default (loadChars() never
  // pre-expands it, even when a detail already exists) so the panel stays
  // visually light. Purely a visibility toggle — hiding never clears the
  // staged text, only showing it again does.
  function toggleCharDetail(feature: string): void {
    const next = !charDetailExpanded[feature];
    charDetailExpanded = { ...charDetailExpanded, [feature]: next };
    if (next) {
      requestAnimationFrame(() => {
        rootEl?.querySelector<HTMLTextAreaElement>(`#${idPrefix}-char-detail-${feature}`)?.focus();
      });
    }
  }
</script>

<div bind:this={rootEl}>
  <!-- Tabs header -->
  {#snippet pendingDot()}
    <span
      class="ml-1 inline-block h-1.5 w-1.5 rounded-full bg-amber-500"
      title={t("asset_detail_modal.unsaved_indicator", "Unsaved changes")}
      aria-hidden="true"
    ></span>
  {/snippet}
  <div class="border-b border-gray-200 dark:border-gray-800">
    <div role="tablist" aria-label="Asset detail sections" class="-mb-px flex flex-nowrap gap-4 overflow-x-auto no-scrollbar text-sm font-medium sm:gap-6">
      <button
        type="button"
        role="tab"
        data-tab="core"
        aria-selected={activeTab === "core"}
        tabindex={activeTab === "core" ? 0 : -1}
        class={tabClass("core")}
        onclick={() => (activeTab = "core")}
        onkeydown={(e) => onTabKeydown(e)}
      >
        <span>{t("asset_detail_modal.core_section", "Core Fields")}</span>
        {#if tabDirty.core}{@render pendingDot()}{/if}
      </button>
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
        {#if tabDirty.chars}{@render pendingDot()}{/if}
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
        {#if tabDirty.related}{@render pendingDot()}{/if}
      </button>
      <button
        type="button"
        role="tab"
        data-tab="related_inits"
        aria-selected={activeTab === "related_inits"}
        tabindex={activeTab === "related_inits" ? 0 : -1}
        class={tabClass("related_inits")}
        onclick={() => (activeTab = "related_inits")}
        onkeydown={(e) => onTabKeydown(e)}
      >
        <span>{t("asset_detail_modal.tab_related_inits", "Related Inits")}</span>
        {#if stagedInits.length > 0}
          <span class="ml-1 rounded-full bg-indigo-100 px-1.5 py-0.5 text-[10px] font-semibold text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300">{stagedInits.length}</span>
        {/if}
        {#if tabDirty.related_inits}{@render pendingDot()}{/if}
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
        {#if tabDirty.permissions}{@render pendingDot()}{/if}
      </button>
      <!-- Discussion (interactive) / History / Versions (read-only) — only for
           an existing asset (nothing to view/discuss while creating). -->
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

  <!-- Core Fields panel (empty shell) — the asset's core fields (name/category/
       status/description/reference/tags) live in AssetDetailModal.astro's own
       markup/validation/save logic; its script re-parents that existing
       <section> into this shell right after mount (same "hydrated externally"
       pattern as the History/Versions panels below). -->
  <div data-tabpanel="core" role="tabpanel" class="pt-4" class:hidden={activeTab !== "core"}>
    <section id={`${idPrefix}-core`}></section>
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
            <div class="flex flex-wrap items-baseline justify-between gap-x-2 mb-1">
              <label class="block min-w-0 break-words text-sm font-semibold text-gray-800 dark:text-gray-200" for={`${idPrefix}-char-${spec.feature}`}>
                {t(`features.${spec.feature}`, spec.featureObj.name || spec.feature)}{#if spec.required}<span class="ml-0.5 text-red-500" aria-hidden="true">*</span>{/if}
              </label>
              <span class="shrink-0 text-[10px] uppercase tracking-wide text-gray-400">{t("asset_detail_modal.characterization_type_label", "Type")}: {spec.featureObj.type || ""}</span>
            </div>
            <div class="mb-2 flex items-start gap-2">
              {#if spec.featureObj.description}
                <p class="min-w-0 flex-1 text-xs text-gray-500 dark:text-gray-400 break-words">{spec.featureObj.description}</p>
              {/if}
              <button
                type="button"
                class="ml-auto flex shrink-0 items-center gap-1.5 text-[11px] font-medium text-gray-500 hover:text-indigo-600 dark:text-gray-400 dark:hover:text-indigo-400"
                aria-pressed={charDetailExpanded[spec.feature] ? "true" : "false"}
                onclick={() => toggleCharDetail(spec.feature)}
              >
                {#if charDetailExpanded[spec.feature]}
                  <svg viewBox="0 0 20 20" fill="currentColor" class="h-3.5 w-3.5" aria-hidden="true">
                    <path d="M2.53 2.47a.75.75 0 00-1.06 1.06l3.02 3.02C2.6 8.03 1.2 9.6.5 10.5c1.99 3 5.5 6.5 9.5 6.5 1.5 0 2.9-.35 4.15-.95l2.32 2.32a.75.75 0 101.06-1.06L2.53 2.47zM10 14.5a4.47 4.47 0 01-3.02-1.18l1.14-1.14A2.98 2.98 0 0010 13a3 3 0 003-3c0-.4-.08-.78-.22-1.12l1.14-1.14A4.47 4.47 0 0113.5 10 4.5 4.5 0 0110 14.5zM10 3.5c1.5 0 2.9.35 4.15.95l-1.24 1.24A6.98 6.98 0 0010 5.5a7 7 0 00-6.16 3.65L2.6 7.9C4.1 5.5 6.9 3.5 10 3.5z"></path>
                  </svg>
                {:else}
                  <svg viewBox="0 0 20 20" fill="currentColor" class="h-3.5 w-3.5" aria-hidden="true">
                    <path d="M10 3.5c-4.5 0-8 3.5-9.5 6.5C1.99 13 5.5 16.5 10 16.5s8.01-3.5 9.5-6.5C18 7 14.5 3.5 10 3.5zm0 11a4.5 4.5 0 110-9 4.5 4.5 0 010 9z"></path>
                    <circle cx="10" cy="10" r="2"></circle>
                  </svg>
                {/if}
                <span>{charDetailExpanded[spec.feature] ? t("asset_detail_modal.characterization_hide_detail", "Hide detail") : t("asset_detail_modal.characterization_show_detail", "Show detail")}</span>
                <span class={`relative inline-block h-4 w-7 shrink-0 rounded-full transition ${charDetailExpanded[spec.feature] ? "bg-indigo-600" : "bg-gray-300 dark:bg-gray-600"}`}>
                  <span class={`absolute top-0.5 left-0.5 h-3 w-3 rounded-full bg-white shadow transition ${charDetailExpanded[spec.feature] ? "translate-x-3" : ""}`}></span>
                </span>
              </button>
            </div>
            {#if spec.listItems && spec.listItems.length > 0}
              <select
                id={`${idPrefix}-char-${spec.feature}`}
                bind:value={charValues[spec.feature]}
                onchange={() => clearCharInvalid(spec.feature)}
                aria-invalid={charInvalid[spec.feature] ? "true" : undefined}
                class={`${charSelectClass} ${charBorderClass(spec.feature)}`}
              >
                <option value="">—</option>
                {#each langItems(spec.listItems) as li (li.value)}
                  <option value={li.value}>{li.label || li.value}</option>
                {/each}
              </select>
            {:else}
              <textarea
                id={`${idPrefix}-char-${spec.feature}`}
                bind:value={charValues[spec.feature]}
                oninput={() => clearCharInvalid(spec.feature)}
                rows="2"
                aria-invalid={charInvalid[spec.feature] ? "true" : undefined}
                class={`${charTextareaClass} ${charBorderClass(spec.feature)}`}
              ></textarea>
            {/if}
            {#if charInvalid[spec.feature]}
              <p class="mt-1 text-xs text-red-600 dark:text-red-400">
                {t("asset_detail_modal.characterization_required", "Please fill the required characterization fields.")}
              </p>
            {/if}
            {#if charDetailExpanded[spec.feature]}
              <textarea
                id={`${idPrefix}-char-detail-${spec.feature}`}
                bind:value={charDetails[spec.feature]}
                rows="2"
                placeholder={t("asset_detail_modal.characterization_detail_placeholder", "Additional detail (optional)")}
                class={`mt-2 ${charDetailTextareaClass}`}
              ></textarea>
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
            <li
              class={pendingRelationTargets.has(rel.target) ? `${rowClass} ring-2 ring-amber-400` : rowClass}
              data-pending={pendingRelationTargets.has(rel.target) ? "1" : undefined}
            >
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

  <!-- Related Inits panel -->
  <div data-tabpanel="related_inits" role="tabpanel" class="pt-4 space-y-4" class:hidden={activeTab !== "related_inits"}>
    <section>
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div>
          <label for={`${idPrefix}-init-target`} class={labelClass}>{t("asset_detail_modal.related_target_init", "Target initiative")}</label>
          <select id={`${idPrefix}-init-target`} bind:value={initTarget} class={fieldClass}>
            <option value="">{t("asset_detail_modal.related_choose_init", "— choose initiative —")}</option>
            {#each initOptions as o (o.value)}
              <option value={o.value}>{o.label}</option>
            {/each}
          </select>
        </div>
        <div>
          <label for={`${idPrefix}-init-type`} class={labelClass}>{t("asset_detail_modal.related_type", "Relation type")}</label>
          <select id={`${idPrefix}-init-type`} bind:value={initType} class={fieldClass}>
            <option value="">{t("asset_detail_modal.related_choose_type", "— choose type —")}</option>
            {#each relTypeOptions as o (o.value)}
              <option value={o.value}>{o.label}</option>
            {/each}
          </select>
        </div>
        <div class="md:col-span-2">
          <label for={`${idPrefix}-init-rationale`} class={labelClass}>{t("asset_detail_modal.related_rationale", "Rationale")}</label>
          <div class="flex gap-2">
            <input id={`${idPrefix}-init-rationale`} type="text" bind:value={initRationale} placeholder={t("asset_detail_modal.related_rationale_placeholder", "Why are these related? (optional)")} class="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 dark:border-gray-700 dark:bg-gray-800 dark:text-white" />
            <button type="button" class={addBtnClass} onclick={addInit}>{t("asset_detail_modal.related_add", "Add relation")}</button>
          </div>
        </div>
      </div>
      {#if initError}
        <p class="mt-2 text-xs text-red-600 dark:text-red-400">{initError}</p>
      {/if}
    </section>
    <section>
      {#if stagedInits.length === 0}
        <div class={emptyClass}>{t("asset_detail_modal.related_inits_empty", "No related initiatives yet.")}</div>
      {:else}
        <ul class="space-y-2">
          {#each stagedInits as rel, idx (rel.init)}
            <li
              class={pendingInitIds.has(rel.init) ? `${rowClass} ring-2 ring-amber-400` : rowClass}
              data-pending={pendingInitIds.has(rel.init) ? "1" : undefined}
            >
              <span class="min-w-0 flex-1 truncate text-sm font-semibold text-gray-800 dark:text-gray-200" title={rel.initLabel}>{rel.initLabel}</span>
              <span class="shrink-0 rounded-full bg-indigo-50 px-2 py-0.5 text-[11px] font-semibold text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300">{rel.typeLabel || rel.type}</span>
              {#if rel.rationale}
                <span class="hidden md:block max-w-[200px] truncate text-xs text-gray-500 dark:text-gray-400" title={rel.rationale}>{rel.rationale}</span>
              {/if}
              <button type="button" class="shrink-0 rounded-md p-1 text-gray-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/30" title={t("asset_detail_modal.related_remove", "Remove")} onclick={() => removeInit(idx)} aria-label={t("asset_detail_modal.related_remove", "Remove")}>
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
            <li
              class={pendingPermissionKeys.has(permPendingKey(p)) ? `${rowClass} ring-2 ring-amber-400` : rowClass}
              data-pending={pendingPermissionKeys.has(permPendingKey(p)) ? "1" : undefined}
            >
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

  <!-- Discussion panel — the Foro island self-loads the opened asset's thread
       off the same [data-modal-open] trigger. Fully interactive (comment/
       question/answer/delete-own), matching the gallery's read/browse
       CatalogDetailModal Discussion tab. -->
  <div data-tabpanel="discussion" role="tabpanel" class="pt-4" class:hidden={activeTab !== "discussion"}>
    <Foro modalId={idPrefix} />
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
