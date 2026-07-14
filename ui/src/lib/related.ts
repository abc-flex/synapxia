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

  const relTypeLabel = (type: string): string =>
    tr(`related.type.${type}`, type.replace(/_/g, " ").toLowerCase());

  // ── Renderer (asset text via textContent — XSS-safe) ───────────────────────
  // Each card is a button that re-opens the SAME detail modal for the related
  // asset (it carries the open trigger the detail controllers listen for, so
  // the whole modal re-hydrates in place via open(item.id)).
  function cardNode(item: RelatedAsset): HTMLElement {
    const card = document.createElement("button");
    card.type = "button";
    card.dataset.modalOpen = modalId;
    card.dataset.assetId = String(item.id);
    card.className =
      "group block w-full rounded-lg border border-gray-200 p-3 text-left transition-colors hover:border-indigo-300 hover:bg-indigo-50/40 dark:border-gray-800 dark:hover:border-indigo-500/40 dark:hover:bg-indigo-500/10";

    const head = document.createElement("div");
    head.className = "mb-1 flex items-center justify-between gap-2";

    const name = document.createElement("span");
    name.className =
      "truncate text-sm font-semibold text-gray-900 group-hover:text-indigo-700 dark:text-gray-100 dark:group-hover:text-indigo-300";
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
    setStatus(tr("related.loading", "Loading related assets…"));
    try {
      const items = await getRelatedAssets(id);
      setStatus("");
      if (!items.length) {
        // Dedicated tab now — show an empty state rather than hiding.
        const p = document.createElement("p");
        p.className = "text-sm text-gray-400 dark:text-gray-500";
        p.textContent = tr("related.empty", "No related assets.");
        listEl.appendChild(p);
        return;
      }
      for (const it of items) listEl.appendChild(cardNode(it));
    } catch {
      setStatus(tr("related.error", "Could not load related assets."));
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
