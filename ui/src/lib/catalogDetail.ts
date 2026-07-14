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
import { getVoteTally, setVote, getWorkflowStage, type VoteValue } from "@/lib/actions";
import { mountRelated } from "@/lib/related";
import { mountHistory } from "@/lib/history";
import { mountVersions } from "@/lib/versions";
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

/** Module-level i18n lookup (the detail controller's inner `tr` is scoped to
 * mountCatalogDetail; the shared renderer below and other consumers use this). */
function trGlobal(key: string, fallback: string): string {
  try {
    const lang = (typeof localStorage !== "undefined" && localStorage.getItem("lang")) || "en";
    const w = window as any;
    if (typeof w.t === "function") return w.t(key, lang) || fallback;
  } catch {
    /* non-fatal */
  }
  return fallback;
}

function labelEl(text: string): HTMLElement {
  const h = document.createElement("h4");
  h.className = "mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400";
  h.textContent = text;
  return h;
}

/** Build one section's DOM node from its raw value (inline meta / prose block /
 * copyable code / tool chips). Pure + XSS-safe (all text via textContent). */
function renderSection(sec: DetailSection, value: string): HTMLElement | null {
  const v = (value ?? "").trim();
  if (!v && sec.type !== "tools") return null;
  const label = trGlobal(sec.labelKey, sec.labelKey);

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
    copyBtn.dataset.copyOk = trGlobal(sec.copyOkKey ?? "catalog_detail.copied", "Copied");
    copyBtn.className =
      "inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800";
    copyBtn.textContent = trGlobal("catalog_detail.copy", "Copy");
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

/** Render a configured section list into `container` from a feature→char map
 * (the same rendering the Detail tab uses). Reused by the Versions tab to show
 * a historical version's snapshot identically. `description` feeds any section
 * with `field: "description"`. */
export function renderCharacterizationSections(
  container: HTMLElement,
  sections: DetailSection[],
  byFeature: Record<string, { value?: string; detail?: string } | undefined>,
  description = "",
): void {
  container.innerHTML = "";
  for (const sec of sections) {
    const raw =
      sec.field === "description"
        ? description
        : ((byFeature[sec.feature ?? ""]?.[sec.column ?? "value"] as string) ?? "");
    const el = renderSection(sec, raw);
    if (el) container.appendChild(el);
  }
}

export function mountCatalogDetail(cfg: CatalogDetailConfig): void {
  if (typeof window === "undefined") return;
  const { modalId, sections } = cfg;

  const dialog = document.getElementById(modalId) as HTMLDialogElement | null;
  if (!dialog) return;

  // ── Tabs (Detail / Discussion / Activity) ──────────────────────────────────
  // The body is split into one panel per tab; switching just toggles the active
  // button styling + which panel is visible. All three sections still hydrate on
  // open regardless of the active tab (they query by scoped id).
  const tabButtons = Array.from(
    dialog.querySelectorAll<HTMLButtonElement>("[data-detail-tab]"),
  );
  const tabPanels = Array.from(
    dialog.querySelectorAll<HTMLElement>("[data-detail-panel]"),
  );

  function activateTab(name: string): void {
    for (const btn of tabButtons) {
      const on = btn.dataset.detailTab === name;
      btn.setAttribute("aria-selected", String(on));
      if (on) btn.removeAttribute("tabindex");
      else btn.setAttribute("tabindex", "-1");
      btn.classList.toggle("border-indigo-600", on);
      btn.classList.toggle("text-indigo-600", on);
      btn.classList.toggle("dark:text-indigo-400", on);
      btn.classList.toggle("border-transparent", !on);
      btn.classList.toggle("text-gray-500", !on);
      btn.classList.toggle("hover:border-gray-300", !on);
      btn.classList.toggle("hover:text-gray-700", !on);
      btn.classList.toggle("dark:text-gray-400", !on);
      btn.classList.toggle("dark:hover:text-gray-200", !on);
    }
    for (const panel of tabPanels) {
      panel.classList.toggle("hidden", panel.dataset.detailPanel !== name);
    }
  }

  for (const btn of tabButtons) {
    btn.addEventListener("click", () => activateTab(btn.dataset.detailTab || "detail"));
  }

  // Hydrate the read-only related-assets section (HU-LI07) and the read-only
  // activity timeline (HU-LI10). Each is self-contained: it hooks the same open
  // trigger and queries within `#${modalId}-related` / `-history`. The discussion
  // section (HU-LI06) is now the `Foro` Svelte island, which self-mounts from
  // Foro.astro and hooks the same trigger on its own — no wiring needed here.
  mountRelated({ modalId });
  mountHistory({ modalId });
  mountVersions({ modalId, sections });

  const nameEl = document.getElementById(`${modalId}-name`) as HTMLElement | null;
  const statusPill = document.getElementById(`${modalId}-status-pill`) as HTMLElement | null;
  const versionPill = document.getElementById(`${modalId}-version-pill`) as HTMLElement | null;
  const stagePill = document.getElementById(`${modalId}-stage-pill`) as HTMLElement | null;
  const descEl = document.getElementById(`${modalId}-desc`) as HTMLElement | null;
  const sectionsEl = document.getElementById(`${modalId}-sections`) as HTMLElement | null;
  const favBtn = document.getElementById(`${modalId}-fav`) as HTMLButtonElement | null;
  const favSvg = favBtn?.querySelector("svg") as SVGElement | null;
  const voteWrap = document.getElementById(`${modalId}-vote`) as HTMLElement | null;
  const voteUp = document.getElementById(`${modalId}-vote-up`) as HTMLButtonElement | null;
  const voteDown = document.getElementById(`${modalId}-vote-down`) as HTMLButtonElement | null;
  const voteUpCount = document.getElementById(`${modalId}-vote-up-count`) as HTMLElement | null;
  const voteDownCount = document.getElementById(`${modalId}-vote-down-count`) as HTMLElement | null;

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
  // Bumped on every open(); async loads capture it and bail if it changed,
  // so a slow response for a previously-viewed asset can't paint over the one
  // now shown (related-asset clicks re-open this same modal in place).
  let openSeq = 0;

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
    if (voteUpCount) voteUpCount.textContent = String(tally.positive);
    if (voteDownCount) voteDownCount.textContent = String(tally.negative);
    // Keep the matching gallery card's vote bar in sync.
    const card = document.querySelector<HTMLElement>(`[data-card][data-id="${currentId}"] [data-vote-bar]`);
    if (card) {
      styleVoteButton(
        card.querySelector<HTMLElement>('[data-action="vote-up"]'),
        upOn, "gallery.vote_up", "text-emerald-500");
      styleVoteButton(
        card.querySelector<HTMLElement>('[data-action="vote-down"]'),
        downOn, "gallery.vote_down", "text-rose-500");
      const cUp = card.querySelector<HTMLElement>("[data-vote-up-count]");
      const cDown = card.querySelector<HTMLElement>("[data-vote-down-count]");
      if (cUp) cUp.textContent = String(tally.positive);
      if (cDown) cDown.textContent = String(tally.negative);
    }
  }

  let voteTimer: ReturnType<typeof setTimeout> | null = null;
  const VOTE_DEBOUNCE_MS = 300;

  async function sendVote(value: VoteValue) {
    // In-flight guard (DOM-level, survives a double-bound listener) serializes
    // any still-overlapping request.
    if (voteWrap?.dataset.voting === "1") return;
    const user = getUser() as any;
    if ((!user?.id && user?.id !== 0) || !currentId) return;
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

  // Debounce: a burst of rapid clicks coalesces into a single request that fires
  // ~300ms after clicking pauses, so continuous clicking no longer floods the
  // API with POST /votes.
  function castVote(value: VoteValue) {
    const user = getUser() as any;
    if ((!user?.id && user?.id !== 0) || !currentId) {
      (window as any).showToast?.("Sign in to vote", "error");
      return;
    }
    if (voteTimer) clearTimeout(voteTimer);
    voteTimer = setTimeout(() => {
      voteTimer = null;
      void sendVote(value);
    }, VOTE_DEBOUNCE_MS);
  }

  voteUp?.addEventListener("click", () => castVote("POSITIVE"));
  voteDown?.addEventListener("click", () => castVote("NEGATIVE"));

  async function open(assetId: number) {
    const seq = ++openSeq;
    currentId = assetId;
    favoriteOn = false;
    paintFavorite();
    activateTab("detail"); // every open starts on the Detail tab
    if (nameEl) nameEl.textContent = "…";
    if (descEl) descEl.classList.add("hidden");
    if (sectionsEl) sectionsEl.innerHTML = "";
    if (statusPill) statusPill.classList.add("hidden");
    if (versionPill) versionPill.classList.add("hidden");
    if (stagePill) stagePill.classList.add("hidden");
    // Guard: a related-asset click re-opens this same modal in place, so the
    // dialog may already be open — calling showModal() twice would throw.
    // The scrollable element is the inner body, not the <dialog> itself.
    if (!dialog!.open) dialog!.showModal();
    else (dialog!.querySelector(".overflow-y-auto") as HTMLElement | null)?.scrollTo({ top: 0 });

    // Review-stage badge (latest workflow action) — distinct from asset.status.
    if (stagePill && currentId) {
      getWorkflowStage(currentId)
        .then((stage) => {
          if (seq !== openSeq || !stage) return; // a newer open() superseded this
          // The badge surfaces *pending* review activity. Once the latest action
          // is FINISHED it just echoes the status pill (a published asset's
          // PUBLICATION·FINISHED == "Published"), so hide it for finished stages —
          // it only shows while an asset is still moving through review.
          if (stage.workflow_status === "FINISHED") return;
          const typeLabel = tr(`workflow_stage.${stage.type}`, stage.type);
          const statusLabel = stage.workflow_status
            ? tr(`workflow_stage.${stage.workflow_status}`, stage.workflow_status)
            : "";
          stagePill.textContent = statusLabel ? `${typeLabel} · ${statusLabel}` : typeLabel;
          stagePill.classList.remove("hidden");
          stagePill.classList.add("inline-flex");
        })
        .catch(() => {});
    }

    const user = getUser() as any;
    if ((user?.id || user?.id === 0) && currentId) {
      isFavorite(Number(user.id), currentId)
        .then((on) => {
          if (seq !== openSeq) return;
          favoriteOn = on;
          paintFavorite();
        })
        .catch(() => {});
    }

    // Vote tally (counts + the current user's vote, resolved server-side).
    if (voteWrap) {
      voteWrap.classList.remove("hidden");
      voteWrap.classList.add("flex");
      if (voteUpCount) voteUpCount.textContent = "0";
      if (voteDownCount) voteDownCount.textContent = "0";
      getVoteTally(currentId)
        .then((tally) => {
          if (seq !== openSeq) return;
          paintVote(tally);
        })
        .catch(() => {});
    }

    try {
      const asset = await getAsset(assetId);
      if (seq !== openSeq) return; // superseded by a newer open()
      currentName = asset.name ?? "";
      if (nameEl) nameEl.textContent = currentName || "—";

      if (versionPill) {
        versionPill.textContent = `v${asset.current_version ?? "1.0.0"}`;
        versionPill.classList.remove("hidden");
      }

      if (statusPill) {
        const label = resolveStatusLabel(asset.status ?? "");
        if (label) {
          statusPill.textContent = label;
          statusPill.className =
            "inline-flex w-fit items-center rounded-full px-2.5 py-0.5 text-xs font-medium " +
            statusTone(asset.status || label);
        } else {
          statusPill.classList.add("hidden");
        }
      }

      const chars = await getCharacterizationsByAsset(assetId);
      if (seq !== openSeq) return; // superseded by a newer open()
      const byFeature = Object.fromEntries(chars.map((c) => [c.feature, c]));

      if (descEl) {
        const desc = (asset.description ?? "").trim();
        descEl.textContent = desc;
        descEl.classList.toggle("hidden", !desc);
      }

      if (sectionsEl) {
        renderCharacterizationSections(
          sectionsEl, sections, byFeature, asset.description ?? "");
      }
    } catch {
      if (nameEl) nameEl.textContent = tr("catalog_detail.error_load", "Could not load.");
    }
  }

  function close() {
    if (voteTimer) {
      clearTimeout(voteTimer);
      voteTimer = null;
    }
    dialog!.close();
  }

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
      // The card's discuss shortcut carries data-foro-focus → land on the
      // Discussion tab (foro.ts then scrolls + focuses the composer).
      if ((opener as HTMLElement).dataset.foroFocus) activateTab("discussion");
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
