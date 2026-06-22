import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { SimulationResultPanel } from "@/components/simulacoes/SimulationResultPanel";
import {
  CALCULATORS,
  DEFAULT_INPUTS,
  endpointForCalculator,
  resultRows,
  summaryCards,
} from "@/lib/simulacoes";
import { menuItems } from "@/components/layout/nav";
import type { SimulationResponse } from "@/lib/simulacoes";

const jurosResult: SimulationResponse = {
  resumo: {
    valor_final: 6756.94,
    total_investido: 6500,
    total_juros: 256.94,
  },
  serie: [
    {
      mes: 1,
      juros: 3.22,
      total_investido: 500,
      total_juros: 3.22,
      total_acumulado: 503.22,
    },
  ],
};

describe("simulacoes hub helpers", () => {
  it("exposes the seven F3.6 calculators and API endpoints", () => {
    expect(CALCULATORS.map((item) => item.key)).toEqual([
      "juros-compostos",
      "renda",
      "pix-parcelado",
      "cdb",
      "marcacao-mercado",
      "amortizacao",
      "imovel",
    ]);
    expect(endpointForCalculator("juros-compostos")).toBe("/sim/juros-compostos");
    expect(endpointForCalculator("imovel")).toBe("/sim/imovel");
    expect(DEFAULT_INPUTS["juros-compostos"]).toMatchObject({
      valor_inicial: 500,
      valor_mensal: 500,
    });
  });

  it("maps simulation results into summary cards and table rows", () => {
    expect(summaryCards(jurosResult)).toEqual([
      { key: "valor_final", label: "Valor final", value: "R$ 6.756,94" },
      { key: "total_investido", label: "Total investido", value: "R$ 6.500,00" },
      { key: "total_juros", label: "Total juros", value: "R$ 256,94" },
    ]);
    expect(resultRows(jurosResult)).toEqual([
      {
        key: "1",
        month: "1",
        firstMetric: "R$ 3,22",
        secondMetric: "R$ 503,22",
      },
    ]);
  });

  it("renders cards and the time series table", () => {
    const html = renderToStaticMarkup(<SimulationResultPanel result={jurosResult} />);

    expect(html).toContain("Valor final");
    expect(html).toContain("R$ 6.756,94");
    expect(html).toContain("Gráfico");
    expect(html).toContain("Série mensal");
    expect(html).toContain("R$ 503,22");
  });

  it("moves the navigation item from simulador to simulacoes", () => {
    expect(menuItems).toContainEqual(
      expect.objectContaining({ href: "/simulacoes", label: "Simulações" }),
    );
    expect(menuItems.some((item) => item.href === "/simulador")).toBe(false);
  });
});
