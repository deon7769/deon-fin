"use client";

import { useMemo } from "react";
import { AlertCircle, DatabaseZap, Landmark, ListChecks, RefreshCw, Wallet } from "lucide-react";
import { CategoryMapPreview } from "@/components/manutencao/CategoryMapPreview";
import { HealthChecklist } from "@/components/manutencao/HealthChecklist";
import { MaintenanceSectionTable } from "@/components/manutencao/MaintenanceSectionTable";
import { RecurrenceRulesTable } from "@/components/manutencao/RecurrenceRulesTable";
import { Header } from "@/components/layout/Header";
import { EmptyState } from "@/components/ui/EmptyState";
import { KpiCard } from "@/components/ui/KpiCard";
import { MoneyText } from "@/components/ui/MoneyText";
import { SectionCard } from "@/components/ui/SectionCard";
import { Skeleton } from "@/components/ui/Skeleton";
import { useMaintenance } from "@/hooks/useMaintenance";
import {
  buildMaintenanceHealth,
  buildMaintenanceSections,
  maintenanceSummary,
} from "@/lib/maintenance";

function MaintenanceSkeleton() {
  return (
    <>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <KpiCard key={index} title="Carregando" value={<Skeleton className="h-8 w-28" />} />
        ))}
      </div>
      <SectionCard title="Saúde dos dados">
        <Skeleton className="h-56 w-full" />
      </SectionCard>
      <SectionCard title="Seções monitoradas">
        <Skeleton className="h-72 w-full" />
      </SectionCard>
    </>
  );
}

function RetryState({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  return (
    <SectionCard>
      <EmptyState
        icon={<AlertCircle size={28} aria-hidden />}
        title="Não foi possível carregar a manutenção"
        description={error instanceof Error ? error.message : undefined}
        action={
          <button
            type="button"
            onClick={onRetry}
            className="inline-flex h-9 items-center gap-2 rounded-md border border-border px-3 text-sm font-medium text-text transition hover:bg-surface2"
          >
            <RefreshCw size={15} aria-hidden />
            Tentar novamente
          </button>
        }
      />
    </SectionCard>
  );
}

export default function ManutencaoPage() {
  const maintenance = useMaintenance();
  const data = maintenance.data;
  const summary = useMemo(() => (data ? maintenanceSummary(data) : null), [data]);
  const sections = useMemo(() => (data ? buildMaintenanceSections(data) : []), [data]);
  const health = useMemo(() => (data ? buildMaintenanceHealth(data) : null), [data]);

  return (
    <>
      <Header
        title="Manutenção"
        subtitle="Saúde dos dados fixos e de/para usados pelas análises."
      />

      <div className="space-y-5 p-4 sm:p-6">
        {maintenance.isError ? (
          <RetryState error={maintenance.error} onRetry={() => void maintenance.refetch()} />
        ) : maintenance.isLoading || !data || !summary || !health ? (
          <MaintenanceSkeleton />
        ) : (
          <>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <KpiCard
                title="Renda informada"
                value={<MoneyText value={summary.incomeTotal} />}
                subtitle={`${data.family_profile.receitas?.length ?? 0} receita(s)`}
                icon={<Wallet size={18} aria-hidden />}
              />
              <KpiCard
                title="Reserva e caixa"
                value={<MoneyText value={summary.cashTotal} />}
                subtitle={`${data.family_profile.patrimonio?.investimentos_caixa?.length ?? 0} posição(ões)`}
                icon={<DatabaseZap size={18} aria-hidden />}
              />
              <KpiCard
                title="Provisões mensais"
                value={<MoneyText value={summary.provisionMonthlyTotal} />}
                subtitle={`${data.family_profile.provisoes?.length ?? 0} provisão(ões)`}
                icon={<ListChecks size={18} aria-hidden />}
              />
              <KpiCard
                title="Patrimônio em imóveis"
                value={<MoneyText value={summary.propertyEquity} />}
                subtitle={`${data.family_profile.patrimonio?.imoveis?.length ?? 0} imóvel(is)`}
                icon={<Landmark size={18} aria-hidden />}
              />
            </div>

            <SectionCard
              title="Saúde dos dados"
              subtitle={
                health.status === "ok"
                  ? "Todas as seções principais possuem dados."
                  : `${summary.missingSections} seção(ões) pedem revisão.`
              }
              actions={
                <a
                  href="/legacy"
                  className="inline-flex h-9 items-center rounded-md border border-border px-3 text-sm font-medium text-text transition hover:bg-surface2"
                >
                  Abrir editor legado
                </a>
              }
            >
              <HealthChecklist health={health} />
            </SectionCard>

            <SectionCard
              title="Seções monitoradas"
              subtitle={`${summary.configuredSections} de 8 seções com dados configurados`}
            >
              <MaintenanceSectionTable rows={sections} />
            </SectionCard>

            <div className="grid gap-5 xl:grid-cols-2">
              <SectionCard
                title="Tradução de categorias"
                subtitle={`${summary.categoryCount} de/para configurado(s); mostrando os primeiros 10.`}
              >
                <CategoryMapPreview overrides={data.overrides} />
              </SectionCard>

              <SectionCard
                title="Regras de recorrência"
                subtitle={`${summary.recurrenceCount} regra(s); mostrando as primeiras 8.`}
              >
                <RecurrenceRulesTable overrides={data.overrides} />
              </SectionCard>
            </div>
          </>
        )}
      </div>
    </>
  );
}
