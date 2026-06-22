"use client";

import { useState } from "react";
import { AlertCircle } from "lucide-react";

import { InvestmentTabs } from "@/components/investimentos/InvestmentTabs";
import { InvestmentTargetsPanel } from "@/components/investimentos/InvestmentTargetsPanel";
import { Header } from "@/components/layout/Header";
import { EmptyState } from "@/components/ui/EmptyState";
import { SectionCard } from "@/components/ui/SectionCard";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  useInvestmentProfiles,
  useInvestmentTargets,
  useSaveInvestmentTargets,
} from "@/hooks/useInvestments";
import type { InvestmentTargetsMap } from "@/lib/types";

function TargetsSkeleton() {
  return (
    <>
      <SectionCard title="Perfil de Investimento">
        <div className="grid gap-3 md:grid-cols-3">
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
        </div>
      </SectionCard>
      <SectionCard title="Distribuição alvo">
        <Skeleton className="h-72" />
      </SectionCard>
    </>
  );
}

function RetryState({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  return (
    <SectionCard>
      <EmptyState
        icon={<AlertCircle size={28} aria-hidden />}
        title="Não foi possível carregar as metas da carteira"
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

export default function InvestmentTargetsPage() {
  const targetsQuery = useInvestmentTargets();
  const profilesQuery = useInvestmentProfiles();
  const saveTargets = useSaveInvestmentTargets();
  const [error, setError] = useState<string | null>(null);

  const retry = () => {
    void targetsQuery.refetch();
    void profilesQuery.refetch();
  };

  const submit = async (input: { targets: InvestmentTargetsMap; perfil?: string }) => {
    try {
      setError(null);
      await saveTargets.mutateAsync(input);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível salvar as metas.");
    }
  };

  const isError = targetsQuery.isError || profilesQuery.isError;
  const errorValue = targetsQuery.error ?? profilesQuery.error;
  const isLoading = targetsQuery.isLoading || profilesQuery.isLoading;

  return (
    <>
      <Header
        title="Investimentos"
        subtitle="Metas de alocação da carteira por classe de ativo."
      />

      <div className="space-y-5 p-4 sm:p-6">
        <InvestmentTabs />

        {isError ? (
          <RetryState error={errorValue} onRetry={retry} />
        ) : isLoading || !targetsQuery.data || !profilesQuery.data ? (
          <TargetsSkeleton />
        ) : (
          <InvestmentTargetsPanel
            targets={targetsQuery.data}
            profiles={profilesQuery.data.profiles}
            saving={saveTargets.isPending}
            error={error}
            onSave={submit}
          />
        )}
      </div>
    </>
  );
}
