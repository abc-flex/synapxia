/**
 * Unified API Service Library
 * Provides reusable HTTP methods for interacting with the FastAPI backend.
 *
 * Auth model:
 *   - Browser: an HTTP-only cookie `auth_token` is set by the API at login
 *     and auto-attached to every same-origin request (via the Vite proxy in
 *     dev / Vercel rewrite in prod). We send `credentials: "include"` to
 *     make sure cross-origin fallback still works.
 *   - Server (Astro frontmatter): cookies are not auto-attached because
 *     Node has no browser context. The Astro middleware extracts the
 *     cookie into AsyncLocalStorage; this module reads it and sends it as
 *     a Bearer header to the API (same JWT, just a different transport).
 */

import type { ApiError } from '../types/api';
import { clearToken, getToken, refreshAccessToken } from './auth';

/* ============================================================
   SSR context — AsyncLocalStorage of the current request's auth token.
   Only meaningful server-side; on the client it's a no-op shim so the
   bundler doesn't trip over `node:async_hooks`.
   ============================================================ */
type SsrCtx = { token?: string };
type AlsLike = { run: (v: SsrCtx, fn: () => any) => any; getStore: () => SsrCtx | undefined };

let _ssrContext: AlsLike = {
  run: (_v, fn) => fn(),
  getStore: () => undefined,
};

if (typeof window === 'undefined') {
  // Defer the import so client bundles never see `node:async_hooks`.
  // Top-level await in module scope is supported by Astro/Vite for SSR.
  // The TS errors below are silenced because @types/node isn't installed
  // (the UI is a browser-first project) and AsyncLocalStorage is only
  // accessed at runtime in the Node SSR pass.
  // @ts-expect-error -- no @types/node in this project; runtime-only import
  const { AsyncLocalStorage } = await import('node:async_hooks');
  _ssrContext = new AsyncLocalStorage() as AlsLike;
}

export const ssrContext: AlsLike = _ssrContext;

/**
 * fetchWithAuth — single source of truth for auth header injection +
 * silent-refresh-on-401 (browser only).
 */
async function fetchWithAuth(url: string, init: RequestInit): Promise<Response> {
  const buildInit = (): RequestInit => {
    const headers = new Headers(init.headers || {});

    if (typeof window === 'undefined') {
      // SSR: pull the JWT out of the request-scoped ALS (set by middleware
      // from the auth_token cookie) and forward as Bearer.
      const token = ssrContext.getStore()?.token;
      if (token) headers.set('Authorization', `Bearer ${token}`);
      return { ...init, headers };
    }

    // Client: the cookie auto-attaches on same-origin requests, but we
    // also keep the Bearer fallback for any legacy localStorage token
    // hanging around mid-migration. credentials:'include' is what
    // actually carries the cookie cross-origin.
    const token = getToken();
    if (token) headers.set('Authorization', `Bearer ${token}`);
    return { ...init, headers, credentials: 'include' };
  };

  let res = await fetch(url, buildInit());

  if (typeof window !== 'undefined' && res.status === 401) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      res = await fetch(url, buildInit());
    }
    if (res.status === 401) {
      clearToken();
      window.location.href = '/login';
    }
  }

  return res;
}

/* ============================================================
   Base URL
   - Browser: empty string → calls go to /api/... as relative paths
     and are forwarded to the API by the Vite proxy (dev) or Vercel
     rewrite (prod). One-origin model: cookies just work.
   - SSR: absolute URL to reach the API directly from Node. Reads
     PROXY_API_TARGET (matches the Vite proxy target) so dev hits
     the API container directly, bypassing the Vite proxy that the
     Astro SSR process can't reach (it IS the Vite process).
   ============================================================ */
const getApiBaseUrl = (): string => {
  if (typeof window === 'undefined') {
    return (
      import.meta.env.PROXY_API_TARGET ||
      import.meta.env.API_BASE_URL ||
      import.meta.env.PUBLIC_API_BASE_URL ||
      'http://synapxia-api:80'
    );
  }
  // Client: relative path → routed through Vite proxy / Vercel rewrite.
  return '';
};

const API_BASE_URL = getApiBaseUrl();

/**
 * Build a request URL. Browser-side we keep paths relative (so they go
 * through the Vite proxy / Vercel rewrite); server-side we prepend the
 * absolute API base.
 */
function buildUrl(route: string): string {
  if (!API_BASE_URL) return route; // browser: relative
  return new URL(route, API_BASE_URL).toString();
}

/**
 * Drain an error response into a single Error suitable for `throw`.
 * Handles FastAPI's `{detail: string}` and pydantic `{detail: [{msg}, ...]}` shapes.
 */
async function errorFrom(res: Response, method: string, url: string): Promise<Error> {
  const text = await res.text().catch(() => '');
  let detail: string = res.statusText;
  try {
    const json = JSON.parse(text) as any;
    if (json && typeof json.error === 'object' && json.error) {
      // Standardized envelope: { data: null, error: {code, message, details}, meta }.
      detail = json.error.message ?? String(json.error.code ?? res.statusText);
    } else if (Array.isArray(json.detail)) {
      // FastAPI / pydantic validation: { detail: [{msg}, …] } (auth routes).
      detail = (json.detail as Array<{ msg?: string }>)
        .map((e) => e.msg ?? 'Validation error')
        .join('. ');
    } else if (typeof json.detail === 'string') {
      detail = json.detail;
    } else if (text) {
      detail = text;
    }
  } catch {
    detail = text || res.statusText;
  }
  return new Error(`${method} ${url} failed (${res.status}): ${detail}`);
}

/**
 * Unwrap the standardized success envelope so callers keep receiving the bare
 * payload. The API wraps data endpoints as `{ data, error, meta }`; we return
 * `.data`. Anything else (auth routes, legacy/un-enveloped bodies) is returned
 * as-is — back-compatible.
 */
function unwrapEnvelope<T>(json: unknown): T {
  if (
    json &&
    typeof json === 'object' &&
    'data' in json &&
    'error' in json &&
    'meta' in json
  ) {
    return (json as { data: T }).data;
  }
  return json as T;
}

/**
 * Generic GET request handler
 */
export async function apiGet<T>(route: string, init?: RequestInit): Promise<T> {
  const url = buildUrl(route);
  try {
    const res = await fetchWithAuth(url, {
      ...init,
      method: 'GET',
      headers: { Accept: 'application/json', ...(init?.headers ?? {}) },
    });
    if (!res.ok) throw await errorFrom(res, 'GET', url);
    return unwrapEnvelope<T>(await res.json());
  } catch (error) {
    if (error instanceof Error) {
      console.error('API GET error:', error.message);
      // Server-side (static build): no API available, return empty so prerender
      // completes. Real data is always fetched client-side after login.
      if (typeof window === 'undefined') {
        return [] as unknown as T;
      }
      throw error;
    }
    throw new Error(`GET ${url} failed: ${String(error)}`);
  }
}

/**
 * Generic POST request handler
 */
export async function apiPost<T, D = any>(route: string, data: D, init?: RequestInit): Promise<T> {
  const url = buildUrl(route);
  try {
    const res = await fetchWithAuth(url, {
      ...init,
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        ...(init?.headers ?? {}),
      },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw await errorFrom(res, 'POST', url);
    return unwrapEnvelope<T>(await res.json());
  } catch (error) {
    if (error instanceof Error) {
      console.error('API POST error:', error.message);
      throw error;
    }
    throw new Error(`POST ${url} failed: ${String(error)}`);
  }
}

/**
 * Generic PUT request handler
 */
export async function apiPut<T, D = any>(route: string, data: D, init?: RequestInit): Promise<T> {
  const url = buildUrl(route);
  try {
    const res = await fetchWithAuth(url, {
      ...init,
      method: 'PUT',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        ...(init?.headers ?? {}),
      },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw await errorFrom(res, 'PUT', url);
    return unwrapEnvelope<T>(await res.json());
  } catch (error) {
    if (error instanceof Error) {
      console.error('API PUT error:', error.message);
      throw error;
    }
    throw new Error(`PUT ${url} failed: ${String(error)}`);
  }
}

/**
 * Generic DELETE request handler
 */
export async function apiDelete<T = void>(route: string, init?: RequestInit): Promise<T> {
  const url = buildUrl(route);
  try {
    const res = await fetchWithAuth(url, {
      ...init,
      method: 'DELETE',
      headers: { Accept: 'application/json', ...(init?.headers ?? {}) },
    });
    if (!res.ok) throw await errorFrom(res, 'DELETE', url);
    if (res.status === 204) return undefined as T;
    return unwrapEnvelope<T>(await res.json());
  } catch (error) {
    if (error instanceof Error) {
      console.error('API DELETE error:', error.message);
      throw error;
    }
    throw new Error(`DELETE ${url} failed: ${String(error)}`);
  }
}

/**
 * Build query string from params object
 * @param params - Object with query parameters
 * @returns Query string (e.g., "?skip=0&limit=10")
 */
export function buildQueryString(params: Record<string, any>): string {
  const searchParams = new URLSearchParams();

  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) {
      searchParams.append(key, String(value));
    }
  }

  const queryString = searchParams.toString();
  return queryString ? `?${queryString}` : '';
}

/**
 * Get the configured API base URL
 */
export function getApiUrl(): string {
  return API_BASE_URL;
}
