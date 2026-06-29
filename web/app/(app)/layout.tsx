"use client";

import { useEffect, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { shouldRedirectToLogin } from "@/lib/auth";
import { useAuth } from "@/providers/AuthProvider";

export default function AppLayout({ children }: { children: ReactNode }) {
  const auth = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (shouldRedirectToLogin({ enabled: auth.enabled, status: auth.status })) {
      router.replace("/login");
    }
  }, [auth.enabled, auth.status, router]);

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
