/**
 * versions — the asset "version history" tab (HU-LI09, read side): a read-only,
 * newest-first list of every version of an asset (label + creation date, plus
 * who created it + the change type for bumped versions), where each row expands
 * to show that version's full characterization snapshot rendered identically to
 * the Details tab.
 *
 * Backed by the two version-history endpoints:
 *   - GET /api/assets/{id}/versions                                  (the list)
 *   - GET /api/assets/{id}/versions/{label}/characterizations   (one snapshot)
 * No new table — the backend derives both from the existing characterizations +
 * VERSIONING actions. Display only; all asset text is rendered with textContent
 * (via the shared section renderer), mirroring the foro/history renderers.
 *
 * `mountVersions` is self-contained: it listens for the same open trigger the
 * detail controller uses (`[data-modal-open=…]`) and loads the list for the
 * opened asset. Call once per detail modal (mountCatalogDetail does this).
 */
import { apiGet } from "./api";
import { formatRelative } from "./datatable";
import { translate } from "@/utils/i18nClient";
import { renderCharacterizationSections, type DetailSection } from "@/lib/catalogDetail";
import type { AssetVersion, Characterization } from "@/types/api";

// ── Services ─────────────────────────────────────────────────────────────────

/** An asset's version history, newest-first (includes the initial version). */
export async function getAssetVersions(assetId: number): Promise<AssetVersion[]> {
  return apiGet<AssetVersion[]>(
    `/api/assets/${encodeURIComponent(String(assetId))}/versions`,
  );
}

/** The characterization snapshot of one specific version of an asset. */
export async function getVersionCharacterizations(
  assetId: number,
  versionLabel: string,
): Promise<Characterization[]> {
  return apiGet<Characterization[]>(
    `/api/assets/${encodeURIComponent(String(assetId))}/versions/${encodeURIComponent(versionLabel)}/characterizations`,
  );
}

// ── Controller (hydrates the versions section in CatalogDetailModal) ──────────

interface VersionsConfig {
  /** The detail dialog id, e.g. "mcp-view-modal". The shell lives at
   * `#${modalId}-versions` (rendered by VersionsTimeline.astro). */
  modalId: string;
  /** The catalog's section config — reused to render each version's snapshot
   * exactly like the Details tab. */
  sections: DetailSection[];
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

const locale = (): string =>
  (typeof localStorage !== "undefined" && localStorage.getItem("lang")) || "en";

const CHANGE_TYPE_KEY: Record<string, string> = {
  major: "versions.change_type_major",
  minor: "versions.change_type_minor",
  patch: "versions.change_type_patch",
};

export function mountVersions(cfg: VersionsConfig): void {
  if (typeof window === "undefined") return;
  const { modalId, sections } = cfg;

  const root = document.getElementById(`${modalId}-versions`);
  if (!root) return;

  const listEl = root.querySelector<HTMLElement>("[data-versions-list]");
  const statusEl = root.querySelector<HTMLElement>("[data-versions-status]");

  const setStatus = (text: string) => {
    if (!statusEl) return;
    statusEl.textContent = text;
    statusEl.classList.toggle("hidden", !text);
  };

  function versionRow(assetId: number, v: AssetVersion): HTMLElement {
    const row = document.createElement("div");
    row.className = "border-b border-gray-100 py-1.5 last:border-0 dark:border-gray-800";

    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className =
      "flex w-full flex-wrap items-center gap-2 rounded-md px-1 py-1 text-left hover:bg-gray-50 dark:hover:bg-gray-800";

    const label = document.createElement("span");
    label.className = "font-mono text-sm font-semibold text-gray-900 dark:text-gray-100";
    label.textContent = `v${v.version_label}`;
    toggle.appendChild(label);

    if (v.is_current) {
      const badge = document.createElement("span");
      badge.className =
        "inline-flex items-center rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300";
      badge.textContent = tr("versions.current", "Current");
      toggle.appendChild(badge);
    }

    if (v.change_type) {
      const chip = document.createElement("span");
      chip.className =
        "inline-flex items-center rounded-md bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-gray-800 dark:text-gray-300";
      chip.textContent = tr(CHANGE_TYPE_KEY[v.change_type] ?? "", v.change_type);
      toggle.appendChild(chip);
    }

    const when = document.createElement("span");
    when.className = "text-xs text-gray-400 dark:text-gray-500";
    const actor = v.actor
      ? ` · ${tr("versions.created_by", "by")} ${v.actor}`
      : "";
    when.textContent = ` · ${formatRelative(v.created_at, locale())}${actor}`;
    toggle.appendChild(when);

    row.appendChild(toggle);

    const snapshot = document.createElement("div");
    snapshot.className = "hidden space-y-4 px-1 pb-3 pt-2";
    row.appendChild(snapshot);

    let loaded = false;
    toggle.addEventListener("click", async () => {
      const isHidden = snapshot.classList.contains("hidden");
      if (!isHidden) {
        snapshot.classList.add("hidden");
        return;
      }
      snapshot.classList.remove("hidden");
      if (loaded) return;
      loaded = true;
      snapshot.textContent = tr("versions.loading", "Loading…");
      try {
        const chars = await getVersionCharacterizations(assetId, v.version_label);
        const byFeature = Object.fromEntries(
          chars.map((c) => [c.feature, { value: c.value, detail: c.detail }]),
        );
        renderCharacterizationSections(snapshot, sections, byFeature);
        if (!snapshot.childElementCount) {
          snapshot.textContent = tr("versions.empty_snapshot", "No details for this version.");
        }
      } catch {
        loaded = false; // allow a retry on next expand
        snapshot.textContent = tr("versions.error", "Could not load the versions.");
      }
    });

    return row;
  }

  async function load(id: number) {
    if (!listEl) return;
    listEl.innerHTML = "";
    setStatus(tr("versions.loading", "Loading versions…"));
    try {
      const items = await getAssetVersions(id);
      setStatus("");
      if (!items.length) {
        setStatus(tr("versions.empty", "No versions yet."));
        return;
      }
      for (const v of items) listEl.appendChild(versionRow(id, v));
    } catch {
      setStatus(tr("versions.error", "Could not load the versions."));
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
