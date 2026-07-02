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
import { setVote, getVoteTally, type VoteValue } from "@/lib/actions";
import { getUser } from "@/lib/auth";
import { translate } from "@/utils/i18nClient";
import { showToast } from "@/lib/toast";
import type { VoteTally } from "@/types/api";

/**
 * Reflect a vote button's state: filled icon when active (outline when not),
 * and flip the title/aria-label to "Remove vote" so the un-vote toggle is
 * discoverable. Keeps the `data-i18n-*` keys in sync so a later language
 * switch re-translates correctly.
 */
export function styleVoteButton(
  btn: HTMLElement | null,
  on: boolean,
  baseKey: string,
  activeColor: string,
): void {
  if (!btn) return;
  btn.setAttribute("aria-pressed", String(on));
  // Solid thumb icon stays filled; state shows via color only (vivid when it's
  // the user's vote, muted gray otherwise) — no fill toggling, which turned the
  // glyph into a messy blob.
  btn.classList.toggle(activeColor, on);
  btn.classList.toggle("text-gray-400", !on);
  const key = on ? "gallery.vote_remove" : baseKey;
  const label = translate(key);
  btn.setAttribute("data-i18n-title", key);
  btn.setAttribute("data-i18n-aria-label", key);
  btn.setAttribute("title", label);
  btn.setAttribute("aria-label", label);
}

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

  // Arrived here from a successful Propose (propose.astro redirects with
  // `?proposed=1`). Confirm on the gallery, then strip the param so a refresh
  // doesn't re-toast.
  const params = new URLSearchParams(window.location.search);
  if (params.has("proposed")) {
    const msg = translate("gallery.proposed");
    // Import `showToast` directly (not `window.showToast`): this runs at page
    // load, before `installGlobalToast()` defines the global, so the global
    // would still be undefined here.
    showToast(
      msg && msg !== "gallery.proposed"
        ? msg
        : "Your asset has been proposed and is now under review.",
      "success",
    );
    params.delete("proposed");
    const qs = params.toString();
    window.history.replaceState({}, "", window.location.pathname + (qs ? `?${qs}` : ""));
  }

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
    // The FavoritesPill's pressed styling comes from the `aria-pressed:` Tailwind
    // variant, so we only flip the attribute here (no manual class toggling).
    favToggle.setAttribute("aria-pressed", String(!on));
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

  // ── Vote bar (up/down) ──────────────────────────────────────────────────────
  const paintVote = (scope: HTMLElement | null, tally: VoteTally) => {
    if (!scope) return;
    const up = scope.querySelector<HTMLElement>('[data-action="vote-up"]');
    const down = scope.querySelector<HTMLElement>('[data-action="vote-down"]');
    const upCount = scope.querySelector<HTMLElement>("[data-vote-up-count]");
    const downCount = scope.querySelector<HTMLElement>("[data-vote-down-count]");
    styleVoteButton(up, tally.my_vote === "POSITIVE", "gallery.vote_up", "text-emerald-500");
    styleVoteButton(down, tally.my_vote === "NEGATIVE", "gallery.vote_down", "text-rose-500");
    if (upCount) upCount.textContent = String(tally.positive);
    if (downCount) downCount.textContent = String(tally.negative);
  };

  // Debounce votes: a burst of rapid clicks on one card coalesces into a single
  // request that fires ~300ms after clicking pauses (per-card timer). The
  // in-flight guard then serializes any still-overlapping request.
  const voteTimers = new WeakMap<HTMLElement, ReturnType<typeof setTimeout>>();
  const VOTE_DEBOUNCE_MS = 300;

  async function sendVote(
    scope: HTMLElement,
    userId: number,
    id: number,
    value: VoteValue,
  ) {
    if (scope.dataset.voting === "1") return; // a request is already in flight
    scope.dataset.voting = "1";
    try {
      const tally = await setVote(userId, id, value);
      paintVote(scope, tally);
    } catch (err) {
      showToast(
        err instanceof Error ? err.message : "Could not register your vote",
        "error",
      );
      // Re-sync from the authoritative tally so a failed vote never leaves the
      // bar in a stale state.
      getVoteTally(id)
        .then((tally) => paintVote(scope, tally))
        .catch(() => {});
    } finally {
      delete scope.dataset.voting;
    }
  }

  function queueVote(scope: HTMLElement, userId: number, id: number, value: VoteValue) {
    const pending = voteTimers.get(scope);
    if (pending) clearTimeout(pending);
    voteTimers.set(
      scope,
      setTimeout(() => {
        voteTimers.delete(scope);
        void sendVote(scope, userId, id, value);
      }, VOTE_DEBOUNCE_MS),
    );
  }

  // ── Delegated card interactions ───────────────────────────────────────────
  root.addEventListener("click", async (e) => {
    const target = e.target as HTMLElement;

    const favBtn = target.closest<HTMLElement>('[data-action="favorite"]');
    if (favBtn) {
      e.preventDefault();
      e.stopPropagation();
      const user = getUser() as any;
      if (!user || (user.id === undefined || user.id === null)) {
        showToast("Sign in to manage favorites", "error");
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
        showToast(
          err instanceof Error ? err.message : "Could not update favorite",
          "error",
        );
      }
      return;
    }

    // Vote up/down → setVote (backend toggles same value off); repaint from the
    // authoritative tally it returns.
    const voteBtn = target.closest<HTMLElement>(
      '[data-action="vote-up"], [data-action="vote-down"]',
    );
    if (voteBtn) {
      e.preventDefault();
      e.stopPropagation();
      const user = getUser() as any;
      if (!user || user.id === undefined || user.id === null) {
        showToast("Sign in to vote", "error");
        return;
      }
      const id = Number(voteBtn.dataset.id);
      const value: VoteValue =
        voteBtn.dataset.action === "vote-up" ? "POSITIVE" : "NEGATIVE";
      const scope = voteBtn.closest<HTMLElement>("[data-vote-bar]");
      // Debounce: coalesce a burst of rapid clicks into one request.
      if (scope) queueVote(scope, Number(user.id), id, value);
      return;
    }

    // Discuss → open the read-only detail view focused on the discussion (foro)
    // section. Reuses the whole-card open path but flags `data-foro-focus` so the
    // foro controller scrolls to + focuses the comment composer.
    const discussBtn = target.closest<HTMLElement>('[data-action="discuss"]');
    if (discussBtn) {
      e.preventDefault();
      e.stopPropagation();
      const card = discussBtn.closest<HTMLElement>("[data-card]");
      const openModal = card?.dataset.detailModal;
      if (card && openModal && card.dataset.id) {
        const synthetic = document.createElement("button");
        synthetic.style.display = "none";
        synthetic.setAttribute("data-modal-open", openModal);
        synthetic.setAttribute("data-asset-id", card.dataset.id);
        synthetic.setAttribute("data-foro-focus", "1");
        document.body.appendChild(synthetic);
        synthetic.click();
        synthetic.remove();
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
        showToast(okMsg, "success");
      } catch {
        showToast("Could not copy", "error");
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
