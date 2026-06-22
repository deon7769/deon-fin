"use client";

import { useState, useSyncExternalStore } from "react";
import Link from "next/link";
import { AlertCircle, BarChart3 } from "lucide-react";
import { HistoryBarChart } from "@/components/charts/HistoryBarChart";
import { TagDonut } from "@/components/charts/TagDonut";
import { Header } from "@/components/layout/Header";
import { EmptyState } from "@/components/ui/EmptyState";
import { InfoTip } from "@/components/ui/InfoTip";
import { KpiCard } from "@/components/ui/KpiCard";
import { MoneyText } from "@/components/ui/MoneyText";
import { SectionCard } from "@/components/ui/SectionCard";
import { Skeleton } from "@/components/ui/Skeleton";
import { TypeToggle } from "@/components/ui/TypeToggle";
import { WindowToggle } from "@/components/ui/WindowToggle";
import { usePainelByTag, usePainelHistory, usePainelSummary } from "@/hooks/usePainel";
import { useProfileName } from "@/hooks/useProfileName";
import { greetingForHour } from "@/lib/greeting";
import { hasUntaggedSlice } from "@/lib/painel";
import type { PainelHistoryWindow, PainelTagType } from "@/lib/types";

function subscribeHour(onStoreChange: () => void) {
  if (typeof window === "undefined") {
    return () => undefined;
  }
  const interval = window.setInterval(onStoreChange, 60_000);
  return () => window.clearInterval(interval);
}

function getCurrentHour() {
  return new Date().getHours();
}

function getServerHour() {
  return 12;
}

export default function PainelPage() {
  const [historyWindow, setHistoryWindow] = useState<PainelHistoryWindow>("6m");
  const [tagType, setTagType] = useState<PainelTagType>("expense");
  const currentHour = useSyncExternalStore(subscribeHour, getCurrentHour, getServerHour);
  const { name } = useProfileName();
  const summary = usePainelSummary();
  const history = usePainelHistory(historyWindow);
  const byTag = usePainelByTag(tagType);

  const greeting = greetingForHour(currentHour, name);
  const hasHistoryData = history.data?.some((point) => point.income !== 0 || point.expense !== 0) ?? false;
  const showCategorizeCta = byTag.data ? hasUntaggedSlice(byTag.data.items) : false;
  const tagSubtitle =
    tagType === "expense" ? "Distribuição dos gastos do mês atual" : "Distribuição das receitas do mês atual";

  return (
    <>
      <Header title={greeting} subtitle="O que está acontecendo hoje?" />

      <div className="space-y-5 p-4 sm:p-6">
        {summary.isError ? (
          <SectionCard>
            <EmptyState
              icon={<AlertCircle size={28} aria-hidden />}
              title="Não foi possível carregar os KPIs"
              description={summary.error instanceof Error ? summary.error.message : undefined}
              action={
                <button
                  type="button"
                  onClick={() => void summary.refetch()}
                  className="h-9 rounded-md border border-border px-3 text-sm font-medium text-text transition hover:bg-surface2"
                >
                  Tentar novamente
                </button>
              }
            />
          </SectionCard>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {summary.isLoading || !summary.data ? (
              <>
                <KpiCard title="Resultado do Período" value={<Skeleton className="h-8 w-32" />} />
                <KpiCard title="Receitas" value={<Skeleton className="h-8 w-32" />} />
                <KpiCard title="Despesas" value={<Skeleton className="h-8 w-32" />} />
                <KpiCard title="Saldo em conta" value={<Skeleton className="h-8 w-32" />} />
              </>
            ) : (
              <>
                <KpiCard
                  title="Resultado do Período"
                  value={<MoneyText value={summary.data.result} />}
                  subtitle="Receitas menos despesas"
                  tone={summary.data.result < 0 ? "negative" : "positive"}
                  icon={<InfoTip label="Resultado do mês selecionado: receitas menos despesas." />}
                />
                <KpiCard
                  title="Receitas"
                  value={<MoneyText value={summary.data.income} />}
                  subtitle="Entradas reconhecidas no mês"
                  tone="positive"
                  icon={<InfoTip label="Soma das receitas por competência, excluindo movimentos internos." />}
                />
                <KpiCard
                  title="Despesas"
                  value={<MoneyText value={summary.data.expense} />}
                  subtitle="Gastos reconhecidos no mês"
                  tone="negative"
                  icon={<InfoTip label="Compras e débitos de consumo, sem pagamento de fatura duplicado." />}
                />
                <KpiCard
                  title="Saldo em conta"
                  value={<MoneyText value={summary.data.accounts_balance} />}
                  subtitle={
                    summary.data.accounts_balance_available
                      ? "Soma dos saldos conectados"
                      : "Indisponível até o sync de contas"
                  }
                  tone={summary.data.accounts_balance_available ? "default" : "accent"}
                  icon={<InfoTip label="Lido de account_balances. Antes do sync de contas, fica indisponível." />}
                />
              </>
            )}
          </div>
        )}

        <div className="grid gap-5 xl:grid-cols-[minmax(0,1.35fr)_minmax(340px,0.65fr)]">
          <SectionCard
            title="Histórico Financeiro"
            subtitle="Comparativo mensal de entradas e saídas"
            actions={<WindowToggle value={historyWindow} onChange={setHistoryWindow} />}
          >
            {history.isLoading ? (
              <Skeleton className="h-[320px] w-full" />
            ) : history.isError ? (
              <EmptyState
                icon={<AlertCircle size={28} aria-hidden />}
                title="Não foi possível carregar o histórico"
                description={history.error instanceof Error ? history.error.message : undefined}
                action={
                  <button
                    type="button"
                    onClick={() => void history.refetch()}
                    className="h-9 rounded-md border border-border px-3 text-sm font-medium text-text transition hover:bg-surface2"
                  >
                    Tentar novamente
                  </button>
                }
              />
            ) : history.data && hasHistoryData ? (
              <HistoryBarChart data={history.data} />
            ) : (
              <EmptyState icon={<BarChart3 size={28} aria-hidden />} title="Sem dados no período" />
            )}
          </SectionCard>

          <SectionCard
            title="Transações por Tags"
            subtitle={tagSubtitle}
            actions={<TypeToggle value={tagType} onChange={setTagType} />}
          >
            {byTag.isLoading ? (
              <Skeleton className="h-[320px] w-full" />
            ) : byTag.isError ? (
              <EmptyState
                icon={<AlertCircle size={28} aria-hidden />}
                title="Não foi possível carregar as tags"
                description={byTag.error instanceof Error ? byTag.error.message : undefined}
                action={
                  <button
                    type="button"
                    onClick={() => void byTag.refetch()}
                    className="h-9 rounded-md border border-border px-3 text-sm font-medium text-text transition hover:bg-surface2"
                  >
                    Tentar novamente
                  </button>
                }
              />
            ) : byTag.data && byTag.data.total > 0 ? (
              <div className="space-y-4">
                <TagDonut items={byTag.data.items} total={byTag.data.total} />
                {showCategorizeCta ? (
                  <Link
                    href="/transacoes?semTag=1"
                    className="inline-flex h-10 w-full items-center justify-center rounded-md bg-accent px-4 text-sm font-semibold text-accentFg transition hover:opacity-90"
                  >
                    Categorize todas as transações
                  </Link>
                ) : null}
              </div>
            ) : (
              <EmptyState title="Nenhuma transação neste mês" />
            )}
          </SectionCard>
        </div>

      </div>
    </>
  );
}
