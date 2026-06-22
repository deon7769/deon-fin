"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { AlertCircle, Plus, Target, Wallet } from "lucide-react";
import { BucketPlanRow } from "@/components/metas/BucketPlanRow";
import { SavingsGoalCard } from "@/components/metas/SavingsGoalCard";
import { SavingsGoalModal } from "@/components/metas/SavingsGoalModal";
import { SumBadge } from "@/components/metas/SumBadge";
import { Header } from "@/components/layout/Header";
import { EmptyState } from "@/components/ui/EmptyState";
import { KpiCard } from "@/components/ui/KpiCard";
import { MoneyText } from "@/components/ui/MoneyText";
import { SectionCard } from "@/components/ui/SectionCard";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  useBucketPlan,
  useCreateGoal,
  useDeleteGoal,
  useReorderBuckets,
  useSavingsGoals,
  useUpdateBucket,
  useUpdateGoal,
  type SavingsGoalInput,
} from "@/hooks/useMetas";
import { formatBRL } from "@/lib/format";
import type { BucketPlanItem, SavingsGoal } from "@/lib/types";

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

function MetasSkeleton() {
  return (
    <>
      <div className="grid gap-4 md:grid-cols-3">
        <KpiCard title="Renda planejada" value={<Skeleton className="h-8 w-32" />} />
        <KpiCard title="Distribuído" value={<Skeleton className="h-8 w-32" />} />
        <KpiCard title="Aporte mensal" value={<Skeleton className="h-8 w-32" />} />
      </div>
      <SectionCard title="Distribuição da renda">
        <Skeleton className="h-72 w-full" />
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
        action={
          <Link
            href="/perfil"
            className="inline-flex h-10 items-center rounded-md bg-accent px-4 text-sm font-semibold text-accentFg transition hover:brightness-95"
          >
            Abrir perfil
          </Link>
        }
      />
    </SectionCard>
  );
}

function moveBucket(items: BucketPlanItem[], index: number, direction: -1 | 1): BucketPlanItem[] {
  const target = index + direction;
  if (target < 0 || target >= items.length) {
    return items;
  }
  const next = [...items];
  const [item] = next.splice(index, 1);
  next.splice(target, 0, item);
  return next;
}

export default function MetasPage() {
  const [bucketOrder, setBucketOrder] = useState<number[]>([]);
  const [modalGoal, setModalGoal] = useState<SavingsGoal | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  const bucketPlan = useBucketPlan();
  const savings = useSavingsGoals();
  const updateBucket = useUpdateBucket();
  const reorderBuckets = useReorderBuckets();
  const createGoal = useCreateGoal();
  const updateGoal = useUpdateGoal();
  const deleteGoal = useDeleteGoal();
  const plan = bucketPlan.data;
  const goals = savings.data;
  const buckets = useMemo(() => {
    const source = plan?.buckets ?? [];
    if (!bucketOrder.length || bucketOrder.length !== source.length) {
      return source;
    }
    const byId = new Map(source.map((bucket) => [bucket.id, bucket]));
    const ordered = bucketOrder
      .map((id) => byId.get(id))
      .filter((bucket): bucket is BucketPlanItem => Boolean(bucket));
    return ordered.length === source.length ? ordered : source;
  }, [bucketOrder, plan?.buckets]);

  const moveAndPersist = (index: number, direction: -1 | 1) => {
    const next = moveBucket(buckets, index, direction);
    if (next === buckets) {
      return;
    }
    setBucketOrder(next.map((bucket) => bucket.id));
    reorderBuckets.mutate(next.map((bucket) => bucket.id));
  };

  const openCreateModal = () => {
    setModalGoal(null);
    setModalError(null);
    setModalOpen(true);
  };

  const openEditModal = (goal: SavingsGoal) => {
    setModalGoal(goal);
    setModalError(null);
    setModalOpen(true);
  };

  const closeModal = () => {
    setModalOpen(false);
    setModalGoal(null);
    setModalError(null);
  };

  const saveGoal = async (input: SavingsGoalInput) => {
    try {
      setModalError(null);
      if (modalGoal) {
        await updateGoal.mutateAsync({ id: modalGoal.id, input });
      } else {
        await createGoal.mutateAsync(input);
      }
      closeModal();
    } catch (error) {
      setModalError(error instanceof Error ? error.message : "Erro ao salvar");
    }
  };

  const removeGoal = (goal: SavingsGoal) => {
    const confirmed = window.confirm(`Excluir ${goal.name}?`);
    if (confirmed) {
      deleteGoal.mutate(goal.id);
    }
  };

  return (
    <>
      <Header title="Metas" subtitle="Distribuição da renda e plano de poupança." />

      <div className="space-y-5 p-4 sm:p-6">
        {bucketPlan.isError ? (
          <RetryState
            title="Não foi possível carregar as metas"
            error={bucketPlan.error}
            onRetry={() => void bucketPlan.refetch()}
          />
        ) : bucketPlan.isLoading || !plan ? (
          <MetasSkeleton />
        ) : (
          <>
            {plan.income_source === "none" || plan.income <= 0 ? <IncomeEmptyState /> : null}

            <div className="grid gap-4 md:grid-cols-3">
              <KpiCard
                title="Renda planejada"
                value={<MoneyText value={plan.income} />}
                subtitle={plan.income_source === "transactions" ? "Receitas do mês" : "Valor de referência"}
                icon={<Wallet size={18} aria-hidden />}
              />
              <KpiCard
                title="Distribuído"
                value={<MoneyText value={plan.sum_amount} />}
                subtitle={`${plan.sum_percent}% em metas percentuais`}
                tone={plan.warning ? "accent" : "positive"}
                icon={<Target size={18} aria-hidden />}
              />
              <KpiCard
                title="Aporte mensal"
                value={<MoneyText value={goals?.total_monthly_required ?? 0} />}
                subtitle={
                  goals ? `Sobra após metas: ${formatBRL(goals.surplus_after_goals)}` : "Carregando"
                }
                tone={(goals?.surplus_after_goals ?? 0) < 0 ? "negative" : "positive"}
              />
            </div>

            <SectionCard
              title="Distribuição da renda"
              subtitle={`Total planejado: ${formatBRL(plan.sum_amount)}`}
              actions={<SumBadge plan={plan} />}
            >
              <div className="hidden border-b border-border pb-2 text-xs font-medium uppercase tracking-normal text-muted xl:grid xl:grid-cols-[minmax(160px,1.1fr)_150px_130px_90px_minmax(170px,1fr)_120px]">
                <span>Meta</span>
                <span>Modo</span>
                <span>Planejado</span>
                <span>Cor</span>
                <span>Realizado</span>
                <span className="text-right">Ações</span>
              </div>
              {buckets.map((bucket, index) => (
                <BucketPlanRow
                  key={`${bucket.id}:${bucket.name}:${bucket.color}:${bucket.planned_kind}:${bucket.planned_value}`}
                  bucket={bucket}
                  first={index === 0}
                  last={index === buckets.length - 1}
                  saving={updateBucket.isPending}
                  moving={reorderBuckets.isPending}
                  onMove={(direction) => moveAndPersist(index, direction)}
                  onSave={(bucketId, input) =>
                    updateBucket.mutateAsync({ id: bucketId, input }).then(() => undefined)
                  }
                />
              ))}
            </SectionCard>
          </>
        )}

        {savings.isError ? (
          <RetryState
            title="Não foi possível carregar a poupança"
            error={savings.error}
            onRetry={() => void savings.refetch()}
          />
        ) : (
          <SectionCard
            title="Metas de poupança"
            subtitle={
              goals
                ? `${goals.goals.length} meta(s), sobra mensal de ${formatBRL(goals.monthly_surplus)}`
                : undefined
            }
            actions={
              <button
                type="button"
                onClick={openCreateModal}
                className="inline-flex h-9 items-center gap-2 rounded-md bg-accent px-3 text-sm font-semibold text-accentFg transition hover:brightness-95"
              >
                <Plus size={16} aria-hidden />
                Nova meta
              </button>
            }
          >
            {savings.isLoading || !goals ? (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {Array.from({ length: 3 }).map((_, index) => (
                  <Skeleton key={index} className="h-56 w-full" />
                ))}
              </div>
            ) : goals.goals.length ? (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {goals.goals.map((goal) => (
                  <SavingsGoalCard
                    key={goal.id}
                    goal={goal}
                    deleting={deleteGoal.isPending && deleteGoal.variables === goal.id}
                    onEdit={() => openEditModal(goal)}
                    onDelete={() => removeGoal(goal)}
                  />
                ))}
              </div>
            ) : (
              <EmptyState icon={<Target size={28} aria-hidden />} title="Nenhuma meta cadastrada" />
            )}
          </SectionCard>
        )}
      </div>

      <SavingsGoalModal
        open={modalOpen}
        goal={modalGoal}
        saving={createGoal.isPending || updateGoal.isPending}
        error={modalError}
        onClose={closeModal}
        onSubmit={saveGoal}
      />
    </>
  );
}
