/**
 * catalogDetail — client controller for the reusable read-only "big card" view
 * (CatalogDetailModal.astro). Opened from a whole-card click via the gallery
 * controller (the card carries `data-detail-modal`), it hydrates on demand:
 * fetches the asset + its characterizations, renders the full description and a
 * configured list of sections (inline meta, prose blocks, code blocks with a
 * Copy button, tool chips), and wires the favorite star + Edit/Delete handoff.
 *
 * Catalog-agnostic: each catalog passes its own `sections` describing which
 * characterization feature feeds each block and from which column (`value` for
 * short fields, `detail` for the rich payload — matching the seed).
 */
import { getAsset } from "@/lib/assets";
import { getCharacterizationsByAsset } from "@/lib/characterizations";
import { isFavorite, setFavorite } from "@/lib/favorites";
import { getVoteTally, setVote, type VoteValue } from "@/lib/actions";
import { styleVoteButton } from "@/lib/catalogGallery";
import { getUser } from "@/lib/auth";
import { statusTone } from "@/lib/datatable";
import type { VoteTally } from "@/types/api";

export interface DetailSection {
  /** inline = "label: value"; block = prose; code = monospace + copy; tools = chips. */
  type: "inline" | "block" | "code" | "tools";
  /** i18n key for the section label. */
  labelKey: string;
  /** Characterization feature code feeding this section. */
  feature?: string;
  /** Which characterization column to read (default "value"). */
  column?: "value" | "detail";
  /** Pull from the asset's own `description` instead of a characterization. */
  field?: "description";
  /** i18n key for the "copied" toast on a code section's Copy button. */
  copyOkKey?: string;
}

export interface CatalogDetailConfig {
  /** Dialog id, e.g. "prompt-view-modal". */
  modalId: string;
  /** Edit form dialog id opened by the footer's Edit button, e.g. "prompt-detail-modal". */
  editModalId: string;
  /** Ordered sections to render. */
  sections: DetailSection[];
}

/** Tolerant list parser: `['a','b']`, `["a"]`, comma/newline text → string[]. */
function parseList(raw: unknown): string[] {
  if (!raw) return [];
  let s = String(raw).trim();
  if (s.startsWith("[") && s.endsWith("]")) s = s.slice(1, -1);
  return s
    .split(/[,\n]/)
    .map((t) => t.trim().replace(/^['"]|['"]$/g, "").trim())
    .filter(Boolean);
}

export function mountCatalogDetail(cfg: CatalogDetailConfig): void {
  if (typeof window === "undefined") return;
  const { modalId, editModalId, sections } = cfg;

  const dialog = document.getElementById(modalId) as HTMLDialogElement | null;
  if (!dialog) return;

  const nameEl = document.getElementById(`${modalId}-name`) as HTMLElement | null;
  const statusPill = document.getElementById(`${modalId}-status-pill`) as HTMLElement | null;
  const descEl = document.getElementById(`${modalId}-desc`) as HTMLElement | null;
  const sectionsEl = document.getElementById(`${modalId}-sections`) as HTMLElement | null;
  const favBtn = document.getElementById(`${modalId}-fav`) as HTMLButtonElement | null;
  const favSvg = favBtn?.querySelector("svg") as SVGElement | null;
  const editBtn = document.getElementById(`${modalId}-edit`) as HTMLButtonElement | null;
  const deleteBtn = document.getElementById(`${modalId}-delete`) as HTMLButtonElement | null;
  const voteWrap = document.getElementById(`${modalId}-vote`) as HTMLElement | null;
  const voteUp = document.getElementById(`${modalId}-vote-up`) as HTMLButtonElement | null;
  const voteDown = document.getElementById(`${modalId}-vote-down`) as HTMLButtonElement | null;
  const voteScore = document.getElementById(`${modalId}-vote-score`) as HTMLElement | null;

  let statuses: { value: string; label: string }[] = [];
  try {
    statuses = JSON.parse(document.getElementById(`${modalId}-statuses`)?.textContent || "[]");
  } catch {
    statuses = [];
  }

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

  const resolveStatusLabel = (raw: string): string => {
    if (!raw) return "";
    const direct = statuses.find((s) => s.value === raw);
    if (direct) return direct.label;
    const stripped = statuses.find((s) => s.value.replace(/^\d+-/, "") === raw);
    return stripped?.label ?? raw;
  };

  let currentId: number | null = null;
  let currentName = "";
  let favoriteOn = false;

  function paintFavorite() {
    if (!favBtn || !favSvg) return;
    favBtn.setAttribute("aria-pressed", String(favoriteOn));
    favSvg.setAttribute("fill", favoriteOn ? "currentColor" : "none");
    favBtn.classList.toggle("text-yellow-400", favoriteOn);
  }

  favBtn?.addEventListener("click", async () => {
    const user = getUser() as any;
    if ((!user?.id && user?.id !== 0) || !currentId) return;
    const next = !favoriteOn;
    favoriteOn = next;
    paintFavorite();
    try {
      await setFavorite(Number(user.id), currentId, next);
      // Keep the matching gallery card star in sync.
      const card = document.querySelector<HTMLElement>(`[data-card][data-id="${currentId}"]`);
      const star = card?.querySelector<HTMLElement>('[data-action="favorite"]');
      if (card) card.dataset.favorite = next ? "yes" : "no";
      if (star) {
        star.setAttribute("aria-pressed", String(next));
        star.classList.toggle("text-yellow-400", next);
        star.querySelector("svg")?.setAttribute("fill", next ? "currentColor" : "none");
      }
    } catch {
      favoriteOn = !next; // revert
      paintFavorite();
    }
  });

  // ── Vote bar ───────────────────────────────────────────────────────────────
  function paintVote(tally: VoteTally) {
    const upOn = tally.my_vote === "POSITIVE";
    const downOn = tally.my_vote === "NEGATIVE";
    styleVoteButton(voteUp, upOn, "gallery.vote_up", "text-emerald-500");
    styleVoteButton(voteDown, downOn, "gallery.vote_down", "text-rose-500");
    if (voteScore) voteScore.textContent = String(tally.score);
    // Keep the matching gallery card's vote bar in sync.
    const card = document.querySelector<HTMLElement>(`[data-card][data-id="${currentId}"] [data-vote-bar]`);
    if (card) {
      styleVoteButton(
        card.querySelector<HTMLElement>('[data-action="vote-up"]'),
        upOn, "gallery.vote_up", "text-emerald-500");
      styleVoteButton(
        card.querySelector<HTMLElement>('[data-action="vote-down"]'),
        downOn, "gallery.vote_down", "text-rose-500");
      const cScore = card.querySelector<HTMLElement>("[data-vote-score]");
      if (cScore) cScore.textContent = String(tally.score);
    }
  }

  async function castVote(value: VoteValue) {
    // Bouncer: ignore clicks while a vote request is already in flight (guards
    // against rapid double-clicks — and survives a listener bound more than
    // once — because the flag lives on the DOM node, not a closure).
    if (voteWrap?.dataset.voting === "1") return;
    const user = getUser() as any;
    if ((!user?.id && user?.id !== 0) || !currentId) {
      (window as any).showToast?.("Sign in to vote", "error");
      return;
    }
    if (voteWrap) voteWrap.dataset.voting = "1";
    try {
      const tally = await setVote(Number(user.id), currentId, value);
      paintVote(tally);
    } catch (err) {
      (window as any).showToast?.(
        err instanceof Error ? err.message : "Could not register your vote",
        "error",
      );
      // Re-sync from the authoritative tally so a failed vote never leaves the
      // bar (and the mirrored card) in a stale state.
      getVoteTally(currentId)
        .then((tally) => paintVote(tally))
        .catch(() => {});
    } finally {
      if (voteWrap) delete voteWrap.dataset.voting;
    }
  }

  voteUp?.addEventListener("click", () => castVote("POSITIVE"));
  voteDown?.addEventListener("click", () => castVote("NEGATIVE"));

  // ── Section renderers ──────────────────────────────────────────────────────
  function labelEl(text: string): HTMLElement {
    const h = document.createElement("h4");
    h.className = "mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400";
    h.textContent = text;
    return h;
  }

  function renderSection(sec: DetailSection, value: string): HTMLElement | null {
    const v = (value ?? "").trim();
    if (!v && sec.type !== "tools") return null;
    const label = tr(sec.labelKey, sec.labelKey);

    if (sec.type === "inline") {
      const row = document.createElement("div");
      row.className = "flex flex-wrap items-baseline gap-2 text-sm";
      const l = document.createElement("span");
      l.className = "font-medium text-gray-500 dark:text-gray-400";
      l.textContent = `${label}:`;
      const val = document.createElement("span");
      val.className = "text-gray-900 dark:text-gray-100";
      val.textContent = v;
      row.append(l, val);
      return row;
    }

    if (sec.type === "tools") {
      const items = parseList(v);
      if (items.length === 0) return null;
      const wrap = document.createElement("div");
      wrap.appendChild(labelEl(label));
      const chips = document.createElement("div");
      chips.className = "flex flex-wrap gap-1.5";
      for (const t of items) {
        const chip = document.createElement("span");
        chip.className =
          "inline-flex items-center rounded-md bg-gray-100 px-2 py-0.5 text-xs text-gray-700 dark:bg-gray-800 dark:text-gray-300";
        chip.textContent = t;
        chips.appendChild(chip);
      }
      wrap.appendChild(chips);
      return wrap;
    }

    if (sec.type === "code") {
      const wrap = document.createElement("div");
      const head = document.createElement("div");
      head.className = "mb-2 flex items-center justify-between gap-2";
      head.appendChild(labelEl(label));
      const copyBtn = document.createElement("button");
      copyBtn.type = "button";
      copyBtn.dataset.action = "copy";
      copyBtn.dataset.copy = v;
      copyBtn.dataset.copyOk = tr(sec.copyOkKey ?? "catalog_detail.copied", "Copied");
      copyBtn.className =
        "inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800";
      copyBtn.textContent = tr("catalog_detail.copy", "Copy");
      head.appendChild(copyBtn);
      wrap.appendChild(head);
      const pre = document.createElement("pre");
      pre.className =
        "max-h-80 overflow-auto whitespace-pre-wrap break-words rounded-lg bg-gray-50 p-3 font-mono text-xs text-gray-800 dark:bg-gray-800 dark:text-gray-200";
      pre.textContent = v;
      wrap.appendChild(pre);
      return wrap;
    }

    // block
    const wrap = document.createElement("div");
    wrap.appendChild(labelEl(label));
    const p = document.createElement("p");
    p.className = "whitespace-pre-wrap text-sm text-gray-700 dark:text-gray-300";
    p.textContent = v;
    wrap.appendChild(p);
    return wrap;
  }

  async function open(assetId: number) {
    currentId = assetId;
    favoriteOn = false;
    paintFavorite();
    if (nameEl) nameEl.textContent = "…";
    if (descEl) descEl.classList.add("hidden");
    if (sectionsEl) sectionsEl.innerHTML = "";
    if (statusPill) statusPill.classList.add("hidden");
    dialog!.showModal();

    const user = getUser() as any;
    if ((user?.id || user?.id === 0) && currentId) {
      isFavorite(Number(user.id), currentId)
        .then((on) => {
          favoriteOn = on;
          paintFavorite();
        })
        .catch(() => {});
    }

    // Vote tally (counts + the current user's vote, resolved server-side).
    if (voteWrap) {
      voteWrap.classList.remove("hidden");
      voteWrap.classList.add("flex");
      if (voteScore) voteScore.textContent = "0";
      getVoteTally(currentId)
        .then((tally) => paintVote(tally))
        .catch(() => {});
    }

    try {
      const asset = await getAsset(assetId);
      currentName = asset.name ?? "";
      if (nameEl) nameEl.textContent = currentName || "—";

      if (statusPill) {
        const label = resolveStatusLabel(asset.status ?? "");
        if (label) {
          statusPill.textContent = label;
          statusPill.className =
            "mt-1 inline-flex w-fit items-center rounded-full px-2.5 py-0.5 text-xs font-medium " +
            statusTone(asset.status || label);
        } else {
          statusPill.classList.add("hidden");
        }
      }

      const chars = await getCharacterizationsByAsset(assetId);
      const byFeature = Object.fromEntries(chars.map((c) => [c.feature, c]));

      if (descEl) {
        const desc = (asset.description ?? "").trim();
        descEl.textContent = desc;
        descEl.classList.toggle("hidden", !desc);
      }

      if (sectionsEl) {
        for (const sec of sections) {
          const raw =
            sec.field === "description"
              ? (asset.description ?? "")
              : ((byFeature[sec.feature ?? ""]?.[sec.column ?? "value"] as string) ?? "");
          const el = renderSection(sec, raw);
          if (el) sectionsEl.appendChild(el);
        }
      }
    } catch {
      if (nameEl) nameEl.textContent = tr("catalog_detail.error_load", "Could not load.");
    }
  }

  function close() {
    dialog!.close();
  }

  // ── Footer actions ─────────────────────────────────────────────────────────
  editBtn?.addEventListener("click", () => {
    if (!currentId) return;
    const id = currentId;
    close();
    const synthetic = document.createElement("button");
    synthetic.style.display = "none";
    synthetic.setAttribute("data-modal-open", editModalId);
    synthetic.setAttribute("data-asset-mode", "edit");
    synthetic.setAttribute("data-asset-id", String(id));
    document.body.appendChild(synthetic);
    synthetic.click();
    synthetic.remove();
  });

  deleteBtn?.addEventListener("click", () => {
    if (!currentId) return;
    const id = currentId;
    const name = currentName;
    close();
    document.dispatchEvent(new CustomEvent("gallery-delete", { detail: { id, name } }));
  });

  // ── Copy buttons inside the dialog (the gallery copy handler is scoped to the
  //    grid root, which the dialog sits outside of). ──────────────────────────
  dialog.addEventListener("click", async (e) => {
    const copyBtn = (e.target as HTMLElement).closest<HTMLElement>('[data-action="copy"]');
    if (!copyBtn) return;
    e.preventDefault();
    try {
      await navigator.clipboard.writeText(copyBtn.dataset.copy ?? "");
      (window as any).showToast?.(copyBtn.dataset.copyOk || "Copied", "success");
    } catch {
      (window as any).showToast?.("Could not copy", "error");
    }
  });

  // ── Open / close wiring ──────────────────────────────────────────────────
  document.addEventListener("click", (e) => {
    const opener = (e.target as HTMLElement).closest?.(`[data-modal-open="${modalId}"]`);
    if (opener) {
      e.preventDefault();
      const assetId = (opener as HTMLElement).dataset.assetId;
      if (assetId) open(Number(assetId));
      return;
    }
    const closer = (e.target as HTMLElement).closest?.(`[data-modal-close="${modalId}"]`);
    if (closer) {
      e.preventDefault();
      close();
    }
  });

  dialog.addEventListener("cancel", (e) => {
    e.preventDefault();
    close();
  });
}
