/**
 * Unified API Service Library
 * Provides reusable HTTP methods for interacting with the FastAPI backend
 */

import type { ApiError } from '../types/list';
import { getToken, clearToken } from './auth';

/**
 * Handle authentication errors (401/403)
 * Logs out user and redirects to login
 */
function handleAuthError(status: number) {
  if (status === 401 || status === 403) {
    // Clear auth state
    clearToken();
    // Redirect to login
    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    }
  }
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
 * Get authorization headers if token exists
 */
function getAuthHeaders(): Record<string, string> {
  const token = getToken();
  if (token) {
    return {
      Authorization: `Bearer ${token}`,
    };
  }
  return {};
}

/**
 * Generic GET request handler
 * @param route - API route (e.g., "/api/lists", "/api/modules")
 * @param init - Optional fetch configuration
 * @returns Promise with typed response data
 */
export async function apiGet<T>(route: string, init?: RequestInit): Promise<T> {
  const url = new URL(route, API_BASE_URL).toString();

  try {
    const res = await fetch(url, {
      ...init,
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        ...getAuthHeaders(),
        ...(init?.headers ?? {}),
      },
    });

    if (!res.ok) {
      // Handle auth errors (401, 403)
      handleAuthError(res.status);

      const errorText = await res.text().catch(() => '');
      let errorDetail = res.statusText;

      try {
        const errorJson = JSON.parse(errorText) as ApiError;
        errorDetail = errorJson.detail || errorText;
      } catch {
        errorDetail = errorText || res.statusText;
      }

      throw new Error(`GET ${url} failed (${res.status}): ${errorDetail}`);
    }

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
 * @param route - API route
 * @param data - Data to send in request body
 * @param init - Optional fetch configuration
 * @returns Promise with typed response data
 */
export async function apiPost<T, D = any>(route: string, data: D, init?: RequestInit): Promise<T> {
  const url = new URL(route, API_BASE_URL).toString();

  try {
    const res = await fetch(url, {
      ...init,
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
        ...(init?.headers ?? {}),
      },
      body: JSON.stringify(data),
    });

    if (!res.ok) {
      // Handle auth errors (401, 403)
      handleAuthError(res.status);

      const errorText = await res.text().catch(() => '');
      let errorDetail = res.statusText;

      try {
        const errorJson = JSON.parse(errorText) as ApiError;
        errorDetail = errorJson.detail || errorText;
      } catch {
        errorDetail = errorText || res.statusText;
      }

      throw new Error(`POST ${url} failed (${res.status}): ${errorDetail}`);
    }

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
 * @param route - API route
 * @param data - Data to send in request body
 * @param init - Optional fetch configuration
 * @returns Promise with typed response data
 */
export async function apiPut<T, D = any>(route: string, data: D, init?: RequestInit): Promise<T> {
  const url = new URL(route, API_BASE_URL).toString();

  try {
    const res = await fetch(url, {
      ...init,
      method: 'PUT',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
        ...(init?.headers ?? {}),
      },
      body: JSON.stringify(data),
    });

    if (!res.ok) {
      // Handle auth errors (401, 403)
      handleAuthError(res.status);

      const errorText = await res.text().catch(() => '');
      let errorDetail = res.statusText;

      try {
        const errorJson = JSON.parse(errorText) as ApiError;
        errorDetail = errorJson.detail || errorText;
      } catch {
        errorDetail = errorText || res.statusText;
      }

      throw new Error(`PUT ${url} failed (${res.status}): ${errorDetail}`);
    }

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
 * @param route - API route
 * @param init - Optional fetch configuration
 * @returns Promise with void or typed response data
 */
export async function apiDelete<T = void>(route: string, init?: RequestInit): Promise<T> {
  const url = new URL(route, API_BASE_URL).toString();

  try {
    const res = await fetch(url, {
      ...init,
      method: 'DELETE',
      headers: {
        'Accept': 'application/json',
        ...getAuthHeaders(),
        ...(init?.headers ?? {}),
      },
    });

    if (!res.ok) {
      // Handle auth errors (401, 403)
      handleAuthError(res.status);

      const errorText = await res.text().catch(() => '');
      let errorDetail = res.statusText;

      try {
        const errorJson = JSON.parse(errorText) as ApiError;
        errorDetail = errorJson.detail || errorText;
      } catch {
        errorDetail = errorText || res.statusText;
      }

      throw new Error(`DELETE ${url} failed (${res.status}): ${errorDetail}`);
    }

    // If response is 204 No Content, return void
    if (res.status === 204) {
      return undefined as T;
    }

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
