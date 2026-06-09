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
  menu_role: string;
  business_unit: string;
}

export interface ChangePasswordRequest {
  old_password: string;
  new_password: string;
}

// Local storage key for token
const TOKEN_STORAGE_KEY = 'auth_token';
const USER_STORAGE_KEY = 'auth_user';

/**
 * Store JWT token in localStorage
 */
export function storeToken(token: string): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  }
}

/**
 * Retrieve JWT token from localStorage
 */
export function getToken(): string | null {
  if (typeof window !== 'undefined') {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  }
  return null;
}

/**
 * Clear JWT token from localStorage
 */
export function clearToken(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    localStorage.removeItem(USER_STORAGE_KEY);
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
 * Login user with username/email and password.
 *
 * fastapi-users' /login returns ONLY {access_token, token_type} — it does not
 * include the user profile. We chain a GET /me with the freshly-issued token
 * so the UI can hydrate the user object in the same call site as before.
 */
export async function login(credentials: LoginRequest): Promise<LoginResponse> {
  // OAuth2PasswordRequestForm requires application/x-www-form-urlencoded.
  const formData = new URLSearchParams();
  formData.append('username', credentials.username);
  formData.append('password', credentials.password);

  const loginUrl = `${getApiUrl()}/api/auth/login`;

  let res: Response;
  try {
    res = await fetch(loginUrl, { method: 'POST', body: formData });
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

  const tokenData = (await res.json()) as { access_token: string; token_type: string };
  storeToken(tokenData.access_token);

  // Hydrate the user object via /me so the rest of the app can rely on it.
  const user = await getCurrentUser();

  return {
    access_token: tokenData.access_token,
    token_type: tokenData.token_type,
    user,
  };
}

/**
 * Register a new user
 */
export async function register(userData: RegisterRequest): Promise<UserRead> {
  const response = await apiPost<UserRead>('/api/auth/register', userData);
  return response;
}

/**
 * Get current authenticated user profile
 */
export async function getCurrentUser(): Promise<UserRead> {
  const token = getToken();
  if (!token) {
    throw new Error('No authentication token found');
  }

  const response = await apiGet<UserRead>('/api/auth/me', {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  // Update stored user info
  storeUser(response);

  return response;
}

/**
 * Logout current user (client-side)
 * Clears stored token and user info
 */
export function logout(): void {
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
