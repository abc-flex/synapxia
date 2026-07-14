/**
 * Authentication Service
 * Handles user authentication, token management, and authorization
 */

import { apiPost, apiGet, getApiUrl } from './api';
import type { UserRead } from '../types/api';

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: UserRead;  // synthesized client-side from a follow-up GET /me
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  profile: string;   // FK → profiles.code (was: menu_role)
  unit: string;      // FK → business_units.code (was: business_unit)
}

export interface ChangePasswordRequest {
  old_password: string;
  new_password: string;
}

// Local storage keys
const TOKEN_STORAGE_KEY = 'auth_token';
const REFRESH_TOKEN_STORAGE_KEY = 'auth_refresh_token';
const USER_STORAGE_KEY = 'auth_user';

/**
 * Store JWT access token in localStorage
 */
export function storeToken(token: string): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  }
}

/**
 * Retrieve JWT access token from localStorage
 */
export function getToken(): string | null {
  if (typeof window !== 'undefined') {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  }
  return null;
}

/**
 * Store the long-lived refresh token in localStorage.
 */
export function storeRefreshToken(token: string): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, token);
  }
}

/**
 * Retrieve the refresh token from localStorage.
 */
export function getRefreshToken(): string | null {
  if (typeof window !== 'undefined') {
    return localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY);
  }
  return null;
}

/**
 * Clear all auth state — both tokens, the cached user object, and the
 * cached sidebar nav. The nav clear matters: a stale cache from a
 * previous user would otherwise leak their menu options to the next
 * user before the background refetch overrides it.
 */
export function clearToken(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    localStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY);
    localStorage.removeItem(USER_STORAGE_KEY);
    localStorage.removeItem('nav_cache');
    // Bug-report FAB activation (see BugReporter.svelte) — a fresh login
    // should start with the floating button hidden again, not carry over
    // the previous session's "visited /support and clicked report" state.
    sessionStorage.removeItem('bug_report_fab_activated');
  }
}

/**
 * Store current user info
 */
export function storeUser(user: UserRead): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
  }
}

/**
 * Retrieve current user info
 */
export function getUser(): UserRead | null {
  if (typeof window !== 'undefined') {
    const userJson = localStorage.getItem(USER_STORAGE_KEY);
    if (userJson) {
      try {
        return JSON.parse(userJson) as UserRead;
      } catch {
        return null;
      }
    }
  }
  return null;
}

/**
 * Check if user is authenticated
 */
export function isAuthenticated(): boolean {
  return getToken() !== null;
}

/**
 * Server-side auth check — reads the `auth_token` cookie set at login.
 * Use from page frontmatters that need to branch on auth state during SSR
 * (e.g. redirect logged-in users away from `/` into the app shell).
 *
 *     import { isAuthenticatedSSR } from '@/lib/auth';
 *     if (isAuthenticatedSSR(Astro)) return Astro.redirect('/lib/assets');
 */
export function isAuthenticatedSSR(astro: { cookies: { get(name: string): { value?: string } | undefined } }): boolean {
  return !!astro.cookies.get('auth_token')?.value;
}

/**
 * POST credentials to a fastapi-users login backend and return the issued
 * token. Used for both the access-token backend (/api/auth/login) and the
 * refresh-token backend (/api/auth/refresh/login).
 */
async function postLogin(endpoint: string, credentials: LoginRequest): Promise<string> {
  const formData = new URLSearchParams();
  formData.append('username', credentials.username);
  formData.append('password', credentials.password);

  let res: Response;
  try {
    res = await fetch(`${getApiUrl()}${endpoint}`, { method: 'POST', body: formData });
  } catch (e) {
    throw new Error(e instanceof Error ? e.message : 'Login failed: network error');
  }

  if (!res.ok) {
    const errorText = await res.text().catch(() => '');
    let errorDetail = 'Login failed';
    try {
      const errorJson = JSON.parse(errorText);
      if (Array.isArray(errorJson.detail)) {
        errorDetail = errorJson.detail
          .map((e: { msg?: string }) => e.msg ?? 'Validation error')
          .join('. ');
      } else if (typeof errorJson.detail === 'string') {
        errorDetail = errorJson.detail;
      } else {
        errorDetail = errorText;
      }
    } catch {
      errorDetail = errorText || res.statusText;
    }
    throw new Error(errorDetail);
  }

  const data = (await res.json()) as { access_token: string; token_type: string };
  return data.access_token;
}

/**
 * POST credentials to the cookie auth backend. The server replies 204 with
 * a Set-Cookie header — there's no body to consume. We send the request
 * through the same origin (Vite proxy / Vercel rewrite) so the browser
 * scopes the cookie correctly. Returns nothing meaningful; throws on
 * non-2xx.
 */
async function postCookieLogin(credentials: LoginRequest): Promise<void> {
  const formData = new URLSearchParams();
  formData.append('username', credentials.username);
  formData.append('password', credentials.password);

  let res: Response;
  try {
    res = await fetch(`${getApiUrl()}/api/auth/cookie/login`, {
      method: 'POST',
      body: formData,
      credentials: 'include',
    });
  } catch (e) {
    throw new Error(e instanceof Error ? e.message : 'Login failed: network error');
  }

  if (!res.ok) {
    const errorText = await res.text().catch(() => '');
    let errorDetail = 'Login failed';
    try {
      const errorJson = JSON.parse(errorText);
      if (Array.isArray(errorJson.detail)) {
        errorDetail = errorJson.detail
          .map((e: { msg?: string }) => e.msg ?? 'Validation error')
          .join('. ');
      } else if (typeof errorJson.detail === 'string') {
        errorDetail = errorJson.detail;
      } else {
        errorDetail = errorText;
      }
    } catch {
      errorDetail = errorText || res.statusText;
    }
    throw new Error(errorDetail);
  }
}

/**
 * Login user with username/email and password.
 *
 * Three legs:
 *   1. POST /api/auth/cookie/login  → 204 + HTTP-only `auth_token` cookie
 *      (the cookie IS the access token — same JWT, just a different
 *      transport. The Astro middleware reads it server-side; the browser
 *      auto-attaches it on every same-origin request.)
 *   2. POST /api/auth/refresh/login → long-lived refresh token (14 d, in
 *      DB) — kept as a Bearer in localStorage for the silent-refresh path.
 *      Non-fatal if it fails; the user can re-login when the cookie
 *      expires.
 *   3. GET  /api/auth/me            → hydrate the user object the UI uses
 *      client-side (header, profile, etc.). The cookie auto-attaches.
 *
 * We keep `access_token` empty in the response — no caller reads it now
 * that the cookie carries it. Bearer access endpoints still exist for
 * non-browser clients (cron / curl / mobile).
 */
export async function login(credentials: LoginRequest): Promise<LoginResponse> {
  await postCookieLogin(credentials);

  // Refresh-token leg uses the existing Bearer backend. If it fails we
  // proceed with the cookie only — the user can re-log in when the
  // access cookie expires.
  try {
    const refreshToken = await postLogin('/api/auth/refresh/login', credentials);
    storeRefreshToken(refreshToken);
  } catch (e) {
    console.warn('Refresh-token issuance failed; proceeding with cookie only:', e);
  }

  const user = await getCurrentUser();

  return {
    access_token: '',
    token_type: 'cookie',
    user,
  };
}

/**
 * Exchange the stored refresh token for a fresh access token (no password
 * re-prompt). Updates ``auth_token`` in localStorage in place. Returns true
 * on success, false otherwise — callers should treat false as "auth lost,
 * redirect to login".
 *
 * Safe to call concurrently: the in-flight refresh promise is shared so
 * parallel 401s only spawn ONE network refresh call.
 */
let inflightRefresh: Promise<boolean> | null = null;

export function refreshAccessToken(): Promise<boolean> {
  if (inflightRefresh) return inflightRefresh;

  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    return Promise.resolve(false);
  }

  inflightRefresh = (async () => {
    try {
      const res = await fetch(`${getApiUrl()}/api/auth/refresh`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${refreshToken}` },
      });
      if (!res.ok) return false;
      const data = (await res.json()) as { access_token: string };
      storeToken(data.access_token);
      return true;
    } catch {
      return false;
    } finally {
      inflightRefresh = null;
    }
  })();

  return inflightRefresh;
}

/**
 * Register a new user
 */
export async function register(userData: RegisterRequest): Promise<UserRead> {
  const response = await apiPost<UserRead>('/api/auth/register', userData);
  return response;
}

/**
 * Get current authenticated user profile.
 *
 * Browser: the auth cookie auto-attaches (credentials:'include' in apiGet).
 * SSR: the token is forwarded from AsyncLocalStorage by the api layer.
 * Either way, no manual Bearer header needed.
 */
export async function getCurrentUser(): Promise<UserRead> {
  const response = await apiGet<UserRead>('/api/auth/me');

  // Cache the user object client-side for instant header/sidebar rendering
  // on the next navigation. SSR calls skip storeUser (no window).
  storeUser(response);

  return response;
}

/**
 * Update the current user's own profile via fastapi-users' PATCH /me.
 *
 * Accepts any subset of the editable fields (first_name, last_name, email,
 * username, profile, unit, password). On success refreshes the localStorage
 * cache so the UI sees the new values immediately.
 */
export async function updateMyProfile(data: Record<string, unknown>): Promise<UserRead> {
  const token = getToken();
  if (!token) {
    throw new Error('No authentication token found');
  }

  const url = `${getApiUrl()}/api/auth/me`;
  const res = await fetch(url, {
    method: 'PATCH',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const errorText = await res.text().catch(() => '');
    let errorDetail = 'Profile update failed';
    try {
      const errorJson = JSON.parse(errorText);
      if (Array.isArray(errorJson.detail)) {
        errorDetail = errorJson.detail
          .map((e: { msg?: string }) => e.msg ?? 'Validation error')
          .join('. ');
      } else if (typeof errorJson.detail === 'string') {
        errorDetail = errorJson.detail;
      }
    } catch {
      errorDetail = errorText || res.statusText;
    }
    throw new Error(errorDetail);
  }

  const updated = (await res.json()) as UserRead;
  storeUser(updated);
  return updated;
}

/**
 * Logout — clear the server-side cookie + revoke the refresh token, then
 * clear local auth state. We DON'T block on the network calls: even if the
 * server is unreachable, the local clear must happen so the user is logged
 * out client-side.
 */
export async function logout(): Promise<void> {
  // 1. Clear the auth cookie server-side (fastapi-users responds with a
  //    Set-Cookie that expires the cookie).
  try {
    await fetch(`${getApiUrl()}/api/auth/cookie/logout`, {
      method: 'POST',
      credentials: 'include',
    });
  } catch {
    /* swallow — local clear below is the source of truth */
  }

  // 2. Revoke the refresh token DB row so it can't mint new access tokens.
  const refreshToken = getRefreshToken();
  if (refreshToken) {
    try {
      await fetch(`${getApiUrl()}/api/auth/refresh/logout`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${refreshToken}` },
      });
    } catch {
      /* swallow */
    }
  }

  clearToken();
}

/**
 * Change password for the current user.
 *
 * Uses fastapi-users' PATCH /me endpoint. Note: there is no old-password
 * verification at the API layer — possessing a valid JWT IS the proof of
 * identity. The `old_password` field in the request is currently ignored
 * server-side. (Keep the field in the UI form anyway so we can re-add a
 * server-side check via a custom endpoint later without a UI rewrite.)
 */
export async function changePassword(request: ChangePasswordRequest): Promise<UserRead> {
  const token = getToken();
  if (!token) {
    throw new Error('No authentication token found');
  }

  const url = `${getApiUrl()}/api/auth/me`;

  try {
    const res = await fetch(url, {
      method: 'PATCH',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ password: request.new_password }),
    });

    if (!res.ok) {
      const errorText = await res.text().catch(() => '');
      let errorDetail = 'Password change failed';
      try {
        const errorJson = JSON.parse(errorText);
        if (Array.isArray(errorJson.detail)) {
          errorDetail = errorJson.detail
            .map((e: { msg?: string }) => e.msg ?? 'Validation error')
            .join('. ');
        } else if (typeof errorJson.detail === 'string') {
          errorDetail = errorJson.detail;
        }
      } catch {
        errorDetail = errorText || res.statusText;
      }
      throw new Error(errorDetail);
    }

    return res.json() as Promise<UserRead>;
  } catch (error) {
    if (error instanceof Error) {
      console.error('Change password error:', error.message);
      throw error;
    }
    throw new Error('Password change failed: unknown error');
  }
}

/**
 * Get authorization header with token
 * Useful for passing to API functions
 */
export function getAuthHeader(): Record<string, string> {
  const token = getToken();
  if (!token) {
    return {};
  }
  return {
    Authorization: `Bearer ${token}`,
  };
}
