"use client";

import { FormEvent, useState } from "react";
import { X } from "lucide-react";
import type { SavingsGoalInput } from "@/hooks/useMetas";
import type { SavingsGoal } from "@/lib/types";

type SavingsGoalModalProps = {
  open: boolean;
  goal?: SavingsGoal | null;
  saving?: boolean;
  error?: string | null;
  onClose: () => void;
  onSubmit: (input: SavingsGoalInput) => void | Promise<void>;
};

function toNumber(value: string): number {
  const parsed = Number(value.trim().replace(/\./g, "").replace(",", "."));
  return Number.isFinite(parsed) ? parsed : 0;
}

export function SavingsGoalModal({
  open,
  goal,
  saving = false,
  error = null,
  onClose,
  onSubmit,
}: SavingsGoalModalProps) {
  if (!open) {
    return null;
  }

  return (
    <SavingsGoalModalContent
      key={goal?.id ?? "new"}
      goal={goal}
      saving={saving}
      error={error}
      onClose={onClose}
      onSubmit={onSubmit}
    />
  );
}

function SavingsGoalModalContent({
  goal,
  saving,
  error,
  onClose,
  onSubmit,
}: Omit<SavingsGoalModalProps, "open">) {
  const [name, setName] = useState(goal?.name ?? "");
  const [target, setTarget] = useState(String(goal?.target_amount ?? ""));
  const [saved, setSaved] = useState(String(goal?.saved_amount ?? 0));
  const [term, setTerm] = useState(String(goal?.term_months ?? 12));
  const [priority, setPriority] = useState(String(goal?.priority ?? 99));
  const [localError, setLocalError] = useState<string | null>(null);
  const title = goal ? "Editar meta" : "Nova meta";
  const submitLabel = saving ? "Salvando..." : "Salvar";

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalizedName = name.trim().replace(/\s+/g, " ");
    const targetValue = toNumber(target);
    const savedValue = toNumber(saved);
    const termValue = Number(term);
    const priorityValue = Number(priority);

    if (!normalizedName) {
      setLocalError("Informe um nome.");
      return;
    }
    if (targetValue <= 0 || termValue < 1 || savedValue < 0 || priorityValue < 1) {
      setLocalError("Revise valores, prazo e prioridade.");
      return;
    }

    setLocalError(null);
    await onSubmit({
      name: normalizedName,
      target_amount: targetValue,
      term_months: termValue,
      saved_amount: savedValue,
      priority: priorityValue,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="goal-modal-title"
        className="w-full max-w-md rounded-md border border-border bg-surface shadow-2xl"
      >
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <h2 id="goal-modal-title" className="text-base font-semibold text-text">
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Fechar"
            className="inline-flex h-9 w-9 items-center justify-center rounded-md text-muted transition hover:bg-surface2 hover:text-text"
          >
            <X size={17} aria-hidden />
          </button>
        </div>

        <form onSubmit={submit} className="space-y-4 px-5 py-5">
          <label className="block space-y-2">
            <span className="text-sm font-medium text-text">Nome</span>
            <input
              value={name}
              onChange={(event) => {
                setName(event.target.value);
                setLocalError(null);
              }}
              className="h-10 w-full rounded-md border border-border bg-bg px-3 text-sm text-text outline-none focus:border-accent"
            />
          </label>

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block space-y-2">
              <span className="text-sm font-medium text-text">Alvo</span>
              <input
                value={target}
                onChange={(event) => setTarget(event.target.value)}
                inputMode="decimal"
                className="h-10 w-full rounded-md border border-border bg-bg px-3 text-sm text-text outline-none focus:border-accent"
              />
            </label>
            <label className="block space-y-2">
              <span className="text-sm font-medium text-text">Guardado</span>
              <input
                value={saved}
                onChange={(event) => setSaved(event.target.value)}
                inputMode="decimal"
                className="h-10 w-full rounded-md border border-border bg-bg px-3 text-sm text-text outline-none focus:border-accent"
              />
            </label>
            <label className="block space-y-2">
              <span className="text-sm font-medium text-text">Prazo</span>
              <input
                value={term}
                onChange={(event) => setTerm(event.target.value)}
                inputMode="numeric"
                className="h-10 w-full rounded-md border border-border bg-bg px-3 text-sm text-text outline-none focus:border-accent"
              />
            </label>
            <label className="block space-y-2">
              <span className="text-sm font-medium text-text">Prioridade</span>
              <input
                value={priority}
                onChange={(event) => setPriority(event.target.value)}
                inputMode="numeric"
                className="h-10 w-full rounded-md border border-border bg-bg px-3 text-sm text-text outline-none focus:border-accent"
              />
            </label>
          </div>

          {localError || error ? <p className="text-sm text-negative">{localError ?? error}</p> : null}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="h-10 rounded-md border border-border px-4 text-sm font-medium text-muted transition hover:bg-surface2 hover:text-text"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving}
              className="h-10 rounded-md bg-accent px-4 text-sm font-semibold text-accentFg transition hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {submitLabel}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
