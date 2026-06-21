"use client";

import { AlertTriangle } from "lucide-react";
import type { Tag } from "@/lib/types";

type DeleteTagDialogProps = {
  open: boolean;
  tag?: Tag | null;
  deleting?: boolean;
  error?: string | null;
  onClose: () => void;
  onConfirm: () => void | Promise<void>;
};

export function DeleteTagDialog({
  open,
  tag,
  deleting = false,
  error = null,
  onClose,
  onConfirm,
}: DeleteTagDialogProps) {
  if (!open || !tag) {
    return null;
  }

  const txCount = tag.tx_count ?? 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-tag-title"
        className="w-full max-w-sm rounded-md border border-border bg-surface p-5 shadow-2xl"
      >
        <div className="flex items-start gap-3">
          <span className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-negative/15 text-negative">
            <AlertTriangle size={18} aria-hidden />
          </span>
          <div className="min-w-0 space-y-2">
            <h2 id="delete-tag-title" className="text-base font-semibold text-text">
              Excluir tag
            </h2>
            <p className="text-sm text-muted">
              Excluir a tag <strong className="font-semibold text-text">{tag.name}</strong>?{" "}
              {txCount} transação(ões) ficarão sem tag.
            </p>
          </div>
        </div>

        {error ? <p className="mt-4 text-sm text-negative">{error}</p> : null}

        <div className="mt-5 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="h-10 rounded-md border border-border px-4 text-sm font-medium text-muted transition hover:bg-surface2 hover:text-text"
          >
            Cancelar
          </button>
          <button
            type="button"
            disabled={deleting}
            onClick={onConfirm}
            className="h-10 rounded-md bg-negative px-4 text-sm font-semibold text-white transition hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {deleting ? "Excluindo..." : "Excluir"}
          </button>
        </div>
      </div>
    </div>
  );
}
