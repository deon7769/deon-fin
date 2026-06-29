import { ApiError, api } from "./api";
import type { AuthSession, LoginRequest, LoginResponse } from "./types";

export type AuthStatus = "disabled" | "loading" | "authenticated" | "unauthenticated";

const ENABLED_VALUES = new Set(["1", "true", "yes", "on"]);

export function isAuthEnabled() {
  return ENABLED_VALUES.has((process.env.NEXT_PUBLIC_AUTH_ENABLED ?? "").trim().toLowerCase());
}

export function normalizeLoginEmail(email: string) {
  return email.trim().toLowerCase();
}

export function shouldRedirectToLogin({
  enabled,
  status,
}: {
  enabled: boolean;
  status: AuthStatus;
}) {
  return enabled && status === "unauthenticated";
}

export async function login(input: LoginRequest): Promise<LoginResponse> {
  return api.post<LoginResponse>("/auth/login", {
    email: normalizeLoginEmail(input.email),
    password: input.password,
  });
}

export async function getCurrentSession(): Promise<AuthSession | null> {
  try {
    return await api.get<AuthSession>("/auth/me");
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      return null;
    }
    throw error;
  }
}

export async function logout(): Promise<{ ok: boolean }> {
  return api.post<{ ok: boolean }>("/auth/logout");
}
