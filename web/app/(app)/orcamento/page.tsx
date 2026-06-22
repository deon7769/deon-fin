"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { AlertCircle, ChevronDown, PiggyBank, Wallet } from "lucide-react";
import { BucketBudgetCard } from "@/components/budget/BucketBudgetCard";
import { Header } from "@/components/layout/Header";
import { BucketSelect } from "@/components/ui/BucketSelect";
import { EmptyState } from "@/components/ui/EmptyState";
import { KpiCard } from "@/components/ui/KpiCard";
import { MoneyText } from "@/components/ui/MoneyText";
import { SectionCard } from "@/components/ui/SectionCard";
import { Skeleton } from "@/components/ui/Skeleton";
import { useBudget } from "@/hooks/useBudget";
import { useBuckets } from "@/hooks/useBuckets";
import { useUpdateTransaction } from "@/hooks/useTransactionMutations";
import { cn } from "@/lib/cn";
import { formatBudgetPercent, formatDate } from "@/lib/format";
import type { Budget, BudgetUncategorized } from "@/lib/types";

function RetryState({
  title,
  error,
  onRetry,
}: {
  title: string;
  error: unknown;
  onRetry: () => void;
}) {
  return (
    <SectionCard>
      <EmptyState
        icon={<AlertCircle size={28} aria-hidden />}
        title={title}
        description={error instanceof Error ? error.message : undefined}
        action={
          <button
            type="button"
            onClick={onRetry}
            className="h-9 rounded-md border border-border px-3 text-sm font-medium text-text transition hover:bg-surface2"
          >
            Tentar novamente
          </button>
        }
      />
    </SectionCard>
  );
}

function BudgetSkeleton() {
  return (
    <>
      <div className="grid gap-4 md:grid-cols-3">
        <KpiCard title="Sua Renda" value={<Skeleton className="h-8 w-32" />} />
        <KpiCard title="Gastos do Mês" value={<Skeleton className="h-8 w-32" />} />
        <KpiCard title="Saldo Restante" value={<Skeleton className="h-8 w-32" />} />
      </div>
      <SectionCard title="Metas Financeiras">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, index) => (
            <Skeleton key={index} className="h-44 w-full" />
          ))}
        </div>
      </SectionCard>
    </>
  );
}

function IncomeEmptyState() {
  return (
    <SectionCard>
      <EmptyState
        icon={<Wallet size={28} aria-hidden />}
        title="Renda mensal não definida"
        description="Informe uma renda no perfil ou sincronize receitas para acompanhar o orçamento do mês."
        action={
          <div className="flex flex-wrap items-center justify-center gap-2">
            <Link
              href="/perfil"
              className="inline-flex h-10 items-center rounded-md bg-accent px-4 text-sm font-semibold text-accentFg transition hover:brightness-95"
            >
              Abrir perfil
            </Link>
            <Link
              href="/metas"
              className="inline-flex h-10 items-center rounded-md border border-border px-4 text-sm font-medium text-muted transition hover:bg-surface2 hover:text-text"
            >
              Ver metas
            </Link>
          </div>
        }
      />
    </SectionCard>
  );
}

function BudgetKpis({ budget }: { budget: Budget }) {
  const usedSubtitle =
    budget.used_pct === null
      ? "Renda não definida"
      : `${formatBudgetPercent(budget.used_pct)} da renda utilizada`;

  return (
    <div className="grid gap-4 md:grid-cols-3">
      <KpiCard
        title="Sua Renda"
        value={<MoneyText value={budget.income} />}
        subtitle={
          budget.income_source === "transactions"
            ? "Receitas reconhecidas no mês"
            : "Renda informada para planejamento"
        }
        tone="positive"
        icon={<Wallet size={18} aria-hidden />}
      />
      <KpiCard
        title="Gastos do Mês"
        value={<MoneyText value={budget.spent} />}
        subtitle={usedSubtitle}
        tone="negative"
        icon={<PiggyBank size={18} aria-hidden />}
      />
      <KpiCard
        title="Saldo Restante"
        value={<MoneyText value={budget.remaining} colorBySign="auto" />}
        subtitle="Renda menos gastos do mês"
        tone={budget.remaining >= 0 ? "positive" : "negative"}
        icon={<Wallet size={18} aria-hidden />}
      />
    </div>
  );
}

function UncategorizedRow({
  item,
  options,
  saving,
  onAssign,
}: {
  item: BudgetUncategorized;
  options: ReturnType<typeof useBuckets>["data"];
  saving: boolean;
  onAssign: (bucketId: number | null) => void;
}) {
  return (
    <div className="grid gap-3 border-b border-border py-3 last:border-b-0 md:grid-cols-[minmax(0,1fr)_120px_130px_auto] md:items-center">
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-text">{item.description}</p>
        <p className="mt-1 text-xs text-muted">{formatDate(item.date)}</p>
      </div>
      <p className="text-sm text-muted md:text-right">
        <MoneyText value={item.amount} />
      </p>
      <div className="md:justify-self-end">
        <BucketSelect
          value={null}
          options={options ?? []}
          loading={!options?.length}
          disabled={saving}
          placeholder="Meta..."
          onChange={onAssign}
        />
      </div>
    </div>
  );
}

export default function OrcamentoPage() {
  const [uncategorizedOpen, setUncategorizedOpen] = useState(true);
  const budgetQuery = useBudget();
  const bucketsQuery = useBuckets();
  const updateTx = useUpdateTransaction();
  const budget = budgetQuery.data;
  const bucketOptions = useMemo(
    () => bucketsQuery.data ?? budget?.categories ?? [],
    [bucketsQuery.data, budget?.categories],
  );

  return (
    <>
      <Header
        title="Orçamento"
        subtitle="Controle seu orçamento com base em suas metas e rendimentos."
      />

      <div className="space-y-5 p-4 sm:p-6">
        {budgetQuery.isError ? (
          <RetryState
            title="Não foi possível carregar o orçamento"
            error={budgetQuery.error}
            onRetry={() => void budgetQuery.refetch()}
          />
        ) : budgetQuery.isLoading || !budget ? (
          <BudgetSkeleton />
        ) : (
          <>
            {budget.income_source === "none" ? <IncomeEmptyState /> : null}
            <BudgetKpis budget={budget} />

            <SectionCard title="Metas Financeiras">
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {budget.categories.map((category) => (
                  <BucketBudgetCard key={category.id} category={category} month={budget.month} />
                ))}
              </div>
            </SectionCard>

            <SectionCard
              title="Transações não categorizadas"
              subtitle={`${budget.uncategorized.length} transações sem meta alocada`}
              actions={
                <button
                  type="button"
                  onClick={() => setUncategorizedOpen((current) => !current)}
                  aria-label={
                    uncategorizedOpen
                      ? "Recolher transações não categorizadas"
                      : "Expandir transações não categorizadas"
                  }
                  aria-expanded={uncategorizedOpen}
                  className="inline-flex h-9 w-9 items-center justify-center rounded-md text-muted transition hover:bg-surface2 hover:text-text"
                >
                  <ChevronDown
                    size={16}
                    aria-hidden
                    className={cn("transition", !uncategorizedOpen && "-rotate-90")}
                  />
                </button>
              }
            >
              {uncategorizedOpen ? (
                budget.uncategorized.length > 0 ? (
                  <div>
                    {budget.uncategorized.map((item) => (
                      <UncategorizedRow
                        key={item.id}
                        item={item}
                        options={bucketOptions}
                        saving={updateTx.isPending}
                        onAssign={(bucketId) =>
                          updateTx.mutate({ id: item.id, input: { bucket_id: bucketId } })
                        }
                      />
                    ))}
                  </div>
                ) : (
                  <EmptyState title="Tudo categorizado" />
                )
              ) : null}
            </SectionCard>
          </>
        )}
      </div>
    </>
  );
}
