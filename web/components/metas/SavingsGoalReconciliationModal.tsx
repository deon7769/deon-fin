"use client";

import { useState } from "react";
import { Link2, X } from "lucide-react";
import {
  useGoalCandidates,
  useGoalTransactions,
  useLinkGoalTransactions,
  useUnlinkGoalTransactions,
} from "@/hooks/useMetas";
import { formatDate } from "@/lib/format";
import type { SavingsGoal, Transaction } from "@/lib/types";
import { MoneyText } from "@/components/ui/MoneyText";
import { Skeleton } from "@/components/ui/Skeleton";

type SavingsGoalReconciliationModalProps = {
  open: boolean;
  goal: SavingsGoal | null;
  onClose: () => void;
};

function txValue(tx: Transaction): number {
  return Math.abs(tx.display_value ?? tx.amount ?? 0);
}

function ToggleRow({
  tx,
  checked,
  onToggle,
}: {
  tx: Transaction;
  checked: boolean;
  onToggle: () => void;
}) {
  return (
    <label className="flex min-h-16 cursor-pointer items-center gap-3 border-b border-border px-3 py-2 last:border-b-0">
      <input
        type="checkbox"
        checked={checked}
        onChange={onToggle}
        className="h-4 w-4 accent-accent"
      />
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-medium text-text">{tx.description}</span>
        <span className="mt-1 block text-xs text-muted">
          {formatDate(tx.posted_at)} · {tx.account_name ?? "Conta"}
        </span>
      </span>
      <span className="shrink-0 text-sm font-semibold text-text">
        <MoneyText value={txValue(tx)} />
      </span>
    </label>
  );
}

function idSet(ids: string[], id: string): string[] {
  return ids.includes(id) ? ids.filter((item) => item !== id) : [...ids, id];
}

export function SavingsGoalReconciliationModal({
  open,
  goal,
  onClose,
}: SavingsGoalReconciliationModalProps) {
  const goalId = goal?.id ?? null;
  const linkedQuery = useGoalTransactions(goalId);
  const candidatesQuery = useGoalCandidates(goalId);
  const linkMutation = useLinkGoalTransactions();
  const unlinkMutation = useUnlinkGoalTransactions();
  const [selectedLinked, setSelectedLinked] = useState<string[]>([]);
  const [selectedCandidates, setSelectedCandidates] = useState<string[]>([]);

  if (!open || !goal) {
    return null;
  }

  const linked = linkedQuery.data?.items ?? [];
  const candidates = candidatesQuery.data?.items ?? [];
  const saving = linkMutation.isPending || unlinkMutation.isPending;
  const savedTotal = goal.saved_total ?? goal.saved_amount;
  const savedFromTx = linkedQuery.data?.saved_from_tx ?? goal.saved_from_tx ?? 0;

  const linkSelected = async () => {
    if (!selectedCandidates.length) return;
    await linkMutation.mutateAsync({ goalId: goal.id, transactionIds: selectedCandidates });
    setSelectedCandidates([]);
  };

  const unlinkSelected = async () => {
    if (!selectedLinked.length) return;
    await unlinkMutation.mutateAsync({ goalId: goal.id, transactionIds: selectedLinked });
    setSelectedLinked([]);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-3 sm:p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="goal-reconciliation-title"
        className="max-h-[92vh] w-full max-w-5xl overflow-hidden rounded-md border border-border bg-surface shadow-2xl"
      >
        <div className="flex items-center justify-between border-b border-border px-4 py-3 sm:px-5">
          <div className="min-w-0">
            <h2 id="goal-reconciliation-title" className="truncate text-base font-semibold text-text">
              Conciliar {goal.name}
            </h2>
            <p className="mt-1 text-xs text-muted">
              Guardado: <MoneyText value={savedTotal} /> · lançamentos:{" "}
              <MoneyText value={savedFromTx} />
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Fechar"
            className="inline-flex h-9 w-9 items-center justify-center rounded-md text-muted transition hover:bg-surface2 hover:text-text"
          >
            <X size={17} aria-hidden />
          </button>
        </div>

        <div className="grid max-h-[calc(92vh-72px)] gap-4 overflow-y-auto p-4 lg:grid-cols-2">
          <section className="min-w-0 rounded-md border border-border bg-bg">
            <div className="flex items-center justify-between gap-3 border-b border-border px-3 py-3">
              <div>
                <h3 className="text-sm font-semibold text-text">Vinculadas</h3>
                <p className="mt-1 text-xs text-muted">{linked.length} lançamento(s)</p>
              </div>
              <button
                type="button"
                onClick={() => void unlinkSelected()}
                disabled={saving || selectedLinked.length === 0}
                className="h-9 rounded-md border border-border px-3 text-sm font-medium text-muted transition hover:bg-surface2 hover:text-text disabled:cursor-not-allowed disabled:opacity-50"
              >
                Desvincular
              </button>
            </div>
            {linkedQuery.isLoading ? (
              <div className="space-y-2 p-3">
                <Skeleton className="h-14 w-full" />
                <Skeleton className="h-14 w-full" />
              </div>
            ) : linked.length ? (
              linked.map((tx) => (
                <ToggleRow
                  key={tx.id}
                  tx={tx}
                  checked={selectedLinked.includes(tx.id)}
                  onToggle={() => setSelectedLinked((ids) => idSet(ids, tx.id))}
                />
              ))
            ) : (
              <p className="px-3 py-8 text-center text-sm text-muted">Nenhum lançamento vinculado.</p>
            )}
          </section>

          <section className="min-w-0 rounded-md border border-border bg-bg">
            <div className="flex items-center justify-between gap-3 border-b border-border px-3 py-3">
              <div>
                <h3 className="text-sm font-semibold text-text">Candidatas do mês</h3>
                <p className="mt-1 text-xs text-muted">{candidates.length} lançamento(s)</p>
              </div>
              <button
                type="button"
                onClick={() => void linkSelected()}
                disabled={saving || selectedCandidates.length === 0}
                className="inline-flex h-9 items-center gap-2 rounded-md bg-accent px-3 text-sm font-semibold text-accentFg transition hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Link2 size={15} aria-hidden />
                Vincular
              </button>
            </div>
            {candidatesQuery.isLoading ? (
              <div className="space-y-2 p-3">
                <Skeleton className="h-14 w-full" />
                <Skeleton className="h-14 w-full" />
              </div>
            ) : candidates.length ? (
              candidates.map((tx) => (
                <ToggleRow
                  key={tx.id}
                  tx={tx}
                  checked={selectedCandidates.includes(tx.id)}
                  onToggle={() => setSelectedCandidates((ids) => idSet(ids, tx.id))}
                />
              ))
            ) : (
              <p className="px-3 py-8 text-center text-sm text-muted">Nenhuma candidata neste mês.</p>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
