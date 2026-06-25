/**
 * related — the asset "related assets" feature (HU-LI07): a read-only section on
 * the shared CatalogDetailModal that lists the assets connected to the one being
 * viewed, in both directions.
 *
 * Backed by the existing `related_assets` table through the resolved
 * `/api/asset_relations/related/{id}` route (one batched call, no N+1) — no new
 * table. Editing relations stays in the admin asset editor; here it is display
 * only. All asset-supplied text is rendered with `textContent` (XSS-safe),
 * mirroring the foro renderers.
 *
 * `mountRelated` is self-contained: it listens for the same open trigger the
 * detail controller uses (`[data-modal-open=…]`), loads the related assets for
 * the opened asset, and hides the whole block when there are none. Call once
 * per detail modal (mountCatalogDetail does this).
 */
import { getRelatedAssets } from "@/lib/asset_relations";
import { translate } from "@/utils/i18nClient";
import type { RelatedAsset } from "@/types/api";

interface RelatedConfig {
  /** The detail dialog id, e.g. "mcp-view-modal". The shell lives at
   * `#${modalId}-related` (rendered by Related.astro). */
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

export function mountRelated(cfg: RelatedConfig): void {
  if (typeof window === "undefined") return;
  const { modalId } = cfg;

  const root = document.getElementById(`${modalId}-related`);
  if (!root) return;

  const listEl = root.querySelector<HTMLElement>("[data-related-list]");
  const statusEl = root.querySelector<HTMLElement>("[data-related-status]");

  const setStatus = (text: string) => {
    if (!statusEl) return;
    statusEl.textContent = text;
    statusEl.classList.toggle("hidden", !text);
  };
  const show = (on: boolean) => root.classList.toggle("hidden", !on);

  const relTypeLabel = (type: string): string =>
    tr(`related.type.${type}`, type.replace(/_/g, " ").toLowerCase());

  // ── Renderer (asset text via textContent — XSS-safe) ───────────────────────
  function cardNode(item: RelatedAsset): HTMLElement {
    const card = document.createElement("div");
    card.className = "rounded-lg border border-gray-200 p-3 dark:border-gray-800";

    const head = document.createElement("div");
    head.className = "mb-1 flex items-center justify-between gap-2";

    const name = document.createElement("span");
    name.className = "truncate text-sm font-semibold text-gray-900 dark:text-gray-100";
    name.textContent = item.name || "—";

    // The arrow conveys direction: → this asset references the related one,
    // ← the related one references this asset.
    const chip = document.createElement("span");
    chip.className =
      "shrink-0 rounded-md bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700 dark:bg-indigo-500/15 dark:text-indigo-300";
    const arrow = item.direction === "outgoing" ? "→" : "←";
    chip.textContent = `${arrow} ${relTypeLabel(item.relation_type)}`;
    const dirTitle =
      item.direction === "outgoing"
        ? tr("related.outgoing", "References")
        : tr("related.incoming", "Referenced by");
    chip.title = dirTitle;

    head.append(name, chip);
    card.appendChild(head);

    const desc = (item.description || "").trim();
    if (desc) {
      const p = document.createElement("p");
      p.className = "line-clamp-2 text-xs text-gray-500 dark:text-gray-400";
      p.textContent = desc;
      card.appendChild(p);
    }
    return card;
  }

  async function load(id: number) {
    if (!listEl) return;
    listEl.innerHTML = "";
    show(true);
    setStatus(tr("related.loading", "Loading related assets…"));
    try {
      const items = await getRelatedAssets(id);
      setStatus("");
      if (!items.length) {
        show(false); // hide the whole block when the asset has no relations
        return;
      }
      for (const it of items) listEl.appendChild(cardNode(it));
    } catch {
      // On error keep the section hidden rather than showing a broken block.
      show(false);
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
