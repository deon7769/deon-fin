"use client";

import type { ReactNode } from "react";
import { KeyRound, RefreshCw, Trash2 } from "lucide-react";
import { cn } from "@/lib/cn";

type AccountActionsProps = {
  accountId: string;
  canUsePluggy: boolean;
  busy?: boolean;
  onSync: (accountId: string) => void;
  onCredentials: (accountId: string) => void;
  onDelete: (accountId: string) => void;
};

function IconButton({
  label,
  disabled,
  destructive = false,
  children,
  onClick,
}: {
  label: string;
  disabled?: boolean;
  destructive?: boolean;
  children: ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      disabled={disabled}
      onClick={onClick}
      className={cn(
        "inline-flex h-9 w-9 items-center justify-center rounded-md border border-border bg-surface2 text-muted transition hover:bg-surface hover:text-text disabled:cursor-not-allowed disabled:opacity-50",
        destructive && "hover:border-negative hover:text-negative",
      )}
    >
      {children}
    </button>
  );
}

export function AccountActions({
  accountId,
  canUsePluggy,
  busy = false,
  onSync,
  onCredentials,
  onDelete,
}: AccountActionsProps) {
  const disabled = busy || !canUsePluggy;

  return (
    <div className="flex justify-end gap-2">
      <IconButton label="Sincronizar agora" disabled={disabled} onClick={() => onSync(accountId)}>
        <RefreshCw size={16} aria-hidden className={busy ? "animate-spin" : undefined} />
      </IconButton>
      <IconButton
        label="Atualizar credenciais"
        disabled={disabled}
        onClick={() => onCredentials(accountId)}
      >
        <KeyRound size={16} aria-hidden />
      </IconButton>
      <IconButton
        label="Remover conexão"
        disabled={disabled}
        destructive
        onClick={() => onDelete(accountId)}
      >
        <Trash2 size={16} aria-hidden />
      </IconButton>
    </div>
  );
}
