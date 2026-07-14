/**
 * assetPermissionsView — read-only "Permissions" tab on the shared gallery
 * detail modal (CatalogDetailModal). Lets a viewer SEE who an asset is shared
 * with (target type · target · access level) without any edit affordance — the
 * editable permissions live only in the /lib/assets repo modal.
 *
 * Backed by the existing `GET /api/asset_permissions/asset/{id}` (gated at
 * module read, so any gallery viewer can read it). Target/type/access labels
 * are resolved the same way the editable AssetDetailTabs does: TARGET_TYPE /
 * ACCESS_LEVEL list_items + the per-target select loaders. Display only; all
 * text via `textContent` (XSS-safe), mirroring the history/foro renderers.
 *
 * `mountPermissions` is self-contained: it listens for the same open trigger
 * the detail controller uses (`[data-modal-open=…]`) and loads the permissions
 * for the opened asset. Call once per detail modal (mountCatalogDetail does).
 */
import { getAssetPermissionsByAsset } from "./asset_permissions";
import { getListItemsbyList } from "./list_items";
import { getUsersSelect } from "./users";
import { getRolesSelect } from "./roles";
import { getTeamsSelect } from "./teams";
import { getBusinessUnitsSelect } from "./business_units";
import { getProjectsSelect } from "./projects";
import { translate } from "@/utils/i18nClient";
import type { AssetPermission } from "@/types/api";

type SelectOption = { value: string; label: string };

interface PermissionsConfig {
  /** The detail dialog id, e.g. "prompt-view-modal". The shell lives at
   * `#${modalId}-permissions` (rendered by PermissionsList.astro). */
  modalId: string;
}

const tr = (key: string, fallback: string): string => {
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

// Mirror AssetDetailTabs.langItems: prefer the current locale's rows, fall back
// to English, sort by sort_order.
function langItems(items: any[]): any[] {
  const lang = currentLang();
  const byLang = items.filter((li) => li.lang === lang);
  return (byLang.length ? byLang : items.filter((li) => li.lang === "en")).sort(
    (a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0),
  );
}

const TARGET_LOADERS: Record<string, () => Promise<SelectOption[]>> = {
  USER: getUsersSelect,
  ROLE: getRolesSelect,
  TEAM: getTeamsSelect,
  UNIT: getBusinessUnitsSelect,
  PROJECT: getProjectsSelect,
};

export function mountPermissions(cfg: PermissionsConfig): void {
  if (typeof window === "undefined") return;
  const { modalId } = cfg;

  const root = document.getElementById(`${modalId}-permissions`);
  if (!root) return;

  const listEl = root.querySelector<HTMLElement>("[data-permissions-list]");
  const statusEl = root.querySelector<HTMLElement>("[data-permissions-status]");

  const setStatus = (text: string) => {
    if (!statusEl) return;
    statusEl.textContent = text;
    statusEl.classList.toggle("hidden", !text);
  };

  // Label caches, resolved once per open (cheap; the modal reloads per asset).
  const targetTypeLabels = new Map<string, string>();
  const accessLabels = new Map<string, string>();
  const targetOptCache = new Map<string, SelectOption[]>();

  async function loadLabelMaps(): Promise<void> {
    targetTypeLabels.clear();
    accessLabels.clear();
    try {
      for (const li of langItems(await getListItemsbyList("TARGET_TYPE")))
        targetTypeLabels.set(li.value, li.label || li.value);
    } catch {
      /* fall back to raw codes */
    }
    try {
      for (const li of langItems(await getListItemsbyList("ACCESS_LEVEL")))
        accessLabels.set(li.value, li.label || li.value);
    } catch {
      /* fall back to raw codes */
    }
  }

  async function resolveTargetLabel(targetType: string, targetCode: string): Promise<string> {
    if (targetType === "PUBLIC") return tr("permissions_view.public", "Public");
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

  function chip(text: string, cls: string): HTMLElement {
    const span = document.createElement("span");
    span.className = `inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${cls}`;
    span.textContent = text;
    return span;
  }

  async function rowNode(p: AssetPermission): Promise<HTMLElement> {
    const row = document.createElement("div");
    row.className =
      "flex flex-wrap items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 dark:border-gray-700 dark:bg-gray-800/50";

    const typeLabel = targetTypeLabels.get(p.target_type) || p.target_type;
    const targetLabel = await resolveTargetLabel(p.target_type, p.target_code);
    const accessLabel = accessLabels.get(p.access_level) || p.access_level;

    row.appendChild(
      chip(typeLabel, "bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-200"),
    );
    const name = document.createElement("span");
    name.className = "min-w-0 flex-1 truncate text-sm font-semibold text-gray-900 dark:text-gray-100";
    name.textContent = targetLabel;
    row.appendChild(name);
    row.appendChild(
      chip(accessLabel, "bg-indigo-100 text-indigo-700 dark:bg-indigo-500/20 dark:text-indigo-300"),
    );
    return row;
  }

  async function load(id: number) {
    if (!listEl) return;
    listEl.innerHTML = "";
    setStatus(tr("permissions_view.loading", "Loading permissions…"));
    try {
      const [perms] = await Promise.all([getAssetPermissionsByAsset(id), loadLabelMaps()]);
      setStatus("");
      if (!perms.length) {
        setStatus(tr("permissions_view.empty", "No permissions defined for this asset."));
        return;
      }
      for (const p of perms) listEl.appendChild(await rowNode(p));
    } catch {
      setStatus(tr("permissions_view.error", "Could not load the permissions."));
    }
  }

  // Load on the same open trigger the detail controller listens for.
  document.addEventListener("click", (e) => {
    const opener = (e.target as HTMLElement).closest?.(`[data-modal-open="${modalId}"]`);
    if (!opener) return;
    const id = (opener as HTMLElement).dataset.assetId;
    if (id) load(Number(id));
  });
}
