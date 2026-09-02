/**
 * relatedInits — the asset "related initiatives" section on the shared
 * CatalogDetailModal (Explore only, see RelatedInits.astro). Mirrors
 * `related.ts` (HU-LI07) but reads the `asset_inits` table via
 * `GET /api/asset_inits/asset/{id}` instead of `related_assets`.
 *
 * Unlike asset_relations, asset_inits has no resolved "with name" endpoint —
 * the raw rows only carry the initiative's id — so names are resolved
 * client-side from `getInitiativesSelect()` (fetched once, cached), the same
 * join AssetDetailTabs.svelte already does for the editable tab. All
 * asset/initiative-supplied text renders via `textContent` (XSS-safe).
 *
 * `mountRelatedInits` is self-contained: it listens for the same open trigger
 * the detail controller uses (`[data-modal-open=…]`), loads the initiative
 * relations for the opened asset, and updates the tab's count badge (if
 * present). Call once per detail modal (mountCatalogDetail does this).
 */
import { getAssetInitsByAsset } from "@/lib/asset_inits";
import { getInitiativesSelect, type InitiativeSelectOption } from "@/lib/initiatives";
import { translate } from "@/utils/i18nClient";
import type { AssetInit } from "@/types/api";

interface RelatedInitsConfig {
  /** The detail dialog id, e.g. "explore-view-modal". The shell lives at
   * `#${modalId}-related-inits` (rendered by RelatedInits.astro). */
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

let initiativeOptions: InitiativeSelectOption[] | null = null;
async function loadInitiativeOptions(): Promise<InitiativeSelectOption[]> {
  if (initiativeOptions) return initiativeOptions;
  try {
    initiativeOptions = await getInitiativesSelect();
  } catch {
    initiativeOptions = [];
  }
  return initiativeOptions;
}

export function mountRelatedInits(cfg: RelatedInitsConfig): void {
  if (typeof window === "undefined") return;
  const { modalId } = cfg;

  const root = document.getElementById(`${modalId}-related-inits`);
  if (!root) return;

  const listEl = root.querySelector<HTMLElement>("[data-related-inits-list]");
  const statusEl = root.querySelector<HTMLElement>("[data-related-inits-status]");
  const countEl = document.getElementById(`${modalId}-related-inits-count`);

  const setStatus = (text: string) => {
    if (!statusEl) return;
    statusEl.textContent = text;
    statusEl.classList.toggle("hidden", !text);
  };

  const setCount = (n: number) => {
    if (!countEl) return;
    countEl.textContent = String(n);
    countEl.classList.toggle("hidden", n === 0);
  };

  const relTypeLabel = (type: string): string =>
    tr(`related.type.${type}`, type.replace(/_/g, " ").toLowerCase());

  // ── Renderer (text via textContent — XSS-safe). Not clickable: there is no
  // initiative browsing UI to navigate to yet. ──────────────────────────────
  function cardNode(item: AssetInit, initLabel: string): HTMLElement {
    const card = document.createElement("div");
    card.className =
      "rounded-lg border border-gray-200 p-3 dark:border-gray-800";

    const head = document.createElement("div");
    head.className = "mb-1 flex items-center justify-between gap-2";

    const name = document.createElement("span");
    name.className = "truncate text-sm font-semibold text-gray-900 dark:text-gray-100";
    name.textContent = initLabel;

    const chip = document.createElement("span");
    chip.className =
      "shrink-0 rounded-md bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700 dark:bg-indigo-500/15 dark:text-indigo-300";
    chip.textContent = relTypeLabel(item.type);

    head.append(name, chip);
    card.appendChild(head);

    const rationale = (item.rationale || "").trim();
    if (rationale) {
      const p = document.createElement("p");
      p.className = "line-clamp-2 text-xs text-gray-500 dark:text-gray-400";
      p.textContent = rationale;
      card.appendChild(p);
    }
    return card;
  }

  async function load(id: number) {
    if (!listEl) return;
    listEl.innerHTML = "";
    setStatus(tr("related_inits.loading", "Loading related initiatives…"));
    setCount(0);
    try {
      const [items, options] = await Promise.all([
        getAssetInitsByAsset(id),
        loadInitiativeOptions(),
      ]);
      setStatus("");
      setCount(items.length);
      if (!items.length) {
        const p = document.createElement("p");
        p.className = "text-sm text-gray-400 dark:text-gray-500";
        p.textContent = tr("related_inits.empty", "No related initiatives.");
        listEl.appendChild(p);
        return;
      }
      for (const it of items) {
        const label = options.find((o) => Number(o.value) === it.init)?.label ?? String(it.init);
        listEl.appendChild(cardNode(it, label));
      }
    } catch {
      setStatus(tr("related_inits.error", "Could not load related initiatives."));
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
