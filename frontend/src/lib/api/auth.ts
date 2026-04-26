// Authentication API client

import { apiFetch, ApiError } from "./client";

export interface RegisterPayload {
  email: string;
  username: string;
  password: string;
  full_name?: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface UpdateProfilePayload {
  full_name?: string;
  email?: string;
}

export interface ChangePasswordPayload {
  current_password: string;
  new_password: string;
}

export interface AuthMeResponse {
  user_id: string;
  email: string;
  username: string;
  full_name: string | null;
  is_admin: boolean;
  email_verified: boolean;
  created_at: string | null;
  last_login_at: string | null;
}

/**
 * Register a new user account.
 */
export async function register(data: RegisterPayload) {
  return apiFetch<{
    message: string;
    user_id: string;
    email: string;
    username: string;
  }>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

/**
 * Verify email address using token sent via email.
 * Returns plain text response.
 */
export async function verifyEmail(token: string): Promise<string> {
  const base = process.env.NEXT_PUBLIC_API_URL || "";
  const url = `${base}/api/auth/verify?token=${encodeURIComponent(token)}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30_000);
  const response = await fetch(url, {
    signal: controller.signal,
    credentials: "include",
  });
  clearTimeout(timeoutId);
  if (!response.ok) {
    const text = await response.text();
    throw new ApiError(response.status, text);
  }
  return response.text();
}

/**
 * User login with email and password.
 * Sets HttpOnly cookie on success.
 */
export async function login(data: LoginPayload) {
  return apiFetch<AuthMeResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

/**
 * Log out by clearing the access token cookie.
 */
export async function logout(): Promise<void> {
  return apiFetch<void>("/api/auth/logout", {
    method: "POST",
  });
}

/**
 * Get current authenticated user's profile.
 */
export async function getMe(): Promise<AuthMeResponse> {
  return apiFetch<AuthMeResponse>("/api/auth/me", {
    method: "GET",
  });
}

/**
 * Update current user's profile (full_name, email).
 */
export async function updateProfile(data: UpdateProfilePayload) {
  return apiFetch<AuthMeResponse>("/api/auth/me", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

/**
 * Change user's password.
 */
export async function changePassword(data: ChangePasswordPayload): Promise<void> {
  return apiFetch<void>("/api/auth/me/password", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}
