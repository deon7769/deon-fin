"use client";

import { useState } from "react";
import { AlertCircle } from "lucide-react";

import { InvestmentAportePanel } from "@/components/investimentos/InvestmentAportePanel";
import { InvestmentTabs } from "@/components/investimentos/InvestmentTabs";
import { Header } from "@/components/layout/Header";
import { EmptyState } from "@/components/ui/EmptyState";
import { SectionCard } from "@/components/ui/SectionCard";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  useCalcularInvestmentAporte,
  useConfirmarInvestmentAporte,
  useInvestmentTargets,
} from "@/hooks/useInvestments";
import type {
  InvestmentAporteConfirmInput,
  InvestmentAporteCalculateInput,
  InvestmentAporteResponse,
} from "@/lib/types";

function RetryState({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  return (
    <SectionCard>
      <EmptyState
        icon={<AlertCircle size={28} aria-hidden />}
        title="Nao foi possivel carregar as metas da carteira"
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

export default function InvestmentAportePage() {
  const targets = useInvestmentTargets();
  const calcular = useCalcularInvestmentAporte();
  const confirmar = useConfirmarInvestmentAporte();
  const [result, setResult] = useState<InvestmentAporteResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const submitCalculate = async (input: InvestmentAporteCalculateInput) => {
    try {
      setError(null);
      setResult(await calcular.mutateAsync(input));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel calcular o aporte.");
    }
  };

  const submitConfirm = async (input: InvestmentAporteConfirmInput) => {
    try {
      setError(null);
      await confirmar.mutateAsync(input);
      setResult(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel confirmar o aporte.");
    }
  };

  return (
    <>
      <Header title="Investimentos" subtitle="Sugestoes de compra para o proximo aporte." />

      <div className="space-y-5 p-4 sm:p-6">
        <InvestmentTabs />

        {targets.isError ? (
          <RetryState error={targets.error} onRetry={() => void targets.refetch()} />
        ) : targets.isLoading || !targets.data ? (
          <SectionCard title="Novo Aporte">
            <Skeleton className="h-52 w-full" />
          </SectionCard>
        ) : (
          <InvestmentAportePanel
            targets={targets.data}
            result={result}
            calculating={calcular.isPending}
            confirming={confirmar.isPending}
            error={error}
            onCalculate={submitCalculate}
            onConfirmAll={submitConfirm}
          />
        )}
      </div>
    </>
  );
}
