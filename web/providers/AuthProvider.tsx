"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  getCurrentSession,
  isAuthEnabled,
  login as requestLogin,
  logout as requestLogout,
  type AuthStatus,
} from "@/lib/auth";
import type { AuthFamily, AuthSession, AuthUser, LoginRequest } from "@/lib/types";

type AuthContextValue = {
  enabled: boolean;
  status: AuthStatus;
  session: AuthSession | null;
  user: AuthUser | null;
  family: AuthFamily | null;
  error: string | null;
  refresh: () => Promise<AuthSession | null>;
  login: (input: LoginRequest) => Promise<AuthSession>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Nao foi possivel validar a sessao.";
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const enabled = isAuthEnabled();
  const [session, setSession] = useState<AuthSession | null>(null);
  const [status, setStatus] = useState<AuthStatus>(() => (enabled ? "loading" : "disabled"));
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!enabled) {
      setSession(null);
      setStatus("disabled");
      setError(null);
      return null;
    }

    setStatus("loading");
    try {
      const nextSession = await getCurrentSession();
      setSession(nextSession);
      setStatus(nextSession ? "authenticated" : "unauthenticated");
      setError(null);
      return nextSession;
    } catch (refreshError) {
      setSession(null);
      setStatus("unauthenticated");
      setError(errorMessage(refreshError));
      return null;
    }
  }, [enabled]);

  useEffect(() => {
    let active = true;

    if (!enabled) {
      return () => {
        active = false;
      };
    }

    void getCurrentSession()
      .then((nextSession) => {
        if (!active) {
          return;
        }
        setSession(nextSession);
        setStatus(nextSession ? "authenticated" : "unauthenticated");
        setError(null);
      })
      .catch((sessionError) => {
        if (!active) {
          return;
        }
        setSession(null);
        setStatus("unauthenticated");
        setError(errorMessage(sessionError));
      });

    return () => {
      active = false;
    };
  }, [enabled]);

  const login = useCallback(async (input: LoginRequest) => {
    const nextSession = await requestLogin(input);
    setSession(nextSession);
    setStatus("authenticated");
    setError(null);
    return nextSession;
  }, []);

  const logout = useCallback(async () => {
    try {
      if (enabled) {
        await requestLogout();
      }
    } finally {
      setSession(null);
      setStatus(enabled ? "unauthenticated" : "disabled");
    }
  }, [enabled]);

  const value = useMemo<AuthContextValue>(
    () => ({
      enabled,
      status,
      session,
      user: session?.user ?? null,
      family: session?.family ?? null,
      error,
      refresh,
      login,
      logout,
    }),
    [enabled, status, session, error, refresh, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return value;
}

export function useOptionalAuth() {
  return useContext(AuthContext);
}
