/**
 * Unified API Service Library
 * Provides reusable HTTP methods for interacting with the FastAPI backend
 */

import type { ApiError } from '../types/list';
import { clearToken, getToken, refreshAccessToken } from './auth';

/**
 * Send a fetch with the current access token, and on a 401 try ONE silent
 * refresh + retry before giving up. On final failure (no refresh token, or
 * refresh itself fails), clears local auth and redirects to /login.
 *
 * The Authorization header is injected here — callers should NOT add it
 * themselves (it would be overwritten on retry anyway).
 */
async function fetchWithAuth(url: string, init: RequestInit): Promise<Response> {
  const buildInit = (): RequestInit => {
    const token = getToken();
    const headers = new Headers(init.headers || {});
    if (token) headers.set('Authorization', `Bearer ${token}`);
    return { ...init, headers };
  };

  let res = await fetch(url, buildInit());

  if (res.status === 401) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      // Retry once with the new access token
      res = await fetch(url, buildInit());
    }
    if (res.status === 401) {
      // Refresh didn't help (or no refresh token); end the session
      clearToken();
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
    }
  } else if (res.status === 403) {
    // 403 is "you're authenticated but not allowed" — don't logout, just bubble up
  }

  return res;
}

// Get API base URL from environment variables
// Use PUBLIC_ prefix for client-side access
const getApiBaseUrl = (): string => {
  // Check if we're on the server (SSR) or client
  if (typeof window === 'undefined') {
    // Server-side: can access both PUBLIC_ and non-PUBLIC_ env vars
    return import.meta.env.API_BASE_URL || import.meta.env.PUBLIC_API_BASE_URL || 'http://localhost:8000';
  } else {
    // Client-side: can only access PUBLIC_ env vars
    return import.meta.env.PUBLIC_API_BASE_URL || 'http://localhost:8000';
  }
};

const API_BASE_URL = getApiBaseUrl();

if (!API_BASE_URL) {
  console.warn('API_BASE_URL not configured. Using default: http://localhost:8000');
}

/**
 * Drain an error response into a single Error suitable for `throw`.
 * Handles FastAPI's `{detail: string}` and pydantic `{detail: [{msg}, ...]}` shapes.
 */
async function errorFrom(res: Response, method: string, url: string): Promise<Error> {
  const text = await res.text().catch(() => '');
  let detail: string = res.statusText;
  try {
    const json = JSON.parse(text) as ApiError;
    if (Array.isArray((json as any).detail)) {
      detail = ((json as any).detail as Array<{ msg?: string }>)
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
 * Generic GET request handler
 */
export async function apiGet<T>(route: string, init?: RequestInit): Promise<T> {
  const url = new URL(route, API_BASE_URL).toString();
  try {
    const res = await fetchWithAuth(url, {
      ...init,
      method: 'GET',
      headers: { Accept: 'application/json', ...(init?.headers ?? {}) },
    });
    if (!res.ok) throw await errorFrom(res, 'GET', url);
    return res.json() as Promise<T>;
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
  const url = new URL(route, API_BASE_URL).toString();
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
    return res.json() as Promise<T>;
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
  const url = new URL(route, API_BASE_URL).toString();
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
    return res.json() as Promise<T>;
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
  const url = new URL(route, API_BASE_URL).toString();
  try {
    const res = await fetchWithAuth(url, {
      ...init,
      method: 'DELETE',
      headers: { Accept: 'application/json', ...(init?.headers ?? {}) },
    });
    if (!res.ok) throw await errorFrom(res, 'DELETE', url);
    if (res.status === 204) return undefined as T;
    return res.json() as Promise<T>;
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
