"use client";

import { Plus } from "lucide-react";

type ConnectAccountButtonProps = {
  loading: boolean;
  disabled?: boolean;
  onClick: () => void;
};

export function ConnectAccountButton({
  loading,
  disabled = false,
  onClick,
}: ConnectAccountButtonProps) {
  return (
    <button
      type="button"
      disabled={disabled || loading}
      onClick={onClick}
      className="inline-flex h-10 items-center gap-2 rounded-md bg-accent px-3 text-sm font-semibold text-black transition hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-60"
    >
      <Plus size={16} aria-hidden />
      <span>{loading ? "Abrindo..." : "Nova conta"}</span>
    </button>
  );
}
