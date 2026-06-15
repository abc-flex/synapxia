/**
 * assetDetailTabs — ONE shared, framework-free editable detail-tabs widget.
 *
 * Builds + wires the Characterizations / Related Assets / Permissions tabs
 * into any container element, parameterized by an `idPrefix` (so the modal
 * and an inline table row can coexist) and an `assetId`. All state lives in
 * the per-call closure (no module globals), so multiple instances never
 * clobber each other.
 *
 * Used by:
 *   - AssetDetailModal.astro (idPrefix "asset-detail-modal", flushed on Save
 *     after the asset is created/updated).
 *   - lib/assets.astro inline expand row (idPrefix `asset-detail-row-${id}`,
 *     flushed on the row's own Save; asset already exists).
 *
 * The widget owns ONLY the tabs region — not the asset core fields, the
 * favorite star, or any Save/Cancel buttons. Callers own that chrome and
 * call `flush(assetId)` to persist the three collections' diffs.
 */

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
import { loadClientTranslations } from "@/utils/i18nClient";

export type TabName = "chars" | "related" | "permissions";
export interface TabCounts {
  chars: number;
  related: number;
  permissions: number;
}
export interface InitAssetDetailTabsOptions {
  idPrefix: string;
  assetId?: number | null;
  mode: "modal" | "inline";
  onError?: (msg: string) => void;
  onCountsChange?: (counts: TabCounts) => void;
}
export interface AssetDetailTabsController {
  /** Populate the relation + permission composer dropdowns (no data load). */
  loadOptions(): Promise<void>;
  loadChars(categoryCode: string): Promise<void>;
  hydrate(assetId: number, category?: string): Promise<void>;
  flush(assetId: number): Promise<void>;
  counts(): TabCounts;
  activateTab(name: TabName): void;
  reset(): void;
  destroy(): void;
  root: HTMLElement;
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

const TARGET_LOADERS: Record<string, () => Promise<SelectOption[]>> = {
  USER: getUsersSelect,
  ROLE: getRolesSelect,
  TEAM: getTeamsSelect,
  UNIT: getBusinessUnitsSelect,
  PROJECT: getProjectsSelect,
};

function escapeHtml(s: unknown): string {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function tr(key: string, fallback: string): string {
  try {
    const lang = localStorage.getItem("lang") || "en";
    const w = window as any;
    if (typeof w.t === "function") return w.t(key, lang) || fallback;
  } catch {
    /* non-fatal */
  }
  return fallback;
}

function isConflict(err: unknown): boolean {
  return err instanceof Error && /\(409\)/.test(err.message);
}

export function initAssetDetailTabs(
  rootEl: HTMLElement,
  opts: InitAssetDetailTabsOptions,
): AssetDetailTabsController {
  const { idPrefix, mode } = opts;
  const onError = opts.onError ?? ((m: string) => console.error(m));

  // ── Build the tabs DOM ────────────────────────────────────────────────
  rootEl.innerHTML = `
    <div class="border-b border-gray-200 dark:border-gray-800">
      <div role="tablist" aria-label="Asset detail sections" class="-mb-px flex gap-6 text-sm font-medium">
        <button type="button" role="tab" id="${idPrefix}-tab-chars" aria-controls="${idPrefix}-panel-chars"
                aria-selected="true" data-tab="chars"
                class="border-b-2 border-indigo-600 px-1 pb-3 text-indigo-600 dark:text-indigo-400">
          <span data-i18n="asset_detail_modal.characterizations_section">Characterizations</span>
          <span id="${idPrefix}-spec-count" class="ml-1 hidden rounded-full bg-gray-100 px-1.5 py-0.5 text-[10px] font-semibold text-gray-600 dark:bg-gray-700 dark:text-gray-300"></span>
        </button>
        <button type="button" role="tab" id="${idPrefix}-tab-related" aria-controls="${idPrefix}-panel-related"
                aria-selected="false" tabindex="-1" data-tab="related"
                class="border-b-2 border-transparent px-1 pb-3 text-gray-500 hover:border-gray-300 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
          <span data-i18n="asset_detail_modal.tab_related">Related Assets</span>
          <span id="${idPrefix}-rel-count" class="ml-1 hidden rounded-full bg-indigo-100 px-1.5 py-0.5 text-[10px] font-semibold text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300"></span>
        </button>
        <button type="button" role="tab" id="${idPrefix}-tab-permissions" aria-controls="${idPrefix}-panel-permissions"
                aria-selected="false" tabindex="-1" data-tab="permissions"
                class="border-b-2 border-transparent px-1 pb-3 text-gray-500 hover:border-gray-300 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
          <span data-i18n="asset_detail_modal.tab_permissions">Permissions</span>
          <span id="${idPrefix}-perm-count" class="ml-1 hidden rounded-full bg-indigo-100 px-1.5 py-0.5 text-[10px] font-semibold text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300"></span>
        </button>
      </div>
    </div>

    <div id="${idPrefix}-panel-chars" role="tabpanel" aria-labelledby="${idPrefix}-tab-chars" class="pt-4">
      <div id="${idPrefix}-empty" class="rounded-lg border border-dashed border-gray-300 dark:border-gray-700 p-6 text-center text-sm text-gray-500 dark:text-gray-400" data-i18n="asset_detail_modal.characterizations_empty">Select a category to load the required features.</div>
      <div id="${idPrefix}-chars" class="hidden space-y-4"></div>
    </div>

    <div id="${idPrefix}-panel-related" role="tabpanel" aria-labelledby="${idPrefix}-tab-related" class="hidden pt-4 space-y-4">
      <section>
        <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <label for="${idPrefix}-rel-target" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1" data-i18n="asset_detail_modal.related_target">Target asset</label>
            <select id="${idPrefix}-rel-target" class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 dark:border-gray-700 dark:bg-gray-800 dark:text-white">
              <option value="" data-i18n="asset_detail_modal.related_choose_asset">— choose asset —</option>
            </select>
          </div>
          <div>
            <label for="${idPrefix}-rel-type" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1" data-i18n="asset_detail_modal.related_type">Relation type</label>
            <select id="${idPrefix}-rel-type" class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 dark:border-gray-700 dark:bg-gray-800 dark:text-white">
              <option value="" data-i18n="asset_detail_modal.related_choose_type">— choose type —</option>
            </select>
          </div>
          <div class="md:col-span-2">
            <label for="${idPrefix}-rel-rationale" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1" data-i18n="asset_detail_modal.related_rationale">Rationale</label>
            <div class="flex gap-2">
              <input id="${idPrefix}-rel-rationale" type="text" placeholder="Why are these related? (optional)" data-i18n-placeholder="asset_detail_modal.related_rationale_placeholder" class="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 dark:border-gray-700 dark:bg-gray-800 dark:text-white" />
              <button type="button" id="${idPrefix}-rel-add" class="shrink-0 rounded-lg border border-indigo-600 px-4 py-2 text-sm font-semibold text-indigo-600 hover:bg-indigo-50 dark:text-indigo-400 dark:hover:bg-indigo-900/30" data-i18n="asset_detail_modal.related_add">Add relation</button>
            </div>
          </div>
        </div>
        <p id="${idPrefix}-rel-error" class="mt-2 hidden text-xs text-red-600 dark:text-red-400"></p>
      </section>
      <section>
        <div id="${idPrefix}-rel-empty" class="rounded-lg border border-dashed border-gray-300 dark:border-gray-700 p-6 text-center text-sm text-gray-500 dark:text-gray-400" data-i18n="asset_detail_modal.related_empty">No related assets yet.</div>
        <ul id="${idPrefix}-rel-rows" class="hidden space-y-2"></ul>
      </section>
    </div>

    <div id="${idPrefix}-panel-permissions" role="tabpanel" aria-labelledby="${idPrefix}-tab-permissions" class="hidden pt-4 space-y-4">
      <section>
        <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div>
            <label for="${idPrefix}-perm-target-type" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1" data-i18n="asset_detail_modal.perm_target_type">Target type</label>
            <select id="${idPrefix}-perm-target-type" class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 dark:border-gray-700 dark:bg-gray-800 dark:text-white">
              <option value="" data-i18n="asset_detail_modal.perm_choose_target_type">— choose type —</option>
            </select>
          </div>
          <div>
            <label for="${idPrefix}-perm-target-code" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1" data-i18n="asset_detail_modal.perm_target">Target</label>
            <select id="${idPrefix}-perm-target-code" class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 dark:border-gray-700 dark:bg-gray-800 dark:text-white">
              <option value="" data-i18n="asset_detail_modal.perm_choose_target">— choose target —</option>
            </select>
          </div>
          <div>
            <label for="${idPrefix}-perm-access" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1" data-i18n="asset_detail_modal.perm_access">Access level</label>
            <div class="flex gap-2">
              <select id="${idPrefix}-perm-access" class="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 dark:border-gray-700 dark:bg-gray-800 dark:text-white">
                <option value="" data-i18n="asset_detail_modal.perm_choose_access">— choose access —</option>
              </select>
            </div>
          </div>
          <div class="md:col-span-3 flex justify-end">
            <button type="button" id="${idPrefix}-perm-add" class="shrink-0 rounded-lg border border-indigo-600 px-4 py-2 text-sm font-semibold text-indigo-600 hover:bg-indigo-50 dark:text-indigo-400 dark:hover:bg-indigo-900/30" data-i18n="asset_detail_modal.perm_add">Add permission</button>
          </div>
        </div>
        <p id="${idPrefix}-perm-error" class="mt-2 hidden text-xs text-red-600 dark:text-red-400"></p>
      </section>
      <section>
        <div id="${idPrefix}-perm-empty" class="rounded-lg border border-dashed border-gray-300 dark:border-gray-700 p-6 text-center text-sm text-gray-500 dark:text-gray-400" data-i18n="asset_detail_modal.perm_empty">No permissions yet.</div>
        <ul id="${idPrefix}-perm-rows" class="hidden space-y-2"></ul>
      </section>
    </div>
  `;

  const el = <T extends HTMLElement>(suffix: string): T =>
    document.getElementById(`${idPrefix}-${suffix}`) as T;

  // Tab elements
  const tabButtons = Array.from(
    rootEl.querySelectorAll<HTMLButtonElement>("[role=tab]"),
  );
  const panelChars = el<HTMLElement>("panel-chars");
  const panelRelated = el<HTMLElement>("panel-related");
  const panelPermissions = el<HTMLElement>("panel-permissions");
  // Chars
  const emptyEl = el<HTMLElement>("empty");
  const charsEl = el<HTMLElement>("chars");
  const specCountEl = el<HTMLElement>("spec-count");
  // Relations
  const relTargetSel = el<HTMLSelectElement>("rel-target");
  const relTypeSel = el<HTMLSelectElement>("rel-type");
  const relRationale = el<HTMLInputElement>("rel-rationale");
  const relAddBtn = el<HTMLButtonElement>("rel-add");
  const relErrorEl = el<HTMLElement>("rel-error");
  const relEmptyEl = el<HTMLElement>("rel-empty");
  const relRowsEl = el<HTMLElement>("rel-rows");
  const relCountEl = el<HTMLElement>("rel-count");
  // Permissions
  const permTypeSel = el<HTMLSelectElement>("perm-target-type");
  const permCodeSel = el<HTMLSelectElement>("perm-target-code");
  const permAccessSel = el<HTMLSelectElement>("perm-access");
  const permAddBtn = el<HTMLButtonElement>("perm-add");
  const permErrorEl = el<HTMLElement>("perm-error");
  const permEmptyEl = el<HTMLElement>("perm-empty");
  const permRowsEl = el<HTMLElement>("perm-rows");
  const permCountEl = el<HTMLElement>("perm-count");

  // ── Per-instance state ────────────────────────────────────────────────
  const featureCache = new Map<string, any>();
  const listItemsCache = new Map<string, any[]>();
  const targetOptCache = new Map<string, SelectOption[]>();
  let loadedSpecs: any[] = [];
  let editingAssetId: number | null = opts.assetId ?? null;
  let initialCharByFeature = new Map<string, any>();
  let stagedRelations: StagedRelation[] = [];
  let initialRelByTarget = new Map<number, any>();
  let assetOptions: SelectOption[] = [];
  let stagedPermissions: StagedPermission[] = [];
  let initialPermById = new Map<number, any>();
  let targetTypeLabels = new Map<string, string>();
  let accessLabels = new Map<string, string>();

  const emitCounts = () => opts.onCountsChange?.(controllerCounts());
  const controllerCounts = (): TabCounts => ({
    chars: loadedSpecs.length,
    related: stagedRelations.length,
    permissions: stagedPermissions.length,
  });

  // ── Tabs ──────────────────────────────────────────────────────────────
  function activateTab(name: TabName) {
    for (const btn of tabButtons) {
      const active = btn.dataset.tab === name;
      btn.setAttribute("aria-selected", String(active));
      btn.tabIndex = active ? 0 : -1;
      btn.classList.toggle("border-indigo-600", active);
      btn.classList.toggle("text-indigo-600", active);
      btn.classList.toggle("dark:text-indigo-400", active);
      btn.classList.toggle("border-transparent", !active);
      btn.classList.toggle("text-gray-500", !active);
      btn.classList.toggle("dark:text-gray-400", !active);
    }
    panelChars.classList.toggle("hidden", name !== "chars");
    panelRelated.classList.toggle("hidden", name !== "related");
    panelPermissions.classList.toggle("hidden", name !== "permissions");
  }

  tabButtons.forEach((btn, idx) => {
    btn.addEventListener("click", () => activateTab(btn.dataset.tab as TabName));
    btn.addEventListener("keydown", (e) => {
      let next = -1;
      if (e.key === "ArrowRight") next = (idx + 1) % tabButtons.length;
      else if (e.key === "ArrowLeft") next = (idx - 1 + tabButtons.length) % tabButtons.length;
      else if (e.key === "Home") next = 0;
      else if (e.key === "End") next = tabButtons.length - 1;
      if (next >= 0) {
        e.preventDefault();
        tabButtons[next].focus();
        activateTab(tabButtons[next].dataset.tab as TabName);
      }
    });
  });

  // Native constraint validation can't focus a control inside a hidden
  // panel. Flip to the owning tab first (modal form only; inline has no form).
  const ownerForm = rootEl.closest("form");
  if (ownerForm) {
    ownerForm.addEventListener(
      "invalid",
      (e) => {
        const panel = (e.target as HTMLElement).closest("[role=tabpanel]");
        if (panel && panel.classList.contains("hidden")) {
          const id = panel.id;
          activateTab(
            id.endsWith("permissions") ? "permissions" : id.endsWith("related") ? "related" : "chars",
          );
        }
      },
      true,
    );
  }

  const keepFirst = (sel: HTMLSelectElement) => {
    const placeholder = sel.options[0];
    sel.innerHTML = "";
    if (placeholder) sel.appendChild(placeholder);
  };
  const langItems = (items: any[]): any[] => {
    const lang = localStorage.getItem("lang") || "en";
    const byLang = items.filter((li) => li.lang === lang);
    return (byLang.length ? byLang : items.filter((li) => li.lang === "en")).sort(
      (a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0),
    );
  };

  // ── Characterizations ─────────────────────────────────────────────────
  async function loadChars(categoryCode: string) {
    loadedSpecs = [];
    charsEl.innerHTML = "";
    if (!categoryCode) {
      emptyEl.classList.remove("hidden");
      charsEl.classList.add("hidden");
      specCountEl.textContent = "";
      specCountEl.classList.add("hidden");
      emitCounts();
      return;
    }
    emptyEl.classList.add("hidden");
    charsEl.classList.remove("hidden");
    charsEl.innerHTML = `<div class="text-sm text-gray-400" data-i18n="common.loading">Loading…</div>`;
    loadClientTranslations();

    let specs: any[] = [];
    try {
      specs = await getSpecificationsbyCategory(categoryCode);
    } catch {
      onError(tr("asset_detail_modal.error_specs", "Could not load specifications."));
      charsEl.innerHTML = "";
      return;
    }

    const enriched = await Promise.all(
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

    loadedSpecs = enriched;
    charsEl.innerHTML = "";
    enriched.forEach((spec) => {
      const featureCode = spec.feature;
      const labelText = spec.featureObj.name || featureCode;
      const descText = spec.featureObj.description || "";
      const existing = initialCharByFeature.get(featureCode);
      const currentValue = existing?.value ?? spec.default_value ?? "";

      const wrap = document.createElement("div");
      wrap.dataset.feature = featureCode;
      wrap.className =
        "rounded-lg border border-gray-200 dark:border-gray-800 bg-gray-50/50 dark:bg-white/[0.02] p-3";

      const labelRow = document.createElement("div");
      labelRow.className = "flex items-baseline justify-between mb-1.5";
      labelRow.innerHTML = `
        <label class="block text-sm font-semibold text-gray-800 dark:text-gray-200" data-i18n="features.${featureCode}" for="${idPrefix}-char-${featureCode}">${escapeHtml(labelText)}</label>
        <span class="text-[10px] uppercase tracking-wide text-gray-400">${escapeHtml(spec.featureObj.type || "")}</span>
      `;
      wrap.appendChild(labelRow);

      if (descText) {
        const desc = document.createElement("p");
        desc.className = "mb-2 text-xs text-gray-500 dark:text-gray-400";
        desc.textContent = descText;
        wrap.appendChild(desc);
      }

      let inputEl: HTMLSelectElement | HTMLTextAreaElement;
      if (spec.listItems && spec.listItems.length > 0) {
        const sel = document.createElement("select");
        sel.className =
          "w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 dark:border-gray-700 dark:bg-gray-800 dark:text-white";
        const blank = document.createElement("option");
        blank.value = "";
        blank.textContent = "—";
        sel.appendChild(blank);
        langItems(spec.listItems).forEach((li: any) => {
          const opt = document.createElement("option");
          opt.value = li.value;
          opt.textContent = li.label || li.value;
          sel.appendChild(opt);
        });
        inputEl = sel;
      } else {
        const ta = document.createElement("textarea");
        ta.rows = 2;
        ta.className =
          "w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 dark:border-gray-700 dark:bg-gray-800 dark:text-white";
        inputEl = ta;
      }
      inputEl.id = `${idPrefix}-char-${featureCode}`;
      inputEl.name = `char_${featureCode}`;
      inputEl.value = currentValue;
      wrap.appendChild(inputEl);

      charsEl.appendChild(wrap);
    });

    specCountEl.textContent = String(enriched.length);
    specCountEl.classList.toggle("hidden", enriched.length === 0);
    emitCounts();
    loadClientTranslations();
  }

  // ── Relations ─────────────────────────────────────────────────────────
  const showRelError = (msg: string) => {
    relErrorEl.textContent = msg;
    relErrorEl.classList.remove("hidden");
  };
  const clearRelError = () => relErrorEl.classList.add("hidden");

  function renderRelations() {
    relRowsEl.innerHTML = "";
    const has = stagedRelations.length > 0;
    relEmptyEl.classList.toggle("hidden", has);
    relRowsEl.classList.toggle("hidden", !has);
    relCountEl.classList.toggle("hidden", !has);
    relCountEl.textContent = String(stagedRelations.length);

    stagedRelations.forEach((rel, idx) => {
      const li = document.createElement("li");
      li.className =
        "flex items-center gap-3 rounded-lg border border-gray-200 dark:border-gray-800 bg-gray-50/50 dark:bg-white/[0.02] px-3 py-2";
      li.innerHTML = `
        <span class="min-w-0 flex-1 truncate text-sm font-semibold text-gray-800 dark:text-gray-200" title="${escapeHtml(rel.targetLabel)}">${escapeHtml(rel.targetLabel)}</span>
        <span class="shrink-0 rounded-full bg-indigo-50 px-2 py-0.5 text-[11px] font-semibold text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300">${escapeHtml(rel.typeLabel || rel.type)}</span>
        ${rel.rationale ? `<span class="hidden md:block max-w-[200px] truncate text-xs text-gray-500 dark:text-gray-400" title="${escapeHtml(rel.rationale)}">${escapeHtml(rel.rationale)}</span>` : ""}
        <button type="button" data-rel-remove="${idx}" class="shrink-0 rounded-md p-1 text-gray-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/30" title="Remove" data-i18n-title="asset_detail_modal.related_remove">
          <svg class="w-4 h-4" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/></svg>
        </button>`;
      relRowsEl.appendChild(li);
    });
    emitCounts();
    try {
      loadClientTranslations();
    } catch {
      /* non-fatal */
    }
  }

  relRowsEl.addEventListener("click", (e) => {
    const btn = (e.target as HTMLElement).closest?.("[data-rel-remove]") as HTMLElement | null;
    if (!btn) return;
    stagedRelations.splice(Number(btn.dataset.relRemove), 1);
    renderRelations();
  });

  relAddBtn.addEventListener("click", () => {
    clearRelError();
    const target = Number(relTargetSel.value);
    const type = relTypeSel.value;
    if (!target || !type) {
      showRelError(tr("asset_detail_modal.related_missing_fields", "Pick a target asset and a relation type."));
      return;
    }
    if (stagedRelations.some((r) => r.target === target)) {
      showRelError(tr("asset_detail_modal.related_duplicate", "This asset is already related."));
      return;
    }
    stagedRelations.push({
      target,
      targetLabel: relTargetSel.selectedOptions[0]?.textContent?.trim() || String(target),
      type,
      typeLabel: relTypeSel.selectedOptions[0]?.textContent?.trim() || type,
      rationale: relRationale.value.trim(),
    });
    relTargetSel.value = "";
    relTypeSel.value = "";
    relRationale.value = "";
    renderRelations();
  });

  async function loadRelationOptions() {
    try {
      assetOptions = await getAssetsSelect();
    } catch {
      assetOptions = [];
    }
    keepFirst(relTargetSel);
    for (const a of assetOptions) {
      if (editingAssetId && Number(a.value) === editingAssetId) continue;
      const opt = document.createElement("option");
      opt.value = a.value;
      opt.textContent = a.label;
      relTargetSel.appendChild(opt);
    }
    try {
      let items = listItemsCache.get("RELATION_TYPE");
      if (!items) {
        items = await getListItemsbyList("RELATION_TYPE");
        listItemsCache.set("RELATION_TYPE", items);
      }
      keepFirst(relTypeSel);
      for (const li of langItems(items)) {
        const opt = document.createElement("option");
        opt.value = li.value;
        opt.textContent = li.label || li.value;
        relTypeSel.appendChild(opt);
      }
    } catch {
      /* type select stays placeholder-only */
    }
  }

  // ── Permissions ───────────────────────────────────────────────────────
  const showPermError = (msg: string) => {
    permErrorEl.textContent = msg;
    permErrorEl.classList.remove("hidden");
  };
  const clearPermError = () => permErrorEl.classList.add("hidden");

  function renderPermissions() {
    permRowsEl.innerHTML = "";
    const has = stagedPermissions.length > 0;
    permEmptyEl.classList.toggle("hidden", has);
    permRowsEl.classList.toggle("hidden", !has);
    permCountEl.classList.toggle("hidden", !has);
    permCountEl.textContent = String(stagedPermissions.length);

    stagedPermissions.forEach((p, idx) => {
      const li = document.createElement("li");
      li.className =
        "flex items-center gap-3 rounded-lg border border-gray-200 dark:border-gray-800 bg-gray-50/50 dark:bg-white/[0.02] px-3 py-2";
      li.innerHTML = `
        <span class="shrink-0 rounded-full bg-gray-100 px-2 py-0.5 text-[11px] font-semibold text-gray-600 dark:bg-gray-700 dark:text-gray-300">${escapeHtml(p.targetTypeLabel || p.targetType)}</span>
        <span class="min-w-0 flex-1 truncate text-sm font-semibold text-gray-800 dark:text-gray-200" title="${escapeHtml(p.targetCodeLabel)}">${escapeHtml(p.targetCodeLabel)}</span>
        <span class="shrink-0 rounded-full bg-indigo-50 px-2 py-0.5 text-[11px] font-semibold text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300">${escapeHtml(p.accessLabel || p.access)}</span>
        <button type="button" data-perm-remove="${idx}" class="shrink-0 rounded-md p-1 text-gray-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/30" title="Remove" data-i18n-title="asset_detail_modal.perm_remove">
          <svg class="w-4 h-4" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/></svg>
        </button>`;
      permRowsEl.appendChild(li);
    });
    emitCounts();
    try {
      loadClientTranslations();
    } catch {
      /* non-fatal */
    }
  }

  permRowsEl.addEventListener("click", (e) => {
    const btn = (e.target as HTMLElement).closest?.("[data-perm-remove]") as HTMLElement | null;
    if (!btn) return;
    stagedPermissions.splice(Number(btn.dataset.permRemove), 1);
    renderPermissions();
  });

  // Populate the target_code dropdown for the chosen target type.
  async function populateTargetCode(targetType: string) {
    permCodeSel.innerHTML = `<option value="" data-i18n="asset_detail_modal.perm_choose_target">— choose target —</option>`;
    if (!targetType || targetType === "PUBLIC") {
      permCodeSel.disabled = targetType === "PUBLIC";
      loadClientTranslations();
      return;
    }
    permCodeSel.disabled = false;
    const loader = TARGET_LOADERS[targetType];
    if (!loader) {
      loadClientTranslations();
      return;
    }
    let optList = targetOptCache.get(targetType);
    if (!optList) {
      try {
        optList = await loader();
      } catch {
        optList = [];
      }
      targetOptCache.set(targetType, optList);
    }
    for (const o of optList) {
      const opt = document.createElement("option");
      opt.value = o.value;
      opt.textContent = o.label;
      permCodeSel.appendChild(opt);
    }
    loadClientTranslations();
  }

  permTypeSel.addEventListener("change", () => {
    void populateTargetCode(permTypeSel.value);
  });

  permAddBtn.addEventListener("click", () => {
    clearPermError();
    const targetType = permTypeSel.value;
    const access = permAccessSel.value;
    if (!targetType || !access) {
      showPermError(tr("asset_detail_modal.perm_missing_fields", "Pick a target type, target and access level."));
      return;
    }
    let targetCode: string;
    let targetCodeLabel: string;
    if (targetType === "PUBLIC") {
      targetCode = "PUBLIC";
      targetCodeLabel = tr("asset_detail_modal.perm_public", "Public");
    } else {
      targetCode = permCodeSel.value;
      if (!targetCode) {
        showPermError(tr("asset_detail_modal.perm_missing_fields", "Pick a target type, target and access level."));
        return;
      }
      targetCodeLabel = permCodeSel.selectedOptions[0]?.textContent?.trim() || targetCode;
    }
    if (stagedPermissions.some((p) => p.targetType === targetType && p.targetCode === targetCode)) {
      showPermError(tr("asset_detail_modal.perm_duplicate", "This target already has a permission."));
      return;
    }
    stagedPermissions.push({
      targetType,
      targetTypeLabel: permTypeSel.selectedOptions[0]?.textContent?.trim() || targetType,
      targetCode,
      targetCodeLabel,
      access,
      accessLabel: permAccessSel.selectedOptions[0]?.textContent?.trim() || access,
    });
    permTypeSel.value = "";
    permCodeSel.innerHTML = `<option value="" data-i18n="asset_detail_modal.perm_choose_target">— choose target —</option>`;
    permAccessSel.value = "";
    renderPermissions();
    loadClientTranslations();
  });

  async function loadPermissionOptions() {
    try {
      let items = listItemsCache.get("TARGET_TYPE");
      if (!items) {
        items = await getListItemsbyList("TARGET_TYPE");
        listItemsCache.set("TARGET_TYPE", items);
      }
      keepFirst(permTypeSel);
      targetTypeLabels = new Map();
      for (const li of langItems(items)) {
        const opt = document.createElement("option");
        opt.value = li.value;
        opt.textContent = li.label || li.value;
        permTypeSel.appendChild(opt);
        targetTypeLabels.set(li.value, li.label || li.value);
      }
    } catch {
      /* placeholder-only */
    }
    try {
      let items = listItemsCache.get("ACCESS_LEVEL");
      if (!items) {
        items = await getListItemsbyList("ACCESS_LEVEL");
        listItemsCache.set("ACCESS_LEVEL", items);
      }
      keepFirst(permAccessSel);
      accessLabels = new Map();
      for (const li of langItems(items)) {
        const opt = document.createElement("option");
        opt.value = li.value;
        opt.textContent = li.label || li.value;
        permAccessSel.appendChild(opt);
        accessLabels.set(li.value, li.label || li.value);
      }
    } catch {
      /* placeholder-only */
    }
  }

  // Resolve a hydrated permission's target_code → friendly label by loading
  // that type's option list (cached). Falls back to the raw code.
  async function resolveTargetLabel(targetType: string, targetCode: string): Promise<string> {
    if (targetType === "PUBLIC") return tr("asset_detail_modal.perm_public", "Public");
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

  // ── options / hydrate / flush / reset / destroy ───────────────────────
  async function loadOptions() {
    await Promise.all([loadRelationOptions(), loadPermissionOptions()]);
  }

  async function hydrate(assetId: number, category?: string) {
    editingAssetId = assetId;
    await loadOptions();

    let cat = category;
    const [chars, relations, permissions] = await Promise.all([
      getCharacterizationsByAsset(assetId).catch(() => [] as any[]),
      getAssetRelationsBySource(assetId).catch(() => {
        onError(tr("asset_detail_modal.error_relations", "Could not load related assets."));
        return [] as any[];
      }),
      getAssetPermissionsByAsset(assetId).catch(() => {
        onError(tr("asset_detail_modal.error_permissions", "Could not load permissions."));
        return [] as any[];
      }),
    ]);

    if (cat === undefined) {
      try {
        cat = (await getAsset(assetId)).category ?? "";
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
      typeLabel: [...relTypeSel.options].find((o) => o.value === r.type)?.textContent?.trim() || r.type,
      rationale: r.rationale ?? "",
    }));
    renderRelations();

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
    renderPermissions();

    // Characterizations
    initialCharByFeature = new Map(chars.map((c: any) => [c.feature, c]));
    await loadChars(cat ?? "");
  }

  async function flush(assetId: number) {
    // 1. Characterizations
    for (const wrap of Array.from(charsEl.querySelectorAll<HTMLElement>("[data-feature]"))) {
      const featureCode = wrap.dataset.feature as string;
      const input = wrap.querySelector("textarea, select, input") as HTMLInputElement | null;
      const newValue = (input?.value ?? "").trim();
      const existing = initialCharByFeature.get(featureCode);
      if (!newValue) {
        if (existing) {
          try {
            await deleteCharacterization(assetId, featureCode);
          } catch {
            /* already gone */
          }
        }
        continue;
      }
      if (existing) {
        if (existing.value !== newValue) {
          await updateCharacterization(assetId, featureCode, { value: newValue });
        }
      } else {
        await createCharacterization({ asset: assetId, feature: featureCode, value: newValue });
      }
    }

    // 2. Relations (deletes first → re-add hits 409→reactivate)
    const stagedTargets = new Set(stagedRelations.map((r) => r.target));
    for (const [target] of initialRelByTarget) {
      if (!stagedTargets.has(target)) {
        try {
          await deleteAssetRelation(assetId, target);
        } catch {
          /* already gone */
        }
      }
    }
    for (const rel of stagedRelations) {
      const initial = initialRelByTarget.get(rel.target);
      if (!initial) {
        try {
          await createAssetRelation({ source: assetId, target: rel.target, type: rel.type, rationale: rel.rationale || undefined });
        } catch {
          await updateAssetRelation(assetId, rel.target, { type: rel.type, rationale: rel.rationale || null, is_active: true });
        }
      } else if (initial.type !== rel.type || (initial.rationale ?? "") !== rel.rationale) {
        await updateAssetRelation(assetId, rel.target, { type: rel.type, rationale: rel.rationale || null });
      }
    }

    // 3. Permissions (surrogate-id keyed)
    const stagedIds = new Set(stagedPermissions.filter((p) => p.id != null).map((p) => p.id));
    for (const [id] of initialPermById) {
      if (!stagedIds.has(id)) {
        try {
          await deleteAssetPermission(id);
        } catch {
          /* already gone */
        }
      }
    }
    for (const p of stagedPermissions) {
      if (p.id == null) {
        try {
          const created = await createAssetPermission({
            asset: assetId,
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

    // Re-seed initial maps from persisted state so a second flush (inline, no
    // reload) diffs against the new baseline.
    initialCharByFeature = new Map(
      Array.from(charsEl.querySelectorAll<HTMLElement>("[data-feature]"))
        .map((wrap) => {
          const f = wrap.dataset.feature as string;
          const input = wrap.querySelector("textarea, select, input") as HTMLInputElement | null;
          return [f, { feature: f, value: (input?.value ?? "").trim() }] as [string, any];
        })
        .filter(([, c]) => c.value),
    );
    initialRelByTarget = new Map(stagedRelations.map((r) => [r.target, { target: r.target, type: r.type, rationale: r.rationale }]));
    initialPermById = new Map(
      stagedPermissions
        .filter((p) => p.id != null)
        .map((p) => [p.id as number, { target_type: p.targetType, target_code: p.targetCode, access_level: p.access }]),
    );
  }

  function reset() {
    editingAssetId = opts.assetId ?? null;
    loadedSpecs = [];
    initialCharByFeature = new Map();
    charsEl.innerHTML = "";
    charsEl.classList.add("hidden");
    emptyEl.classList.remove("hidden");
    specCountEl.textContent = "";
    specCountEl.classList.add("hidden");
    stagedRelations = [];
    initialRelByTarget = new Map();
    renderRelations();
    clearRelError();
    stagedPermissions = [];
    initialPermById = new Map();
    renderPermissions();
    clearPermError();
    activateTab("chars");
  }

  function destroy() {
    // Listeners live on elements inside rootEl; clearing it drops them.
    rootEl.innerHTML = "";
  }

  return {
    loadOptions,
    loadChars,
    hydrate,
    flush,
    counts: controllerCounts,
    activateTab,
    reset,
    destroy,
    root: rootEl,
  };
}
