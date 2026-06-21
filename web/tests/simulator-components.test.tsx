import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { AmortizationResult } from "@/components/simulador/AmortizationResult";
import { ScenarioResult } from "@/components/simulador/ScenarioResult";
import type { AmortizationResponse, ScenarioSimulationResponse } from "@/lib/types";

const scenarioResult: ScenarioSimulationResponse = {
  entrada: 10000,
  valor_financiado: 40000,
  financiar: {
    price: {
      sistema: "price",
      parcela: 1304.4,
      total_parcelas: 62611.2,
      total_juros: 22611.2,
    },
    sac: {
      sistema: "sac",
      primeira_parcela: 1468.79,
      ultima_parcela: 847.36,
      total_parcelas: 55587.38,
      total_juros: 15587.38,
    },
    custo_total_price: 72611.2,
    custo_total_sac: 65587.38,
  },
  consorcio: {
    sistema: "consorcio",
    taxa_adm_pct: 18,
    parcela: 1229.17,
    total_parcelas: 59000,
    custo_taxa_adm: 9000,
  },
  juntar_a_vista: {
    aporte_mensal: 2000,
    rendimento_aa: 0,
    meses_para_juntar: 25,
    anos_para_juntar: 2.1,
    custo_total: 50000,
  },
  economia_juntando_vs_price: 22611.2,
};

const amortizationResult: AmortizationResponse = {
  saldo: 30000,
  parcela_atual: 1000,
  aporte_extra: 500,
  sem_extra: { meses: 35, juros_pagos: 4360.39 },
  com_extra: { meses: 22, juros_pagos: 2683.55 },
  meses_economizados: 13,
  juros_economizados: 1676.84,
};

describe("simulator result components", () => {
  it("renders scenario strategy cards", () => {
    const html = renderToStaticMarkup(<ScenarioResult result={scenarioResult} />);

    expect(html).toContain("Financiar");
    expect(html).toContain("Consórcio");
    expect(html).toContain("Juntar à vista");
    expect(html).toContain("R$ 1.304,40/mês");
    expect(html).toContain("R$ 22.611,20");
  });

  it("renders amortization savings rows", () => {
    const html = renderToStaticMarkup(<AmortizationResult result={amortizationResult} />);

    expect(html).toContain("Sem aporte extra");
    expect(html).toContain("Com aporte de R$ 500,00/mês");
    expect(html).toContain("Você economiza");
    expect(html).toContain("13 meses");
    expect(html).toContain("R$ 1.676,84");
  });
});
