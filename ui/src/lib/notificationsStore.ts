/**
 * notificationsStore — one client-side source of truth for the caller's asset
 * requests, shared by the header bell and the "My Asset Requests" page so the
 * two can never disagree.
 *
 * WHY THIS EXISTS. Before it, both surfaces loaded once and never again, which
 * went stale three different ways:
 *
 *   1. `history.back()` after deciding a review is served from the browser's
 *      back/forward cache, so the page is NOT re-executed — `onMount` never
 *      fires again and the bell keeps the list it loaded before the decision.
 *      `pageshow` is the only event that fires on a bfcache restore.
 *   2. A tab left open simply never reloaded.
 *   3. A change made by somebody else (a reviewer deciding your proposal)
 *      happens in a different browser entirely, where no navigation occurs.
 *      Only a timer reaches that case.
 *
 * Push (SSE/websockets) would be the obvious answer to (3) but is not available:
 * the API runs on serverless functions, which do not hold long-lived
 * connections. So this polls — gated on visibility, so a backgrounded tab costs
 * nothing.
 *
 * Deliberately framework-free: `ui/src/lib/*` holds services, and this must stay
 * callable from `.astro` shells as well as Svelte islands. Components subscribe
 * in `onMount` and assign into their own local `$state`.
 */
import { getAssetRequests, getNotifications } from "./notifications";
import type { AssetRequest, NotificationFeed } from "@/types/api";

/** How often to re-check while the tab is visible. Comfortably inside the 90 s
 *  the spec allows for converging on somebody else's change, without making a
 *  request a second. */
const POLL_MS = 60_000;

/** Dispatch this on `window` after any mutation that changes what the caller
 *  owes — acknowledging, deciding a review, resubmitting — for an instant
 *  refresh instead of waiting out the interval. */
export const CHANGED_EVENT = "notifications:changed";

export interface NotificationsState {
  feed: NotificationFeed;
  pending: AssetRequest[];
  handled: AssetRequest[];
  /** False until the first successful load, so callers can tell "nothing yet"
   *  from a genuinely empty list. */
  loaded: boolean;
}

type Listener = (state: NotificationsState) => void;

let state: NotificationsState = {
  feed: { items: [], total: 0 },
  pending: [],
  handled: [],
  loaded: false,
};

const listeners = new Set<Listener>();
let timer: ReturnType<typeof setInterval> | null = null;
let started = false;
let inFlight: Promise<void> | null = null;

function emit(): void {
  for (const fn of listeners) {
    try {
      fn(state);
    } catch {
      /* a broken subscriber must not take the others down */
    }
  }
}

function isVisible(): boolean {
  return typeof document === "undefined" || document.visibilityState !== "hidden";
}

/**
 * Re-read everything the caller owns.
 *
 * On failure the previous state is KEPT. Blanking the list on a transient
 * network error would tell the user they have no pending work, which is worse
 * than showing them a slightly stale truth — and it is exactly what the old
 * bell did with its `catch { items = [] }`.
 *
 * Concurrent calls share one request, so a focus event landing on top of a
 * timer tick does not double-fetch.
 */
export function refresh(): Promise<void> {
  if (inFlight) return inFlight;

  inFlight = (async () => {
    try {
      const [feed, pending, handled] = await Promise.all([
        getNotifications(),
        getAssetRequests("PENDING"),
        getAssetRequests("HANDLED"),
      ]);
      state = { feed, pending, handled, loaded: true };
      emit();
    } catch {
      /* keep the last known good state — see the note above */
    } finally {
      inFlight = null;
    }
  })();

  return inFlight;
}

function onVisibility(): void {
  if (isVisible()) {
    void refresh();
    startTimer();
  } else {
    stopTimer();
  }
}

/** A bfcache restore does not re-run the page, so this is the only signal that
 *  a back-navigation happened. `persisted` marks exactly that case. */
function onPageShow(event: PageTransitionEvent): void {
  if (event.persisted) void refresh();
}

function onChanged(): void {
  void refresh();
}

function startTimer(): void {
  if (timer !== null || !isVisible()) return;
  timer = setInterval(() => {
    if (isVisible()) void refresh();
  }, POLL_MS);
}

function stopTimer(): void {
  if (timer !== null) {
    clearInterval(timer);
    timer = null;
  }
}

/** Subscribe to state changes. The listener fires immediately with the current
 *  state so a late subscriber is never blank. Returns an unsubscribe function. */
export function subscribe(fn: Listener): () => void {
  listeners.add(fn);
  fn(state);
  return () => listeners.delete(fn);
}

/** Begin loading and keeping the state current. Idempotent — several islands
 *  may each call it on mount. */
export function start(): void {
  if (started) {
    void refresh();
    return;
  }
  started = true;

  if (typeof window !== "undefined") {
    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("pageshow", onPageShow);
    window.addEventListener(CHANGED_EVENT, onChanged);
  }

  void refresh();
  startTimer();
}

/** Stop polling and detach listeners. Only used when the last consumer goes
 *  away; in practice the header bell lives for the whole page. */
export function stop(): void {
  stopTimer();
  if (typeof window !== "undefined") {
    document.removeEventListener("visibilitychange", onVisibility);
    window.removeEventListener("pageshow", onPageShow);
    window.removeEventListener(CHANGED_EVENT, onChanged);
  }
  started = false;
}

/** Announce that the caller's pending set just changed, so every subscribed
 *  surface updates now rather than on the next tick. */
export function notifyChanged(): void {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent(CHANGED_EVENT));
  }
}
