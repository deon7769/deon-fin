"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ShieldCheck } from "lucide-react";
import { useRouter } from "next/navigation";
import { LoginForm } from "@/components/auth/LoginForm";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/providers/AuthProvider";
import type { LoginRequest } from "@/lib/types";

function loginErrorMessage(error: unknown) {
  if (error instanceof ApiError && error.status === 401) {
    return "E-mail ou senha invalidos.";
  }
  return error instanceof Error ? error.message : "Nao foi possivel entrar.";
}

export default function LoginPage() {
  const auth = useAuth();
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!auth.enabled || auth.status === "authenticated") {
      router.replace("/");
    }
  }, [auth.enabled, auth.status, router]);

  async function submit(input: LoginRequest) {
    setPending(true);
    setError(null);
    try {
      await auth.login(input);
      router.replace("/");
    } catch (loginError) {
      setError(loginErrorMessage(loginError));
    } finally {
      setPending(false);
    }
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
          <Link href="/" className="font-medium text-accent hover:underline">
            Voltar ao painel
          </Link>
        </p>
      </section>
    </main>
  );
}
