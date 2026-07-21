"use client";

import { type FormEvent, useState } from "react";
import { KeyRound, LockKeyhole, Mail, Save } from "lucide-react";
import type { AccountUpdateInput } from "@/lib/types";

type AccountCredentialsFormProps = {
  email: string;
  saving?: boolean;
  error?: string | null;
  savedMessage?: string | null;
  onSubmit: (input: AccountUpdateInput) => Promise<void> | void;
};

const inputWrapClass =
  "flex h-10 items-center rounded-md border border-border bg-bg focus-within:border-accent";

function messageClass(isError: boolean) {
  return isError ? "text-sm text-negative" : "text-sm text-positive";
}

export function AccountCredentialsForm({
  email,
  saving = false,
  error = null,
  savedMessage = null,
  onSubmit,
}: AccountCredentialsFormProps) {
  const [loginEmail, setLoginEmail] = useState(email);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalizedEmail = loginEmail.trim();
    const shouldChangePassword = Boolean(newPassword || confirmPassword);

    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(normalizedEmail)) {
      setLocalError("Informe um email valido.");
      return;
    }
    if (!currentPassword) {
      setLocalError("Informe a senha atual.");
      return;
    }
    if (shouldChangePassword && newPassword.length < 8) {
      setLocalError("A nova senha deve ter pelo menos 8 caracteres.");
      return;
    }
    if (shouldChangePassword && newPassword !== confirmPassword) {
      setLocalError("A confirmacao da senha nao confere.");
      return;
    }

    setLocalError(null);
    await onSubmit({
      email: normalizedEmail,
      current_password: currentPassword,
      new_password: shouldChangePassword ? newPassword : undefined,
    });
    setCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");
  };

  return (
    <form onSubmit={submit} className="grid gap-4 md:grid-cols-2">
      <label className="space-y-2">
        <span className="text-sm font-medium text-text">Email de login</span>
        <div className={inputWrapClass}>
          <Mail size={16} aria-hidden className="ml-3 shrink-0 text-muted" />
          <input
            value={loginEmail}
            onChange={(event) => setLoginEmail(event.target.value)}
            autoComplete="email"
            inputMode="email"
            type="email"
            className="min-w-0 flex-1 bg-transparent px-3 text-sm text-text outline-none placeholder:text-muted"
            placeholder="voce@email.com"
          />
        </div>
      </label>

      <label className="space-y-2">
        <span className="text-sm font-medium text-text">Senha atual</span>
        <div className={inputWrapClass}>
          <LockKeyhole size={16} aria-hidden className="ml-3 shrink-0 text-muted" />
          <input
            value={currentPassword}
            onChange={(event) => setCurrentPassword(event.target.value)}
            autoComplete="current-password"
            type="password"
            className="min-w-0 flex-1 bg-transparent px-3 text-sm text-text outline-none placeholder:text-muted"
            placeholder="Necessaria para salvar"
          />
        </div>
      </label>

      <label className="space-y-2">
        <span className="text-sm font-medium text-text">Nova senha</span>
        <div className={inputWrapClass}>
          <KeyRound size={16} aria-hidden className="ml-3 shrink-0 text-muted" />
          <input
            value={newPassword}
            onChange={(event) => setNewPassword(event.target.value)}
            autoComplete="new-password"
            type="password"
            className="min-w-0 flex-1 bg-transparent px-3 text-sm text-text outline-none placeholder:text-muted"
            placeholder="Opcional"
          />
        </div>
      </label>

      <label className="space-y-2">
        <span className="text-sm font-medium text-text">Confirmar nova senha</span>
        <div className={inputWrapClass}>
          <KeyRound size={16} aria-hidden className="ml-3 shrink-0 text-muted" />
          <input
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            autoComplete="new-password"
            type="password"
            className="min-w-0 flex-1 bg-transparent px-3 text-sm text-text outline-none placeholder:text-muted"
            placeholder="Repita a nova senha"
          />
        </div>
      </label>

      {localError || error || savedMessage ? (
        <p className={messageClass(Boolean(localError || error))} role={localError || error ? "alert" : undefined}>
          {localError ?? error ?? savedMessage}
        </p>
      ) : null}

      <div className="flex justify-end md:col-span-2">
        <button
          type="submit"
          disabled={saving}
          className="inline-flex h-10 items-center gap-2 rounded-md bg-accent px-4 text-sm font-semibold text-accentFg transition hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <Save size={17} aria-hidden />
          <span>{saving ? "Atualizando..." : "Atualizar acesso"}</span>
        </button>
      </div>
    </form>
  );
}
