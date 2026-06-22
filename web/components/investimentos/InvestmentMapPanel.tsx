"use client";

import dynamic from "next/dynamic";
import { useMemo, useState } from "react";
import { Globe2, Search } from "lucide-react";

import { cn } from "@/lib/cn";
import type { InvestmentCountryDetail, InvestmentMapCountry } from "@/lib/types";

const LeafletCountryMap = dynamic(
  () => import("./LeafletCountryMap").then((mod) => mod.LeafletCountryMap),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full min-h-[320px] items-center justify-center rounded-md border border-border bg-surface2 text-sm text-muted">
        Carregando mapa...
      </div>
    ),
  },
);

export type CountryPanelTab = "indices" | "empresas" | "etfs";

type InvestmentMapPanelProps = {
  countries: InvestmentMapCountry[];
  selectedCode: string | null;
  selectedCountry: InvestmentCountryDetail | null;
  loadingCountry: boolean;
  countryDetails?: Record<string, InvestmentCountryDetail>;
  countryError?: string | null;
  onSelectCountry: (code: string) => void;
};

type CountryRiskPanelProps = {
  country: InvestmentCountryDetail;
  activeTab?: CountryPanelTab;
  onTabChange?: (tab: CountryPanelTab) => void;
};

const TABS: Array<{ key: CountryPanelTab; label: string }> = [
  { key: "indices", label: "Índices" },
  { key: "empresas", label: "Empresas" },
  { key: "etfs", label: "ETFs" },
];

function normalize(value: string) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

export function filterInvestmentMapCountries(
  countries: InvestmentMapCountry[],
  details: Record<string, InvestmentCountryDetail>,
  query: string,
) {
  const term = normalize(query.trim());
  if (!term) {
    return countries;
  }

  return countries.filter((country) => {
    const detail = details[country.code.toUpperCase()];
    return [
      country.code,
      country.name,
      detail?.name,
      detail?.name_intl,
      detail?.main_index,
    ].some((value) => value && normalize(value).includes(term));
  });
}

function EmptyPanel() {
  return (
    <div className="flex min-h-[320px] flex-col items-center justify-center rounded-md border border-border bg-surface p-6 text-center">
      <Globe2 size={28} className="text-blue-300" aria-hidden />
      <h2 className="mt-3 text-base font-semibold text-text">Selecione um país</h2>
      <p className="mt-2 max-w-sm text-sm leading-6 text-muted">
        Clique no mapa ou use a busca para abrir índices, ratings, empresas e ETFs.
      </p>
    </div>
  );
}

function RiskBadge({ country }: { country: InvestmentCountryDetail }) {
  return (
    <span
      className="inline-flex w-fit items-center rounded-full border px-2.5 py-1 text-xs font-semibold"
      style={{ borderColor: country.color, color: country.color, backgroundColor: `${country.color}1f` }}
    >
      {country.tier_label}
    </span>
  );
}

function RatingRow({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="rounded-md border border-border bg-surface2 p-3">
      <dt className="text-xs font-medium uppercase tracking-normal text-muted">{label}</dt>
      <dd className="mt-1 text-lg font-semibold text-text">{value ?? "--"}</dd>
    </div>
  );
}

export function CountryRiskPanel({ country, activeTab = "indices", onTabChange }: CountryRiskPanelProps) {
  return (
    <aside className="rounded-md border border-border bg-surface p-4">
      <div className="flex flex-col gap-3 border-b border-border pb-4">
        <div>
          <h2 className="text-xl font-semibold text-text">{country.name}</h2>
          <p className="mt-1 text-sm text-muted">{country.name_intl}</p>
        </div>
        <RiskBadge country={country} />
      </div>

      <div className="mt-4 grid grid-cols-3 rounded-md border border-border bg-surface2 p-1" role="tablist">
        {TABS.map((tab) => {
          const active = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => onTabChange?.(tab.key)}
              className={cn(
                "h-9 rounded px-2 text-sm font-medium transition",
                active ? "bg-blue-500 text-white" : "text-muted hover:bg-surface hover:text-text",
              )}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      <div className="mt-4">
        {activeTab === "indices" ? (
          <div className="space-y-4">
            <div className="rounded-md border border-border bg-surface2 p-3">
              <div className="text-xs font-medium uppercase tracking-normal text-muted">Principal Índice</div>
              <div className="mt-1 text-lg font-semibold text-text">{country.main_index}</div>
            </div>
            <dl className="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
              <RatingRow label="S&P" value={country.ratings.sp} />
              <RatingRow label="Moody's" value={country.ratings.moody} />
              <RatingRow label="Fitch" value={country.ratings.fitch} />
            </dl>
          </div>
        ) : null}

        {activeTab === "empresas" ? (
          <div className="space-y-2">
            {country.empresas.length === 0 ? (
              <p className="text-sm text-muted">Sem empresas cadastradas.</p>
            ) : (
              country.empresas.map((empresa) => (
                <div key={`${empresa.ticker}-${empresa.name}`} className="rounded-md border border-border bg-surface2 p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="font-medium text-text">{empresa.name}</div>
                      <div className="mt-1 text-xs text-muted">{empresa.setor}</div>
                    </div>
                    <span className="rounded-md bg-blue-500/15 px-2 py-1 text-xs font-semibold text-blue-200">
                      {empresa.ticker}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        ) : null}

        {activeTab === "etfs" ? (
          <div className="space-y-2">
            {country.etfs.length === 0 ? (
              <p className="text-sm text-muted">Sem ETFs cadastrados.</p>
            ) : (
              country.etfs.map((etf) => (
                <div key={etf.ticker} className="flex items-center justify-between gap-3 rounded-md border border-border bg-surface2 p-3">
                  <span className="font-semibold text-text">{etf.ticker}</span>
                  <span className="text-sm text-muted">{etf.label ?? "ETF"}</span>
                </div>
              ))
            )}
          </div>
        ) : null}
      </div>
    </aside>
  );
}

export function InvestmentMapPanel({
  countries,
  selectedCode,
  selectedCountry,
  loadingCountry,
  countryDetails = {},
  countryError = null,
  onSelectCountry,
}: InvestmentMapPanelProps) {
  const [query, setQuery] = useState("");
  const [activeTab, setActiveTab] = useState<CountryPanelTab>("indices");
  const details = useMemo(
    () => (selectedCountry ? { ...countryDetails, [selectedCountry.code.toUpperCase()]: selectedCountry } : countryDetails),
    [countryDetails, selectedCountry],
  );
  const filteredCountries = useMemo(
    () => filterInvestmentMapCountries(countries, details, query),
    [countries, details, query],
  );

  const selectCountry = (code: string) => {
    setActiveTab("indices");
    onSelectCountry(code);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text">Mapa de risco soberano</h1>
          <p className="mt-1 text-sm text-muted">Verifique abaixo a saúde financeira de cada país.</p>
        </div>
        <label className="relative block w-full lg:max-w-sm">
          <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" aria-hidden />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Buscar por país ou índice..."
            className="h-10 w-full rounded-md border border-border bg-surface py-2 pl-9 pr-3 text-sm text-text outline-none transition placeholder:text-muted focus:border-blue-500"
            aria-label="Buscar por país ou índice"
          />
        </label>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_380px]">
        <section className="rounded-md border border-border bg-surface p-3">
          <div className="h-[420px]">
            <LeafletCountryMap
              countries={countries}
              selectedCode={selectedCode}
              onSelectCountry={selectCountry}
            />
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {filteredCountries.length === 0 ? (
              <div className="rounded-md border border-dashed border-border bg-surface2 px-3 py-2 text-sm text-muted">
                {countries.length === 0
                  ? "Nenhum pais com dados disponiveis."
                  : "Nenhum pais encontrado para a busca."}
              </div>
            ) : (
              filteredCountries.map((country) => {
                const active = selectedCode?.toUpperCase() === country.code.toUpperCase();
                return (
                  <button
                    key={country.code}
                    type="button"
                    onClick={() => selectCountry(country.code)}
                    className={cn(
                      "inline-flex h-9 items-center gap-2 rounded-md border px-3 text-sm font-medium transition",
                      active
                        ? "border-blue-400 bg-blue-500/15 text-blue-100"
                        : "border-border bg-surface2 text-muted hover:border-blue-400/60 hover:text-text",
                    )}
                  >
                    <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: country.color }} aria-hidden />
                    {country.name}
                  </button>
                );
              })
            )}
          </div>
        </section>

        {loadingCountry ? (
          <div className="flex min-h-[320px] items-center justify-center rounded-md border border-border bg-surface text-sm text-muted">
            Carregando pais...
          </div>
        ) : countryError ? (
          <div className="rounded-md border border-negative/40 bg-negative/10 p-4 text-sm text-negative">{countryError}</div>
        ) : selectedCountry ? (
          <CountryRiskPanel country={selectedCountry} activeTab={activeTab} onTabChange={setActiveTab} />
        ) : (
          <EmptyPanel />
        )}
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        {[
          ["top", "AAA", "#2563EB"],
          ["high", "AA/A", "#22C55E"],
          ["medium", "BBB/BB", "#F59E0B"],
        ].map(([key, label, color]) => (
          <div key={key} className="flex items-center gap-2 rounded-md border border-border bg-surface px-3 py-2 text-sm text-muted">
            <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: color }} aria-hidden />
            <span>{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
