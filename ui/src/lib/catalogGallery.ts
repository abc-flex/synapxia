/**
 * catalogGallery — client controller for a card-based LIB catalog gallery
 * (CardGallery.astro). Catalog-agnostic: it operates purely on `[data-card]`
 * elements and their `data-*` attributes, so every curated catalog (Prompts,
 * MCPs, Agents, …) reuses it unchanged. No DataTable / simple-datatables dep.
 *
 * Responsibilities:
 *   - text search (over `data-search`), status filter (`data-status`),
 *     "my favorites" toggle (`data-favorite`), "show more" pagination
 *   - favorite-star clicks → setFavorite (optimistic, revert on error)
 *   - whole-card click → open the edit modal named by `data-edit-modal`
 *   - delete-button clicks → dispatch the `datatable-action` event consumed by
 *     crudClient.js (reuses the existing delete modal prefill flow)
 */
import { setFavorite } from "@/lib/favorites";
import { getUser } from "@/lib/auth";

export interface CardGalleryConfig {
  /** Root element id wrapping the toolbar + grid, e.g. "prompts-gallery". */
  galleryId: string;
  /** How many cards to reveal per page (default 12). */
  pageSize?: number;
}

export function initCardGallery(cfg: CardGalleryConfig): void {
  if (typeof window === "undefined") return;
  const { galleryId } = cfg;
  const pageSize = cfg.pageSize ?? 12;

  const root = document.getElementById(galleryId);
  if (!root) return;

  const search = document.getElementById(`${galleryId}-search`) as HTMLInputElement | null;
  const statusSel = document.getElementById(`${galleryId}-status`) as HTMLSelectElement | null;
  const favToggle = document.getElementById(`${galleryId}-fav-filter`) as HTMLButtonElement | null;
  const emptyEl = document.getElementById(`${galleryId}-empty`);
  const showMoreBtn = document.getElementById(`${galleryId}-more`) as HTMLButtonElement | null;

  const cards = () => Array.from(root.querySelectorAll<HTMLElement>("[data-card]"));
  let limit = pageSize;

  function applyFilters() {
    const q = (search?.value || "").trim().toLowerCase();
    const st = statusSel?.value || "";
    const favOnly = favToggle?.getAttribute("aria-pressed") === "true";

    let matched = 0;
    for (const card of cards()) {
      const text = (card.dataset.search || "").toLowerCase();
      const cardStatus = card.dataset.status || "";
      const fav = card.dataset.favorite === "yes";
      const ok = (!q || text.includes(q)) && (!st || cardStatus === st) && (!favOnly || fav);
      if (ok) {
        matched++;
        card.classList.toggle("hidden", matched > limit);
      } else {
        card.classList.add("hidden");
      }
    }
    emptyEl?.classList.toggle("hidden", matched > 0);
    showMoreBtn?.classList.toggle("hidden", matched <= limit);
  }

  search?.addEventListener("input", () => {
    limit = pageSize;
    applyFilters();
  });
  statusSel?.addEventListener("change", () => {
    limit = pageSize;
    applyFilters();
  });
  favToggle?.addEventListener("click", () => {
    const on = favToggle.getAttribute("aria-pressed") === "true";
    favToggle.setAttribute("aria-pressed", String(!on));
    favToggle.classList.toggle("bg-indigo-600", !on);
    favToggle.classList.toggle("text-white", !on);
    limit = pageSize;
    applyFilters();
  });
  showMoreBtn?.addEventListener("click", () => {
    limit += pageSize;
    applyFilters();
  });

  // ── Favorite star ─────────────────────────────────────────────────────────
  const paintStar = (btn: HTMLElement, on: boolean) => {
    btn.setAttribute("aria-pressed", String(on));
    btn.classList.toggle("text-yellow-400", on);
    btn.classList.toggle("text-gray-400", !on);
    btn.querySelector("svg")?.setAttribute("fill", on ? "currentColor" : "none");
    const card = btn.closest<HTMLElement>("[data-card]");
    if (card) card.dataset.favorite = on ? "yes" : "no";
  };

  // ── Delegated card interactions ───────────────────────────────────────────
  root.addEventListener("click", async (e) => {
    const target = e.target as HTMLElement;

    const favBtn = target.closest<HTMLElement>('[data-action="favorite"]');
    if (favBtn) {
      e.preventDefault();
      e.stopPropagation();
      const user = getUser() as any;
      if (!user || (user.id === undefined || user.id === null)) {
        (window as any).showToast?.("Sign in to manage favorites", "error");
        return;
      }
      const id = Number(favBtn.dataset.id);
      const wasOn = favBtn.getAttribute("aria-pressed") === "true";
      paintStar(favBtn, !wasOn); // optimistic
      try {
        await setFavorite(Number(user.id), id, !wasOn);
        if (favToggle?.getAttribute("aria-pressed") === "true") applyFilters();
      } catch (err) {
        paintStar(favBtn, wasOn); // revert
        (window as any).showToast?.(
          err instanceof Error ? err.message : "Could not update favorite",
          "error",
        );
      }
      return;
    }

    // Generic copy-to-clipboard action (e.g. an MCP card's "Copy config").
    const copyBtn = target.closest<HTMLElement>('[data-action="copy"]');
    if (copyBtn) {
      e.preventDefault();
      e.stopPropagation();
      const text = copyBtn.dataset.copy ?? "";
      const okMsg = copyBtn.dataset.copyOk || "Copied";
      try {
        await navigator.clipboard.writeText(text);
        (window as any).showToast?.(okMsg, "success");
      } catch {
        (window as any).showToast?.("Could not copy", "error");
      }
      return;
    }

    const delBtn = target.closest<HTMLElement>('[data-action="delete"]');
    if (delBtn) {
      e.preventDefault();
      e.stopPropagation();
      // Decoupled from any specific delete modal — the page wires this to its
      // CrudModal. Carries id + name so the confirmation can be prefilled.
      document.dispatchEvent(
        new CustomEvent("gallery-delete", {
          detail: { id: delBtn.dataset.id, name: delBtn.dataset.name ?? "" },
        }),
      );
      return;
    }

    // Edit buttons carry their own data-modal-open (handled by the modal);
    // ignore them here so we don't double-open.
    if (target.closest('[data-modal-open]')) return;

    // Whole-card click → open the read-only detail view if the card declares
    // one (`data-detail-modal`), else fall back to the edit modal.
    const card = target.closest<HTMLElement>("[data-card]");
    const openModal = card?.dataset.detailModal || card?.dataset.editModal;
    if (card && openModal && card.dataset.id) {
      const synthetic = document.createElement("button");
      synthetic.style.display = "none";
      synthetic.setAttribute("data-modal-open", openModal);
      synthetic.setAttribute("data-asset-mode", "edit");
      synthetic.setAttribute("data-asset-id", card.dataset.id);
      document.body.appendChild(synthetic);
      synthetic.click();
      synthetic.remove();
    }
  });

  applyFilters();
}
