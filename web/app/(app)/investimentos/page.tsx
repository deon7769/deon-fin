"use client";

import { useState } from "react";
import { AlertCircle, BriefcaseBusiness, CircleDollarSign, PieChart, RefreshCw } from "lucide-react";
import { Header } from "@/components/layout/Header";
import { EmptyState } from "@/components/ui/EmptyState";
import { KpiCard } from "@/components/ui/KpiCard";
import { MoneyText } from "@/components/ui/MoneyText";
import { Pill } from "@/components/ui/Pill";
import { SectionCard } from "@/components/ui/SectionCard";
import { Skeleton } from "@/components/ui/Skeleton";
import { useInvestments } from "@/hooks/useInvestments";
import { formatDate } from "@/lib/format";
import type { InvestmentAsset, InvestmentClassSummary } from "@/lib/types";

const CLASS_COLORS: Record<string, string> = {
  acoes_nac: "#3b82f6",
  fii: "#22c55e",
  rf: "#f59e0b",
  cripto: "#a855f7",
  acoes_int: "#06b6d4",
  reit: "#ef4444",
  rf_int: "#84cc16",
};

const STATUS_LABELS: Record<string, string> = {
  ACTIVE: "Ativo",
  TOTAL_WITHDRAWAL: "Encerrado",
};

function RetryState({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  return (
    <SectionCard>
      <EmptyState
        icon={<AlertCircle size={28} aria-hidden />}
        title="Não foi possível carregar a carteira"
        description={error instanceof Error ? error.message : undefined}
        action={
          <button
            type="button"
            onClick={onRetry}
            className="inline-flex h-9 items-center gap-2 rounded-md border border-border px-3 text-sm font-medium text-text transition hover:bg-surface2"
          >
            <RefreshCw size={16} aria-hidden />
            Tentar novamente
          </button>
        }
      />
    </SectionCard>
  );
}

function InvestmentsSkeleton() {
  return (
    <>
      <div className="grid gap-4 md:grid-cols-3">
        <KpiCard title="Patrimônio investido" value={<Skeleton className="h-8 w-32" />} />
        <KpiCard title="Ativos" value={<Skeleton className="h-8 w-20" />} />
        <KpiCard title="Classes" value={<Skeleton className="h-8 w-20" />} />
      </div>
      <SectionCard>
        <Skeleton className="h-72 w-full" />
      </SectionCard>
    </>
  );
}

function AllocationRows({ items, total }: { items: InvestmentClassSummary[]; total: number }) {
  return (
    <div className="space-y-4">
      {items.map((item) => (
        <div key={item.asset_class} className="space-y-2">
          <div className="flex items-center justify-between gap-3 text-sm">
            <div className="flex min-w-0 items-center gap-2">
              <span
                className="h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ backgroundColor: CLASS_COLORS[item.asset_class] ?? "#94a3b8" }}
                aria-hidden
              />
              <span className="truncate font-medium text-text">{item.label}</span>
              <span className="text-muted">{item.count}</span>
            </div>
            <div className="shrink-0 text-right">
              <MoneyText value={item.current_value} className="font-medium" />
              <span className="ml-2 text-xs text-muted">{item.pct.toFixed(2)}%</span>
            </div>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-surface2">
            <div
              className="h-full rounded-full"
              style={{
                width: `${total > 0 ? Math.min(100, Math.max(0, item.pct)) : 0}%`,
                backgroundColor: CLASS_COLORS[item.asset_class] ?? "#94a3b8",
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function statusLabel(status: string | null) {
  if (!status) {
    return "Sem status";
  }
  return STATUS_LABELS[status] ?? status;
}

function displayDate(value: string | null) {
  return value ? formatDate(value) : "--";
}

function AssetsTable({ assets }: { assets: InvestmentAsset[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-[920px] w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs font-semibold uppercase tracking-normal text-muted">
            <th className="py-3 pr-4">Tipo</th>
            <th className="px-4 py-3">Ativo</th>
            <th className="px-4 py-3 text-right">Valor atual</th>
            <th className="px-4 py-3 text-right">Quantidade</th>
            <th className="px-4 py-3 text-right">Preço</th>
            <th className="px-4 py-3">Status</th>
            <th className="py-3 pl-4">Atualização</th>
          </tr>
        </thead>
        <tbody>
          {assets.map((asset) => (
            <tr key={asset.id} className="border-b border-border last:border-0">
              <td className="py-3 pr-4">
                <Pill color={CLASS_COLORS[asset.asset_class]}>{asset.asset_class_label}</Pill>
              </td>
              <td className="px-4 py-3">
                <div className="font-medium text-text">{asset.ticker ?? asset.name ?? "--"}</div>
                <div className="mt-1 text-xs text-muted">{asset.provider_subtype ?? asset.provider_type ?? asset.source}</div>
              </td>
              <td className="px-4 py-3 text-right font-medium">
                <MoneyText value={asset.current_value} />
              </td>
              <td className="px-4 py-3 text-right tabular-nums text-text">{asset.quantity.toLocaleString("pt-BR")}</td>
              <td className="px-4 py-3 text-right">
                {asset.unit_price === null ? <span className="text-muted">--</span> : <MoneyText value={asset.unit_price} />}
              </td>
              <td className="px-4 py-3 text-muted">{statusLabel(asset.status)}</td>
              <td className="py-3 pl-4 text-muted">{displayDate(asset.as_of_date)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function InvestimentosPage() {
  const [includeInactive, setIncludeInactive] = useState(false);
  const investments = useInvestments(includeInactive);
  const data = investments.data;

  return (
    <>
      <Header title="Investimentos" subtitle="Carteira sincronizada pelas conexões bancárias." />

      <div className="space-y-5 p-4 sm:p-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <label className="inline-flex w-fit items-center gap-2 rounded-md border border-border bg-surface px-3 py-2 text-sm text-muted">
            <input
              type="checkbox"
              checked={includeInactive}
              onChange={(event) => setIncludeInactive(event.target.checked)}
              className="h-4 w-4 accent-[var(--accent)]"
            />
            Incluir encerrados
          </label>
          <button
            type="button"
            onClick={() => void investments.refetch()}
            className="inline-flex h-10 w-fit items-center gap-2 rounded-md border border-border bg-surface px-3 text-sm font-medium text-text transition hover:bg-surface2"
          >
            <RefreshCw size={16} aria-hidden />
            Atualizar
          </button>
        </div>

        {investments.isError ? (
          <RetryState error={investments.error} onRetry={() => void investments.refetch()} />
        ) : investments.isLoading || !data ? (
          <InvestmentsSkeleton />
        ) : (
          <>
            <div className="grid gap-4 md:grid-cols-3">
              <KpiCard
                title="Patrimônio investido"
                value={<MoneyText value={data.totals.current_value} />}
                subtitle={includeInactive ? "Incluindo posições encerradas" : "Posições ativas"}
                icon={<CircleDollarSign size={18} aria-hidden />}
              />
              <KpiCard
                title="Ativos"
                value={data.totals.asset_count}
                subtitle={`${data.assets.filter((asset) => asset.source === "pluggy").length} via Pluggy`}
                icon={<BriefcaseBusiness size={18} aria-hidden />}
              />
              <KpiCard
                title="Classes"
                value={data.by_class.length}
                subtitle={data.by_class.map((item) => item.label).join(", ") || "Sem classes"}
                icon={<PieChart size={18} aria-hidden />}
              />
            </div>

            {data.assets.length === 0 ? (
              <SectionCard>
                <EmptyState
                  icon={<PieChart size={28} aria-hidden />}
                  title="Nenhum ativo sincronizado"
                />
              </SectionCard>
            ) : (
              <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
                <SectionCard
                  title="Ativos"
                  subtitle={`${data.assets.length} posição(ões)`}
                >
                  <AssetsTable assets={data.assets} />
                </SectionCard>

                <SectionCard
                  title="Alocação por classe"
                  subtitle={`Total: ${data.totals.asset_count} ativo(s)`}
                >
                  <AllocationRows items={data.by_class} total={data.totals.current_value} />
                </SectionCard>
              </div>
            )}
          </>
        )}
      </div>
    </>
  );
}
