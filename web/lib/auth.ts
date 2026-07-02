import { ApiError, api } from "./api";
import type {
  AccountUpdateInput,
  AccountUpdateResponse,
  AuthSession,
  LoginRequest,
  LoginResponse,
} from "./types";

export type AuthStatus = "disabled" | "loading" | "authenticated" | "unauthenticated";

const ENABLED_VALUES = new Set(["1", "true", "yes", "on"]);
export const SESSION_MARKER_COOKIE = "deon_session_present";

type NavigationTarget = {
  assign: (url: string) => void;
};

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

export function redirectToLogin(url = "/login", target?: NavigationTarget) {
  const destination =
    target ??
    (typeof window === "undefined"
      ? null
      : {
          assign: window.location.assign.bind(window.location),
        });

  destination?.assign(url);
}

export function shouldProbeCurrentSession({
  enabled,
  pathname,
  hasSessionMarker,
}: {
  enabled: boolean;
  pathname: string | null;
  hasSessionMarker: boolean;
}) {
  if (!enabled) {
    return false;
  }
  return pathname !== "/login" || hasSessionMarker;
}

export function hasSessionMarkerCookie(cookieHeader?: string) {
  const source =
    cookieHeader ??
    (typeof document === "undefined" ? "" : document.cookie);
  return source.split(";").some((part) => part.trim() === `${SESSION_MARKER_COOKIE}=1`);
}

export function markSessionPresent() {
  if (typeof document === "undefined") {
    return;
  }
  document.cookie = `${SESSION_MARKER_COOKIE}=1; path=/; SameSite=Lax`;
}

export function clearSessionMarker() {
  if (typeof document === "undefined") {
    return;
  }
  document.cookie = `${SESSION_MARKER_COOKIE}=; path=/; Max-Age=0; SameSite=Lax`;
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

export async function updateAccount(input: AccountUpdateInput): Promise<AccountUpdateResponse> {
  return api.patch<AccountUpdateResponse>("/auth/me", {
    email: input.email === undefined ? undefined : normalizeLoginEmail(input.email),
    current_password: input.current_password,
    new_password: input.new_password,
  });
}
