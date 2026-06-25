/**
 * history — the asset "activity timeline" feature (HU-LI10): a read-only,
 * newest-first log of everything that happened to an asset (creation, votes,
 * comments, questions, answers, and any review-workflow actions).
 *
 * Backed by the read-side of the Asset Action Service through
 * `/api/actions/history/asset/{id}` (one call, actors resolved server-side with
 * a batched query — no N+1) — no new table. Display only; all asset-supplied
 * text is rendered with `textContent` (XSS-safe), mirroring the foro renderers.
 *
 * `mountHistory` is self-contained: it listens for the same open trigger the
 * detail controller uses (`[data-modal-open=…]`) and loads the timeline for the
 * opened asset. Call once per detail modal (mountCatalogDetail does this).
 */
import { apiGet, buildQueryString } from "./api";
import { formatRelative } from "./datatable";
import { translate } from "@/utils/i18nClient";
import type { HistoryEntry } from "@/types/api";

// ── Service ──────────────────────────────────────────────────────────────────

/** An asset's activity timeline, newest first (includes the CREATED marker). */
export async function getAssetHistory(
  assetId: number,
  skip = 0,
  limit = 100,
): Promise<HistoryEntry[]> {
  return apiGet<HistoryEntry[]>(
    `/api/actions/history/asset/${encodeURIComponent(String(assetId))}${buildQueryString({ skip, limit })}`,
  );
}

// ── Controller (hydrates the timeline section in CatalogDetailModal) ──────────

interface HistoryConfig {
  /** The detail dialog id, e.g. "mcp-view-modal". The shell lives at
   * `#${modalId}-history` (rendered by HistoryTimeline.astro). */
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

const locale = (): string =>
  (typeof localStorage !== "undefined" && localStorage.getItem("lang")) || "en";

// A small per-type accent for the timeline dot, for at-a-glance scanning.
const DOT_COLORS: Record<string, string> = {
  VOTE: "bg-emerald-400",
  COMMENT: "bg-indigo-400",
  QUESTION: "bg-amber-400",
  ANSWER: "bg-sky-400",
  CREATED: "bg-gray-400",
};

export function mountHistory(cfg: HistoryConfig): void {
  if (typeof window === "undefined") return;
  const { modalId } = cfg;

  const root = document.getElementById(`${modalId}-history`);
  if (!root) return;

  const listEl = root.querySelector<HTMLElement>("[data-history-list]");
  const statusEl = root.querySelector<HTMLElement>("[data-history-status]");

  const setStatus = (text: string) => {
    if (!statusEl) return;
    statusEl.textContent = text;
    statusEl.classList.toggle("hidden", !text);
  };

  const actionLabel = (e: HistoryEntry): string =>
    tr(`history.action.${e.type}`, e.summary || e.type.toLowerCase());

  // ── Renderer (actor + content via textContent — XSS-safe) ──────────────────
  function entryNode(e: HistoryEntry): HTMLElement {
    const row = document.createElement("div");
    row.className = "flex gap-3 py-1.5";

    const dot = document.createElement("span");
    dot.className = `mt-1.5 h-2 w-2 shrink-0 rounded-full ${DOT_COLORS[e.type] ?? "bg-gray-400"}`;
    row.appendChild(dot);

    const body = document.createElement("div");
    body.className = "min-w-0 flex-1";

    const line = document.createElement("p");
    line.className = "text-sm text-gray-700 dark:text-gray-300";
    if (e.actor) {
      const who = document.createElement("span");
      who.className = "font-semibold text-gray-900 dark:text-gray-100";
      who.textContent = e.actor;
      line.append(who, document.createTextNode(` ${actionLabel(e)}`));
    } else {
      // No actor (e.g. the synthetic CREATED marker).
      line.textContent = actionLabel(e);
    }
    const when = document.createElement("span");
    when.className = "text-xs text-gray-400 dark:text-gray-500";
    when.textContent = ` · ${formatRelative(e.created_at, locale())}`;
    line.appendChild(when);
    body.appendChild(line);

    const content = (e.content || "").trim();
    if (content) {
      const p = document.createElement("p");
      p.className = "mt-0.5 line-clamp-2 break-words text-xs text-gray-500 dark:text-gray-400";
      p.textContent = content;
      body.appendChild(p);
    }

    row.appendChild(body);
    return row;
  }

  async function load(id: number) {
    if (!listEl) return;
    listEl.innerHTML = "";
    setStatus(tr("history.loading", "Loading activity…"));
    try {
      const items = await getAssetHistory(id);
      setStatus("");
      if (!items.length) {
        setStatus(tr("history.empty", "No activity yet."));
        return;
      }
      for (const it of items) listEl.appendChild(entryNode(it));
    } catch {
      setStatus(tr("history.error", "Could not load the activity."));
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
