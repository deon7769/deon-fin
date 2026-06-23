import { readFileSync } from "node:fs";
import { join } from "node:path";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import {
  CountryRiskPanel,
  filterInvestmentMapCountries,
  InvestmentMapPanel,
} from "@/components/investimentos/InvestmentMapPanel";
import { buildInvestmentCountryDetailsMap } from "@/lib/investments";
import type { InvestmentCountryDetail, InvestmentMapCountry } from "@/lib/types";

const countries: InvestmentMapCountry[] = [
  {
    code: "BR",
    name: "Brasil",
    name_intl: "Brazil",
    main_index: "Ibovespa",
    tier: "medium",
    tier_label: "Médio Risco",
    color: "#F59E0B",
  },
  {
    code: "US",
    name: "Estados Unidos",
    name_intl: "United States",
    main_index: "S&P 500",
    tier: "top",
    tier_label: "AAA (Prime)",
    color: "#2563EB",
  },
];

const detail: InvestmentCountryDetail = {
  code: "BR",
  name: "Brasil",
  name_intl: "Brazil",
  main_index: "Ibovespa",
  ratings: { sp: "BB", moody: "Ba2", fitch: "BB-" },
  tier: "medium",
  tier_label: "Médio Risco",
  color: "#F59E0B",
  empresas: [{ name: "Vale", ticker: "VALE3", setor: "Mineração" }],
  etfs: [{ ticker: "BOVA11", label: "ETF Brasileiro" }],
};

describe("InvestmentMapPanel", () => {
  it("builds a normalized details map for country index search", () => {
    expect(buildInvestmentCountryDetailsMap([detail, undefined])).toEqual({ BR: detail });
  });

  it("renders the map search, country list and selected country risk summary", () => {
    const html = renderToStaticMarkup(
      <InvestmentMapPanel
        countries={countries}
        selectedCode="BR"
        selectedCountry={detail}
        loadingCountry={false}
        onSelectCountry={() => undefined}
      />,
    );

    expect(html).toContain("Buscar por país ou índice");
    expect(html).toContain("Mapa de risco soberano");
    expect(html).toContain("Brasil");
    expect(html).toContain("Médio Risco");
    expect(html).toContain("Ibovespa");
    expect(html).toContain("B/CCC");
    expect(html).toContain("Sem dados");
  });

  it("renders an explicit empty state when no map countries are available", () => {
    const html = renderToStaticMarkup(
      <InvestmentMapPanel
        countries={[]}
        selectedCode={null}
        selectedCountry={null}
        loadingCountry={false}
        onSelectCountry={() => undefined}
      />,
    );

    expect(html).toContain("Nenhum pais com dados disponiveis.");
  });

  it("shows a map asset error instead of hanging on the loading state", () => {
    const source = readFileSync(
      join(process.cwd(), "components", "investimentos", "LeafletCountryMap.tsx"),
      "utf8",
    );

    expect(source).toContain("Nao foi possivel carregar o mapa.");
    expect(source).toContain("setGeoError(true)");
  });

  it("filters countries by country name or main index and keeps selection case-insensitive", () => {
    expect(filterInvestmentMapCountries(countries, {}, "ibov")).toEqual([countries[0]]);
    expect(filterInvestmentMapCountries(countries, {}, "brazil")).toEqual([countries[0]]);
    expect(filterInvestmentMapCountries(countries, { BR: detail }, "estados")).toEqual([countries[1]]);
    expect(filterInvestmentMapCountries(countries, { BR: detail }, "br")).toEqual([countries[0]]);
  });

  it("renders Indices, Empresas and ETFs tabs for the selected country", () => {
    const indicesHtml = renderToStaticMarkup(<CountryRiskPanel country={detail} activeTab="indices" />);
    expect(indicesHtml).toContain("Principal Índice");
    expect(indicesHtml).toContain("S&amp;P");
    expect(indicesHtml).toContain("Moody");
    expect(indicesHtml).toContain("Fitch");

    const empresasHtml = renderToStaticMarkup(<CountryRiskPanel country={detail} activeTab="empresas" />);
    expect(empresasHtml).toContain("Vale");
    expect(empresasHtml).toContain("VALE3");
    expect(empresasHtml).toContain("Mineração");

    const etfsHtml = renderToStaticMarkup(<CountryRiskPanel country={detail} activeTab="etfs" />);
    expect(etfsHtml).toContain("BOVA11");
    expect(etfsHtml).toContain("ETF Brasileiro");
  });
});
