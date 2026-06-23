"use client";

import { Edit3, Link2, Trash2 } from "lucide-react";
import { MoneyText } from "@/components/ui/MoneyText";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { cn } from "@/lib/cn";
import { formatBRL, formatBudgetPercent } from "@/lib/format";
import { goalViabilityLabel } from "@/lib/metas";
import type { SavingsGoal } from "@/lib/types";

type SavingsGoalCardProps = {
  goal: SavingsGoal;
  deleting?: boolean;
  onEdit: () => void;
  onDelete: () => void;
  onReconcile?: () => void;
};

export function SavingsGoalCard({
  goal,
  deleting = false,
  onEdit,
  onDelete,
  onReconcile,
}: SavingsGoalCardProps) {
  const label = goalViabilityLabel(goal);
  const finished = goal.monthly_required <= 0;
  const savedTotal = goal.saved_total ?? goal.saved_amount;
  const savedFromTx = goal.saved_from_tx ?? 0;
  const linkedCount = goal.linked_count ?? 0;

  return (
    <article className="rounded-card border border-border bg-bg p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-sm font-semibold text-text">{goal.name}</h3>
          <p className="mt-1 text-xs text-muted">{goal.term_months} meses</p>
        </div>
        <span
          className={cn(
            "shrink-0 rounded-md px-2 py-1 text-xs font-medium",
            finished
              ? "bg-positive/10 text-positive"
              : goal.fits_surplus
                ? "bg-accent/10 text-accent"
                : "bg-negative/10 text-negative",
          )}
        >
          {label}
        </span>
      </div>

      <div className="mt-4 space-y-3">
        <ProgressBar value={goal.progress_pct} color="var(--color-positive)" />
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <p className="text-xs text-muted">Guardado</p>
            <p className="mt-1 font-semibold text-text">
              <MoneyText value={savedTotal} />
            </p>
            {savedFromTx > 0 ? (
              <p className="mt-1 text-[11px] text-muted">
                manual + {formatBRL(savedFromTx)} em lançamentos
              </p>
            ) : null}
          </div>
          <div>
            <p className="text-xs text-muted">Alvo</p>
            <p className="mt-1 font-semibold text-text">
              <MoneyText value={goal.target_amount} />
            </p>
          </div>
          <div>
            <p className="text-xs text-muted">Por mês</p>
            <p className="mt-1 font-semibold text-text">
              <MoneyText value={goal.monthly_required} />
            </p>
          </div>
          <div>
            <p className="text-xs text-muted">Progresso</p>
            <p className="mt-1 font-semibold text-text">{formatBudgetPercent(goal.progress_pct)}</p>
          </div>
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between gap-2">
        <span className="rounded-md border border-border px-2 py-1 text-xs text-muted">
          {linkedCount} {linkedCount === 1 ? "lançamento" : "lançamentos"}
        </span>
        <div className="flex justify-end gap-2">
          {onReconcile ? (
            <button
              type="button"
              onClick={onReconcile}
              aria-label={`Conciliar ${goal.name}`}
              title="Conciliar"
              className="inline-flex h-9 items-center gap-2 rounded-md border border-border px-3 text-sm font-medium text-muted transition hover:bg-surface2 hover:text-text"
            >
              <Link2 size={15} aria-hidden />
              Conciliar
            </button>
          ) : null}
        <button
          type="button"
          onClick={onEdit}
          aria-label={`Editar ${goal.name}`}
          title="Editar"
          className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-border text-muted transition hover:bg-surface2 hover:text-text"
        >
          <Edit3 size={15} aria-hidden />
        </button>
        <button
          type="button"
          onClick={onDelete}
          disabled={deleting}
          aria-label={`Excluir ${goal.name}`}
          title="Excluir"
          className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-border text-muted transition hover:bg-surface2 hover:text-negative disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Trash2 size={15} aria-hidden />
        </button>
        </div>
      </div>
    </article>
  );
}
