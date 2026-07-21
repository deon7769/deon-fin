"use client";

import { type FormEvent, useState } from "react";
import { LockKeyhole, LogIn, Mail } from "lucide-react";
import type { LoginRequest } from "@/lib/types";

type LoginFormProps = {
  pending?: boolean;
  error?: string | null;
  onSubmit: (input: LoginRequest) => Promise<void> | void;
};

const inputWrapClass =
  "flex h-11 items-center rounded-md border border-border bg-bg focus-within:border-accent";

export function LoginForm({ pending = false, error = null, onSubmit }: LoginFormProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalizedEmail = email.trim();
    if (!normalizedEmail) {
      setLocalError("Informe o e-mail.");
      return;
    }
    if (!password) {
      setLocalError("Informe a senha.");
      return;
    }

    setLocalError(null);
    await onSubmit({ email: normalizedEmail, password });
  };

  return (
    <form onSubmit={submit} className="space-y-4">
      <label className="block space-y-2">
        <span className="text-sm font-medium text-text">E-mail</span>
        <div className={inputWrapClass}>
          <Mail size={17} aria-hidden className="ml-3 shrink-0 text-muted" />
          <input
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            autoComplete="email"
            inputMode="email"
            type="email"
            className="min-w-0 flex-1 bg-transparent px-3 text-sm text-text outline-none placeholder:text-muted"
            placeholder="voce@email.com"
          />
        </div>
      </label>

      <label className="block space-y-2">
        <span className="text-sm font-medium text-text">Senha</span>
        <div className={inputWrapClass}>
          <LockKeyhole size={17} aria-hidden className="ml-3 shrink-0 text-muted" />
          <input
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            type="password"
            className="min-w-0 flex-1 bg-transparent px-3 text-sm text-text outline-none placeholder:text-muted"
            placeholder="Sua senha"
          />
        </div>
      </label>

      {localError || error ? (
        <p className="text-sm text-negative" role="alert">
          {localError ?? error}
        </p>
      ) : null}

      <button
        type="submit"
        disabled={pending}
        className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-md bg-accent px-4 text-sm font-semibold text-accentFg transition hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-60"
      >
        <LogIn size={17} aria-hidden />
        <span>{pending ? "Entrando..." : "Entrar"}</span>
      </button>
    </form>
  );
}
