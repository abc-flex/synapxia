/**
 * Sidebar navigation data — fetched per page load.
 *
 * IMPORTANT: this MUST be called client-side, not in Astro frontmatter (SSR).
 * The JWT lives in localStorage which the server can't read, so a server-side
 * call returns 401 → apiGet's SSR-fallback returns []. We cache the result in
 * localStorage so subsequent page loads render the menu before first paint.
 */
import { getModules } from "@/lib/modules";
import { getOptions } from "@/lib/options";
import type { NavModule, NavOption } from "@/types/nav";

export interface NavigationData {
  primaryNav: NavModule[];
  itemsNav: NavOption[];
}

const NAV_CACHE_KEY = "nav_cache";

/**
 * Read the previously-cached nav data synchronously. Used by the sidebar's
 * inline bootstrap script for an immediate render before the network refetch
 * completes.
 */
export function readNavCache(): NavigationData | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(NAV_CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as NavigationData;
    if (Array.isArray(parsed?.primaryNav) && Array.isArray(parsed?.itemsNav)) {
      return parsed;
    }
  } catch {
    /* fall through */
  }
  return null;
}

/**
 * Fetch modules + options from the API, normalize, and (when run client-side)
 * cache the result. Returns the shape the sidebar expects.
 */
export async function getNavigationData(): Promise<NavigationData> {
  const [modulesRaw, optionsRaw] = await Promise.all([
    getModules().catch(() => []),
    getOptions().catch(() => []),
  ]);

  const primaryNav: NavModule[] = modulesRaw.map((m: any) => ({
    code: m.code,
    name: m.name,
    icon: m.icon,
  }));

  const itemsNav: NavOption[] = optionsRaw.map((o: any) => ({
    module: o.module,
    code: o.code,
    name: o.name,
    path: o.path,
    icon: o.icon ?? null,
  }));

  const result: NavigationData = { primaryNav, itemsNav };

  // Cache only on the client AND only when we got real data (don't cache
  // empty results — that would defeat the purpose).
  if (typeof window !== "undefined" && (primaryNav.length || itemsNav.length)) {
    try {
      localStorage.setItem(NAV_CACHE_KEY, JSON.stringify(result));
    } catch {
      /* localStorage may be unavailable in some embeds — non-fatal */
    }
  }

  return result;
}

/**
 * Clear the cached nav data — call from logout so the next user doesn't
 * inherit the previous user's menu items.
 */
export function clearNavCache(): void {
  if (typeof window !== "undefined") {
    try {
      localStorage.removeItem(NAV_CACHE_KEY);
    } catch {
      /* non-fatal */
    }
  }
}
