"use client";

import { useMemo, useState } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";

import { InvestmentMapPanel } from "@/components/investimentos/InvestmentMapPanel";
import { InvestmentTabs } from "@/components/investimentos/InvestmentTabs";
import { Header } from "@/components/layout/Header";
import { EmptyState } from "@/components/ui/EmptyState";
import { SectionCard } from "@/components/ui/SectionCard";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  useInvestmentCountry,
  useInvestmentCountryDetails,
  useInvestmentMap,
} from "@/hooks/useInvestments";
import { buildInvestmentCountryDetailsMap } from "@/lib/investments";

function MapSkeleton() {
  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_380px]">
      <SectionCard>
        <Skeleton className="h-[420px]" />
      </SectionCard>
      <SectionCard>
        <Skeleton className="h-8 w-44" />
        <Skeleton className="mt-4 h-10 w-32" />
        <Skeleton className="mt-4 h-52" />
      </SectionCard>
    </div>
  );
}

function RetryState({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  return (
    <SectionCard>
      <EmptyState
        icon={<AlertCircle size={28} aria-hidden />}
        title="Não foi possível carregar o mapa"
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

export default function InvestmentMapPage() {
  const mapQuery = useInvestmentMap();
  const [selectedCode, setSelectedCode] = useState<string | null>(null);
  const activeCode = selectedCode ?? mapQuery.data?.[0]?.code ?? null;
  const countryQuery = useInvestmentCountry(activeCode);
  const detailQueries = useInvestmentCountryDetails(mapQuery.data ?? []);
  const countryDetails = useMemo(
    () =>
      buildInvestmentCountryDetailsMap([
        ...detailQueries.map((query) => query.data),
        countryQuery.data,
      ]),
    [countryQuery.data, detailQueries],
  );

  const selectedCountry = useMemo(() => {
    if (!activeCode) {
      return null;
    }
    return countryQuery.data ?? countryDetails[activeCode.toUpperCase()] ?? null;
  }, [activeCode, countryDetails, countryQuery.data]);

  return (
    <>
      <Header title="Investimentos" subtitle="Mapa de rating soberano por país." />

      <div className="space-y-5 p-4 sm:p-6">
        <InvestmentTabs />

        {mapQuery.isError ? (
          <RetryState error={mapQuery.error} onRetry={() => void mapQuery.refetch()} />
        ) : mapQuery.isLoading || !mapQuery.data ? (
          <MapSkeleton />
        ) : (
          <InvestmentMapPanel
            countries={mapQuery.data}
            selectedCode={activeCode}
            selectedCountry={selectedCountry}
            loadingCountry={countryQuery.isLoading}
            countryDetails={countryDetails}
            countryError={countryQuery.isError && countryQuery.error instanceof Error ? countryQuery.error.message : null}
            onSelectCountry={setSelectedCode}
          />
        )}
      </div>
    </>
  );
}
