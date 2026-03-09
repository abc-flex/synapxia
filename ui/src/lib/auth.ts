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
  user: UserRead;
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
 * Login user with username/email and password
 * Returns user data and stores token
 */
export async function login(credentials: LoginRequest): Promise<LoginResponse> {
  // Use FormData for OAuth2PasswordRequestForm compatibility
  const formData = new FormData();
  formData.append('username', credentials.username);
  formData.append('password', credentials.password);

  const url = `${getApiUrl()}/api/auth/login`;

  try {
    const res = await fetch(url, {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) {
      const errorText = await res.text().catch(() => '');
      let errorDetail = 'Login failed';

      try {
        const errorJson = JSON.parse(errorText);
        errorDetail = errorJson.detail || errorText;
      } catch {
        errorDetail = errorText || res.statusText;
      }

      throw new Error(errorDetail);
    }

    const data = (await res.json()) as LoginResponse;

    // Store token and user info
    storeToken(data.access_token);
    storeUser(data.user);

    return data;
  } catch (error) {
    if (error instanceof Error) {
      console.error('Login error:', error.message);
      throw error;
    }
    throw new Error('Login failed: unknown error');
  }
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
 * Change password for current user
 */
export async function changePassword(request: ChangePasswordRequest): Promise<{ message: string }> {
  const token = getToken();
  if (!token) {
    throw new Error('No authentication token found');
  }

  const url = `${getApiUrl()}/api/auth/change-password`;

  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(request),
    });

    if (!res.ok) {
      const errorText = await res.text().catch(() => '');
      let errorDetail = 'Password change failed';

      try {
        const errorJson = JSON.parse(errorText);
        errorDetail = errorJson.detail || errorText;
      } catch {
        errorDetail = errorText || res.statusText;
      }

      throw new Error(errorDetail);
    }

    return res.json() as Promise<{ message: string }>;
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
