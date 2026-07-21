"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ShieldCheck } from "lucide-react";
import { LoginForm } from "@/components/auth/LoginForm";
import { redirectAfterLogin, submitLogin } from "@/lib/login-flow";
import { useAuth } from "@/providers/AuthProvider";
import type { LoginRequest } from "@/lib/types";

export default function LoginPage() {
  const auth = useAuth();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!auth.enabled || auth.status === "authenticated") {
      redirectAfterLogin();
    }
  }, [auth.enabled, auth.status]);

  async function submit(input: LoginRequest) {
    await submitLogin({
      input,
      login: auth.login,
      redirect: redirectAfterLogin,
      setPending,
      setError,
    });
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-bg px-4 py-10 text-text">
      <section className="w-full max-w-[420px] rounded-md border border-border bg-surface p-6 shadow-2xl">
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-md bg-accent text-accentFg">
            <ShieldCheck size={22} aria-hidden />
          </div>
          <div className="min-w-0">
            <h1 className="text-xl font-semibold">deon-fin</h1>
            <p className="mt-1 text-sm text-muted">Acesse seu painel financeiro.</p>
          </div>
        </div>

        <LoginForm pending={pending} error={error ?? auth.error} onSubmit={submit} />

        <p className="mt-5 text-center text-xs text-muted">
          Fluxo de sessao em implantacao.{" "}
          <Link href="/" prefetch={false} className="font-medium text-accent hover:underline">
            Voltar ao painel
          </Link>
        </p>
      </section>
    </main>
  );
}
