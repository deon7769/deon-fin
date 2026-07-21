"use client";

import { useEffect, type ReactNode } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { redirectToLogin, shouldRedirectToLogin } from "@/lib/auth";
import { useAuth } from "@/providers/AuthProvider";

export default function AppLayout({ children }: { children: ReactNode }) {
  const auth = useAuth();

  useEffect(() => {
    if (shouldRedirectToLogin({ enabled: auth.enabled, status: auth.status })) {
      redirectToLogin();
    }
  }, [auth.enabled, auth.status]);

  if (auth.enabled && auth.status === "loading") {
    return (
      <div className="flex min-h-screen bg-bg text-text">
        <Sidebar />
        <main className="min-w-0 flex-1 overflow-x-hidden">
          <div className="flex min-h-screen items-center justify-center p-6 text-sm text-muted">
            Validando sessao...
          </div>
        </main>
      </div>
    );
  }

  if (shouldRedirectToLogin({ enabled: auth.enabled, status: auth.status })) {
    return null;
  }

  return (
    <div className="flex min-h-screen bg-bg text-text">
      <Sidebar />
      <main className="min-w-0 flex-1 overflow-x-hidden">{children}</main>
    </div>
  );
}
