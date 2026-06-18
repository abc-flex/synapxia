/**
 * catalogModal — reusable create/edit orchestration for a LIB curated-catalog
 * modal (CatalogFormModal.astro). One asset category per modal.
 *
 * A catalog page mounts this once with its category + the feature codes it
 * renders as first-class fields (the inputs whose `name` === feature code live
 * in the modal's <slot>). The helper wires:
 *   - data-modal-open / data-modal-close + ESC
 *   - edit hydrate (asset core + its characterizations)
 *   - create defaults (seeded from the category's specifications)
 *   - submit → createAsset/updateAsset (fixed category) → upsert each
 *     characterization from the feature inputs → favorite → toast + reload
 *
 * Mirrors AssetDetailModal's behavior but generalized so MCP / Agent / Flow /
 * etc. catalogs reuse it unchanged — they differ only by `category` + `features`.
 */
import { createAsset, updateAsset, getAsset } from "@/lib/assets";
import {
  getCharacterizationsByAsset,
  createCharacterization,
  updateCharacterization,
  deleteCharacterization,
} from "@/lib/characterizations";
import { getSpecificationsbyCategory } from "@/lib/specifications";
import { isFavorite, setFavorite } from "@/lib/favorites";
import { getUser } from "@/lib/auth";

/**
 * A feature input declaration. A bare string targets the characterization
 * `value` column; an object lets a "rich" feature (e.g. PROMPT_TEMPLATE, TOOLS,
 * INSTRUCTIONS) read/write the `detail` column instead — matching the seed,
 * where `value` holds a short summary and `detail` holds the full payload.
 */
export type CatalogFeature = string | { name: string; column?: "value" | "detail" };

interface NormalizedFeature {
  name: string;
  column: "value" | "detail";
}

export interface CatalogModalConfig {
  /** Dialog id, e.g. "prompt-detail-modal". */
  modalId: string;
  /** Fixed asset category for everything created/edited here, e.g. "PROMPTS". */
  category: string;
  /** Feature codes rendered as first-class inputs (input name === feature code). */
  features: CatalogFeature[];
  /** i18n keys for the header title. */
  titleCreateKey?: string;
  titleEditKey?: string;
  /** i18n keys for status-banner messages (defaults are generic asset keys). */
  savedKey?: string;
  errorSaveKey?: string;
  errorLoadKey?: string;
}

export function mountCatalogModal(cfg: CatalogModalConfig): void {
  if (typeof window === "undefined") return;
  const { modalId, category } = cfg;
  const features: NormalizedFeature[] = cfg.features.map((f) =>
    typeof f === "string" ? { name: f, column: "value" } : { name: f.name, column: f.column ?? "value" },
  );

  const dialogEl = document.getElementById(modalId) as HTMLDialogElement | null;
  if (!dialogEl) return;
  const dialog: HTMLDialogElement = dialogEl;

  const form = document.getElementById(`${modalId}-form`) as HTMLFormElement;
  const idField = document.getElementById(`${modalId}-id`) as HTMLInputElement;
  const nameField = document.getElementById(`${modalId}-name`) as HTMLInputElement;
  const statusSel = document.getElementById(`${modalId}-status-select`) as HTMLSelectElement;
  const descField = document.getElementById(`${modalId}-description`) as HTMLTextAreaElement;
  const refField = document.getElementById(`${modalId}-reference`) as HTMLInputElement;
  const tagsField = document.getElementById(`${modalId}-tags`) as HTMLInputElement;
  const titleEl = document.getElementById(`${modalId}-title`) as HTMLElement;
  const statusBanner = document.getElementById(`${modalId}-status`) as HTMLElement;
  const submitBtn = document.getElementById(`${modalId}-submit`) as HTMLButtonElement;
  const favBtn = document.getElementById(`${modalId}-fav`) as HTMLButtonElement;
  const favSvg = favBtn?.querySelector("svg") as SVGElement | null;

  const featureInput = (code: string) =>
    form.querySelector<HTMLInputElement | HTMLTextAreaElement>(`[name="${code}"]`);

  // ── i18n + status banner helpers ────────────────────────────────────────
  const tr = (key: string, fallback: string): string => {
    try {
      const lang = localStorage.getItem("lang") || "en";
      const w = window as any;
      if (typeof w.t === "function") return w.t(key, lang) || fallback;
    } catch {
      /* non-fatal */
    }
    return fallback;
  };
  const showStatus = (msg: string, kind: "ok" | "error") => {
    if (!statusBanner) return;
    statusBanner.textContent = msg;
    statusBanner.className =
      "mx-6 mt-4 rounded-lg p-3 text-sm " +
      (kind === "ok"
        ? "bg-green-50 text-green-800 border border-green-200 dark:bg-green-900/30 dark:text-green-300 dark:border-green-700"
        : "bg-red-50 text-red-800 border border-red-200 dark:bg-red-900/30 dark:text-red-300 dark:border-red-700");
    statusBanner.classList.remove("hidden");
  };
  const clearStatus = () => statusBanner?.classList.add("hidden");

  // Category defaults (default_value per feature) — seed create mode.
  let defaults: Record<string, string> = {};
  getSpecificationsbyCategory(category)
    .then((specs) => {
      defaults = Object.fromEntries(
        specs
          .filter((s) => s.default_value != null)
          .map((s) => [s.feature, String(s.default_value)]),
      );
    })
    .catch(() => {
      defaults = {};
    });

  let editingId: number | null = null;
  let favoriteOn = false;

  function paintFavorite() {
    if (!favBtn || !favSvg) return;
    favBtn.setAttribute("aria-pressed", String(favoriteOn));
    favSvg.setAttribute("fill", favoriteOn ? "currentColor" : "none");
    favBtn.classList.toggle("text-yellow-400", favoriteOn);
    favBtn.classList.toggle("text-gray-400", !favoriteOn);
  }

  favBtn?.addEventListener("click", async () => {
    const user = getUser() as any;
    if (!user?.id && user?.id !== 0) return;
    if (!editingId) {
      // create mode → stage the bit until the asset exists
      favoriteOn = !favoriteOn;
      paintFavorite();
      return;
    }
    const next = !favoriteOn;
    favoriteOn = next;
    paintFavorite();
    try {
      await setFavorite(Number(user.id), editingId, next);
    } catch {
      favoriteOn = !next; // revert
      paintFavorite();
    }
  });

  // ── Reset / open / close ────────────────────────────────────────────────
  function resetForm() {
    form.reset();
    idField.value = "";
    editingId = null;
    favoriteOn = false;
    paintFavorite();
    clearStatus();
  }

  function openCreate() {
    resetForm();
    if (titleEl && cfg.titleCreateKey) {
      titleEl.setAttribute("data-i18n", cfg.titleCreateKey);
      titleEl.textContent = tr(cfg.titleCreateKey, titleEl.textContent || "");
    }
    // Seed feature fields with the category defaults.
    for (const feat of features) {
      const input = featureInput(feat.name);
      if (input && !input.value) input.value = defaults[feat.name] ?? "";
    }
    dialog.showModal();
  }

  async function openEdit(assetId: number | string) {
    resetForm();
    editingId = Number(assetId);
    if (titleEl && cfg.titleEditKey) {
      titleEl.setAttribute("data-i18n", cfg.titleEditKey);
      titleEl.textContent = tr(cfg.titleEditKey, titleEl.textContent || "");
    }
    dialog.showModal();

    const user = getUser() as any;
    if (user?.id || user?.id === 0) {
      isFavorite(Number(user.id), editingId).then((on) => {
        favoriteOn = on;
        paintFavorite();
      });
    }

    try {
      const asset = await getAsset(editingId);
      idField.value = String(asset.id ?? "");
      nameField.value = asset.name ?? "";
      descField.value = asset.description ?? "";
      refField.value = asset.reference ?? "";
      // Tolerate legacy/seeded rows that stored the bare status code
      // (e.g. `IN_USE`) without the list_items `N-` sort-prefix.
      const resolveStatusValue = (raw: string): string => {
        if (!raw) return "";
        if ([...statusSel.options].some((o) => o.value === raw)) return raw;
        const opt = [...statusSel.options].find(
          (o) => o.value.replace(/^\d+-/, "") === raw,
        );
        return opt?.value ?? raw;
      };
      statusSel.value = resolveStatusValue(asset.status ?? "");
      tagsField.value = Array.isArray(asset.tags)
        ? asset.tags.join(", ")
        : ((asset.tags as unknown as string) ?? "");

      const chars = await getCharacterizationsByAsset(editingId);
      const byFeature = Object.fromEntries(chars.map((c) => [c.feature, c]));
      for (const feat of features) {
        const input = featureInput(feat.name);
        if (input) input.value = (byFeature[feat.name]?.[feat.column] as string) ?? "";
      }
    } catch (e) {
      showStatus(
        e instanceof Error
          ? e.message
          : tr(cfg.errorLoadKey ?? "asset_detail_modal.error_load", "Could not load."),
        "error",
      );
    }
  }

  function closeModal() {
    dialog.close();
    resetForm();
  }

  // ── Wire global open/close buttons ──────────────────────────────────────
  document.addEventListener("click", (e) => {
    const opener = (e.target as HTMLElement).closest?.(`[data-modal-open="${modalId}"]`);
    if (opener) {
      e.preventDefault();
      const mode = (opener as HTMLElement).dataset.assetMode || "create";
      const assetId = (opener as HTMLElement).dataset.assetId;
      if (mode === "edit" && assetId) openEdit(assetId);
      else openCreate();
    }
    const closer = (e.target as HTMLElement).closest?.(`[data-modal-close="${modalId}"]`);
    if (closer) {
      e.preventDefault();
      closeModal();
    }
  });

  dialog.addEventListener("cancel", (e) => {
    e.preventDefault();
    closeModal();
  });

  // ── Upsert one characterization (create-or-update), or delete if blank ───
  async function flushFeature(
    assetId: number,
    feature: string,
    value: string,
    column: "value" | "detail",
  ) {
    const v = value.trim();
    if (v) {
      try {
        await updateCharacterization(assetId, feature, { [column]: v });
      } catch {
        await createCharacterization({ asset: assetId, feature, [column]: v });
      }
    } else {
      // Blank → remove any existing row (best-effort).
      try {
        await deleteCharacterization(assetId, feature);
      } catch {
        /* nothing to delete */
      }
    }
  }

  // ── Submit ──────────────────────────────────────────────────────────────
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    submitBtn.disabled = true;
    clearStatus();

    const corePayload = {
      name: nameField.value.trim(),
      description: descField.value.trim() || undefined,
      category,
      reference: refField.value.trim() || undefined,
      status: statusSel.value,
      tags: tagsField.value
        ? tagsField.value.split(",").map((t) => t.trim()).filter(Boolean)
        : undefined,
      is_active: true,
    };

    try {
      const saved = editingId
        ? await updateAsset(editingId, corePayload)
        : await createAsset(corePayload);
      const assetId = Number(saved.id ?? editingId);

      for (const feat of features) {
        const input = featureInput(feat.name);
        await flushFeature(assetId, feat.name, input?.value ?? "", feat.column);
      }

      // Favorite (create mode only — edit mode toggled immediately).
      if (!editingId && favoriteOn) {
        const user = getUser() as any;
        if (user?.id || user?.id === 0) {
          try {
            await setFavorite(Number(user.id), assetId, true);
          } catch {
            /* non-fatal */
          }
        }
      }

      showStatus(tr(cfg.savedKey ?? "asset_detail_modal.saved", "Saved."), "ok");
      setTimeout(() => {
        closeModal();
        window.location.reload();
      }, 400);
    } catch (err) {
      showStatus(
        err instanceof Error
          ? err.message
          : tr(cfg.errorSaveKey ?? "asset_detail_modal.error_save", "Could not save."),
        "error",
      );
      submitBtn.disabled = false;
    }
  });
}
