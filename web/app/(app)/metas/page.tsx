"use client";

import { useState } from "react";
import Link from "next/link";
import { AlertCircle, Plus, Target, Wallet } from "lucide-react";
import { BucketAllocationPanel } from "@/components/metas/BucketAllocationPanel";
import { SavingsGoalCard } from "@/components/metas/SavingsGoalCard";
import { SavingsGoalModal } from "@/components/metas/SavingsGoalModal";
import { SavingsGoalReconciliationModal } from "@/components/metas/SavingsGoalReconciliationModal";
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
  useSavingsGoals,
  useUpdateBucket,
  useUpdateGoal,
  type SavingsGoalInput,
} from "@/hooks/useMetas";
import { formatBRL } from "@/lib/format";
import type { BucketPlanPatch } from "@/lib/metas";
import type { SavingsGoal } from "@/lib/types";

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

export default function MetasPage() {
  const [modalGoal, setModalGoal] = useState<SavingsGoal | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [reconcileGoal, setReconcileGoal] = useState<SavingsGoal | null>(null);
  const [modalError, setModalError] = useState<string | null>(null);
  const [allocationError, setAllocationError] = useState<string | null>(null);

  const bucketPlan = useBucketPlan();
  const savings = useSavingsGoals();
  const updateBucket = useUpdateBucket();
  const createGoal = useCreateGoal();
  const updateGoal = useUpdateGoal();
  const deleteGoal = useDeleteGoal();
  const plan = bucketPlan.data;
  const goals = savings.data;

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

  const saveBucketAllocations = async (
    updates: Array<{ id: number; input: BucketPlanPatch }>,
  ) => {
    try {
      setAllocationError(null);
      await Promise.all(updates.map((update) => updateBucket.mutateAsync(update)));
    } catch (error) {
      setAllocationError(error instanceof Error ? error.message : "Erro ao salvar metas");
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

            <BucketAllocationPanel
              buckets={plan.buckets}
              income={plan.income}
              saving={updateBucket.isPending}
              error={allocationError}
              onSave={saveBucketAllocations}
            />
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
                    onReconcile={() => setReconcileGoal(goal)}
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
      <SavingsGoalReconciliationModal
        open={reconcileGoal !== null}
        goal={reconcileGoal}
        onClose={() => setReconcileGoal(null)}
      />
    </>
  );
}
