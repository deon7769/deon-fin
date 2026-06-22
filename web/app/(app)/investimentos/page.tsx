"use client";

import { useState } from "react";
import { AlertCircle, BriefcaseBusiness, CircleDollarSign, Pencil, PieChart, Plus, RefreshCw } from "lucide-react";
import { InvestmentAssetModal } from "@/components/investimentos/InvestmentAssetModal";
import { InvestmentTabs } from "@/components/investimentos/InvestmentTabs";
import { Header } from "@/components/layout/Header";
import { EmptyState } from "@/components/ui/EmptyState";
import { KpiCard } from "@/components/ui/KpiCard";
import { MoneyText } from "@/components/ui/MoneyText";
import { Pill } from "@/components/ui/Pill";
import { SectionCard } from "@/components/ui/SectionCard";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  useCreateInvestmentAsset,
  useDeleteInvestmentAsset,
  useInvestmentAssetAnswers,
  useInvestments,
  useRefreshInvestmentQuotes,
  useSaveInvestmentAssetAnswers,
  useTickerSearch,
  useUpdateInvestmentAsset,
} from "@/hooks/useInvestments";
import { formatDate } from "@/lib/format";
import type { InvestmentAsset, InvestmentAssetInput, InvestmentClassSummary } from "@/lib/types";

const CLASS_COLORS: Record<string, string> = {
  acoes_nac: "#3b82f6",
  etf: "#14b8a6",
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

function priceSourceLabel(value: string | null) {
  if (value === "brapi") {
    return "brapi";
  }
  if (value === "manual") {
    return "manual";
  }
  if (value === "pluggy") {
    return "Pluggy";
  }
  return "sem fonte";
}

function AssetsTable({ assets, onEdit }: { assets: InvestmentAsset[]; onEdit: (asset: InvestmentAsset) => void }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-[1160px] w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs font-semibold uppercase tracking-normal text-muted">
            <th className="py-3 pr-4">Tipo</th>
            <th className="px-4 py-3">Ativo</th>
            <th className="px-4 py-3 text-right">Valor atual</th>
            <th className="px-4 py-3 text-right">% carteira</th>
            <th className="px-4 py-3 text-right">Quantidade</th>
            <th className="px-4 py-3 text-right">Preço</th>
            <th className="px-4 py-3">Status</th>
            <th className="py-3 pl-4">Atualização</th>
            <th className="py-3 pl-4 text-right">Ação</th>
          </tr>
        </thead>
        <tbody>
          {assets.map((asset) => (
            <tr key={asset.id} className="border-b border-border last:border-0">
              <td className="py-3 pr-4">
                <Pill color={CLASS_COLORS[asset.asset_class]}>{asset.asset_class_label}</Pill>
              </td>
              <td className="px-4 py-3">
                <div className="flex min-w-0 items-center gap-2">
                  <div className="truncate font-medium text-text">{asset.ticker ?? asset.name ?? "--"}</div>
                  {asset.manually_adjusted ? (
                    <span
                      title="Ajustado na mão; o Pluggy sobrescreve no próximo sync"
                      className="shrink-0 rounded-full border border-blue-400/40 bg-blue-500/10 px-2 py-0.5 text-[11px] font-semibold text-blue-300"
                    >
                      manual
                    </span>
                  ) : null}
                </div>
                <div className="mt-1 text-xs text-muted">{asset.provider_subtype ?? asset.provider_type ?? asset.source}</div>
              </td>
              <td className="px-4 py-3 text-right font-medium">
                <MoneyText value={asset.current_value} />
              </td>
              <td className="px-4 py-3 text-right tabular-nums text-text">{asset.pct_carteira.toFixed(2)}%</td>
              <td className="px-4 py-3 text-right tabular-nums text-text">{asset.quantity.toLocaleString("pt-BR")}</td>
              <td className="px-4 py-3 text-right">
                {asset.unit_price === null ? <span className="text-muted">--</span> : <MoneyText value={asset.unit_price} />}
              </td>
              <td className="px-4 py-3 text-muted">{statusLabel(asset.status)}</td>
              <td className="py-3 pl-4 text-muted">
                <div>{displayDate(asset.price_updated_at ?? asset.as_of_date)}</div>
                <div className="mt-1 text-xs">{priceSourceLabel(asset.price_source)}</div>
              </td>
              <td className="py-3 pl-4 text-right">
                <button
                  type="button"
                  onClick={() => onEdit(asset)}
                  aria-label={`Editar ${asset.ticker ?? asset.name ?? "ativo"}`}
                  className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-border text-muted transition hover:bg-surface2 hover:text-text"
                  title="Editar"
                >
                  <Pencil size={16} aria-hidden />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function InvestimentosPage() {
  const [includeInactive, setIncludeInactive] = useState(false);
  const [modalAsset, setModalAsset] = useState<InvestmentAsset | null>(null);
  const [modalMode, setModalMode] = useState<"create" | "edit" | null>(null);
  const [modalError, setModalError] = useState<string | null>(null);
  const [tickerSearch, setTickerSearch] = useState("");
  const [modalAssetClass, setModalAssetClass] = useState("acoes_nac");
  const investments = useInvestments(includeInactive);
  const refreshQuotes = useRefreshInvestmentQuotes();
  const createAsset = useCreateInvestmentAsset();
  const updateAsset = useUpdateInvestmentAsset();
  const deleteAsset = useDeleteInvestmentAsset();
  const saveAssetAnswers = useSaveInvestmentAssetAnswers();
  const tickerOptions = useTickerSearch(tickerSearch, modalAssetClass);
  const assetAnswers = useInvestmentAssetAnswers(
    modalAsset?.id ?? null,
    modalMode === "edit" && modalAsset !== null,
  );
  const data = investments.data;
  const modalOpen = modalMode !== null;
  const modalSaving = createAsset.isPending || updateAsset.isPending;

  const openCreateModal = () => {
    setModalMode("create");
    setModalAsset(null);
    setModalError(null);
    setTickerSearch("");
    setModalAssetClass("acoes_nac");
  };

  const openEditModal = (asset: InvestmentAsset) => {
    setModalMode("edit");
    setModalAsset(asset);
    setModalError(null);
    setTickerSearch(asset.ticker ?? "");
    setModalAssetClass(asset.asset_class);
  };

  const closeModal = () => {
    setModalMode(null);
    setModalAsset(null);
    setModalError(null);
    setTickerSearch("");
  };

  const submitAsset = async (input: InvestmentAssetInput) => {
    try {
      setModalError(null);
      if (modalMode === "edit" && modalAsset) {
        await updateAsset.mutateAsync({ id: modalAsset.id, input });
      } else {
        await createAsset.mutateAsync(input);
      }
      closeModal();
    } catch (error) {
      setModalError(error instanceof Error ? error.message : "Não foi possível salvar o ativo.");
    }
  };

  const removeAsset = async () => {
    if (!modalAsset) {
      return;
    }
    const confirmed = window.confirm(`Remover ${modalAsset.ticker ?? modalAsset.name ?? "ativo"}?`);
    if (!confirmed) {
      return;
    }
    try {
      setModalError(null);
      await deleteAsset.mutateAsync(modalAsset.id);
      closeModal();
    } catch (error) {
      setModalError(error instanceof Error ? error.message : "Não foi possível remover o ativo.");
    }
  };

  const saveScoreAnswers = async (answers: Array<{ question_id: number; resposta: boolean }>) => {
    if (!modalAsset) {
      return;
    }
    try {
      setModalError(null);
      await saveAssetAnswers.mutateAsync({
        id: modalAsset.id,
        input: { answers },
      });
    } catch (error) {
      setModalError(error instanceof Error ? error.message : "NÃ£o foi possÃ­vel salvar as respostas.");
    }
  };

  return (
    <>
      <Header title="Investimentos" subtitle="Carteira sincronizada pelas conexões bancárias." />

      <div className="space-y-5 p-4 sm:p-6">
        <InvestmentTabs />

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <label className="inline-flex w-fit items-center gap-2 rounded-md border border-border bg-surface px-3 py-2 text-sm text-muted">
            <input
              type="checkbox"
              checked={includeInactive}
              onChange={(event) => setIncludeInactive(event.target.checked)}
              className="h-4 w-4 accent-accent"
            />
            Incluir encerrados
          </label>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={openCreateModal}
              className="inline-flex h-10 w-fit items-center gap-2 rounded-md bg-blue-500 px-3 text-sm font-medium text-white transition hover:bg-blue-600"
            >
              <Plus size={16} aria-hidden />
              Adicionar ativo
            </button>
            <button
              type="button"
              onClick={() => refreshQuotes.mutate()}
              disabled={refreshQuotes.isPending}
              className="inline-flex h-10 w-fit items-center gap-2 rounded-md border border-blue-400/40 bg-blue-500/10 px-3 text-sm font-medium text-blue-200 transition hover:bg-blue-500/20 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <RefreshCw size={16} aria-hidden className={refreshQuotes.isPending ? "animate-spin" : undefined} />
              {refreshQuotes.isPending ? "Atualizando..." : "Atualizar cotações"}
            </button>
          </div>
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
                  action={
                    <button
                      type="button"
                      onClick={openCreateModal}
                      className="inline-flex h-9 items-center gap-2 rounded-md bg-blue-500 px-3 text-sm font-medium text-white transition hover:bg-blue-600"
                    >
                      <Plus size={16} aria-hidden />
                      Adicionar ativo
                    </button>
                  }
                />
              </SectionCard>
            ) : (
              <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
                <SectionCard
                  title="Ativos"
                  subtitle={`${data.assets.length} posição(ões)`}
                >
                  <AssetsTable assets={data.assets} onEdit={openEditModal} />
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

      <InvestmentAssetModal
        open={modalOpen}
        mode={modalMode ?? "create"}
        asset={modalAsset}
        scoreAnswers={modalMode === "edit" ? assetAnswers.data ?? null : null}
        scoreLoading={modalMode === "edit" && assetAnswers.isLoading}
        scoreSaving={saveAssetAnswers.isPending}
        tickerOptions={tickerOptions.data ?? []}
        saving={modalSaving}
        deleting={deleteAsset.isPending}
        error={modalError}
        onClose={closeModal}
        onSubmit={submitAsset}
        onDelete={modalMode === "edit" ? removeAsset : undefined}
        onScoreAnswersSave={modalMode === "edit" ? saveScoreAnswers : undefined}
        onTickerSearchChange={setTickerSearch}
        onAssetClassChange={setModalAssetClass}
      />
    </>
  );
}
