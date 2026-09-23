/**
 * usageTracking (HU-LI07) — the write + read side of asset usage, shared by the
 * two detail modals that render copyable characteristics: the read-only Explore
 * modal (`catalogDetail.ts`) and the editable Asset Management modal
 * (`AssetDetailModal.astro`).
 *
 * A "use" is one copy of a copyable characteristic's value. Clicking Copy does
 * three things: copy to the clipboard, toast the confirmation, and POST a USAGE
 * action. The count is then repainted into a pill that sits under the modal
 * title beside the version.
 *
 * Failing to record usage never fails the copy. Usage is telemetry: the user
 * asked for the text, they got the text, and a lost count is a far smaller
 * problem than an error toast on a copy that actually worked.
 *
 * USAGE actions are deliberately excluded from the History timeline server-side
 * (`HISTORY_EXCLUDED_TYPES`) — one row per copy would bury the asset's real
 * lifecycle under noise. The pill is where that data surfaces instead.
 */
import { getUsageTally, recordUsage } from "@/lib/actions";
import { showToast } from "@/lib/toast";
import { translate } from "@/utils/i18nClient";

const tr = (key: string, fallback: string): string => {
  try {
    const v = translate(key);
    if (v && v !== key) return v;
  } catch {
    /* i18n not ready — fall back */
  }
  return fallback;
};

/** Inline "copy/usage" glyph for the pill (matches the Copy button's meaning). */
const USAGE_ICON =
  `<svg class="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="9" y="9" width="11" height="11" rx="2" /><path d="M5 15V5a2 2 0 0 1 2-2h10" stroke-linecap="round" /></svg>`;

/**
 * Paint the usage count into its pill. `count === null` hides the pill (no
 * asset loaded, or the count could not be read — showing a stale or invented
 * number would be worse than showing none).
 */
export function paintUsagePill(pill: HTMLElement | null, count: number | null): void {
  if (!pill) return;
  // `hidden` and `inline-flex` both set `display`, so they are toggled as a
  // pair — leaving `inline-flex` on a hidden pill (or off a shown one) would
  // either defeat the hide or drop the icon/number alignment.
  if (count === null) {
    pill.classList.add("hidden");
    pill.classList.remove("inline-flex");
    pill.textContent = "";
    return;
  }
  const label = tr("usage.pill_title", "Times this asset has been used");
  pill.innerHTML = USAGE_ICON;
  const n = document.createElement("span");
  n.textContent = String(count);
  pill.appendChild(n);
  pill.title = label;
  pill.setAttribute("aria-label", `${label}: ${count}`);
  pill.classList.remove("hidden");
  pill.classList.add("inline-flex");
}

export interface UsageTrackingConfig {
  /** The element the copy buttons live inside — normally the modal `<dialog>`.
   * The click handler is delegated from here, so re-rendered sections keep
   * working without re-binding. */
  root: HTMLElement;
  /** The count pill, or null when this surface doesn't show one. */
  pill: HTMLElement | null;
  /** The asset currently open in the modal, or null when none is. Read at
   * click time — the modal is reused across assets. */
  currentAssetId: () => number | null;
}

export interface UsageTracker {
  /** Load and paint the count for an asset (or clear it when null). Call this
   * whenever the modal opens or switches asset. */
  refresh: (assetId: number | null) => Promise<void>;
}

/**
 * Wire copy-to-clipboard + usage recording on every `[data-action="copy"]`
 * button inside `root`, and keep `pill` in sync. Returns a `refresh` the caller
 * uses to (re)load the count when the modal opens.
 */
export function mountUsageTracking(cfg: UsageTrackingConfig): UsageTracker {
  const { root, pill, currentAssetId } = cfg;
  // Bumped on every refresh(); an in-flight count for a previously-open asset
  // bails instead of painting over the one now shown (the modal is reused,
  // and a related-asset click re-opens it in place).
  let seq = 0;

  async function refresh(assetId: number | null): Promise<void> {
    const mine = ++seq;
    if (assetId == null) {
      paintUsagePill(pill, null);
      return;
    }
    try {
      const tally = await getUsageTally(assetId);
      if (mine !== seq) return;
      paintUsagePill(pill, tally.count ?? 0);
    } catch {
      // Keep the pill hidden rather than showing a wrong number.
      if (mine !== seq) return;
      paintUsagePill(pill, null);
    }
  }

  root.addEventListener("click", async (e) => {
    const btn = (e.target as HTMLElement).closest<HTMLElement>('[data-action="copy"]');
    if (!btn || !root.contains(btn)) return;
    e.preventDefault();

    try {
      await navigator.clipboard.writeText(btn.dataset.copy ?? "");
    } catch {
      showToast(tr("catalog_detail.copy_error", "Could not copy"), "error");
      return; // nothing was consumed — don't record a use
    }
    showToast(btn.dataset.copyOk || tr("catalog_detail.copied", "Copied"), "success");

    const assetId = currentAssetId();
    if (assetId == null) return;
    const mine = seq;
    try {
      const tally = await recordUsage(assetId, btn.dataset.feature ?? null);
      if (mine !== seq) return; // modal moved on to another asset
      paintUsagePill(pill, tally.count ?? 0);
    } catch {
      /* telemetry only — the copy already succeeded, so stay silent */
    }
  });

  return { refresh };
}
