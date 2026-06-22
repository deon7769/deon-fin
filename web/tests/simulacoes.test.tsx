import { readFileSync } from "node:fs";
import { join } from "node:path";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { menuItems } from "@/components/layout/nav";
import { SimulationResultPanel } from "@/components/simulacoes/SimulationResultPanel";
import {
  CALCULATORS,
  DEFAULT_INPUTS,
  endpointForCalculator,
  fieldsForCalculator,
  resultRows,
  summaryCards,
} from "@/lib/simulacoes";
import { PrivacyProvider } from "@/providers/PrivacyProvider";
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
    expect(DEFAULT_INPUTS["marcacao-mercado"]).toMatchObject({
      data_aplicacao: "2026-01-01",
      data_vencimento: "2030-01-01",
    });
    expect(CALCULATORS.find((item) => item.key === "cdb")?.description).toBe(
      "Rendimento bruto, IR e líquido.",
    );
  });

  it("describes friendly fields and options for calculator forms", () => {
    expect(fieldsForCalculator("juros-compostos").map((field) => field.label)).toEqual([
      "Valor inicial",
      "Aporte mensal",
      "Taxa",
      "Período da taxa",
      "Prazo",
      "Unidade do prazo",
    ]);
    expect(fieldsForCalculator("juros-compostos")[3]).toMatchObject({
      type: "select",
      options: [
        { value: "anual", label: "Anual" },
        { value: "mensal", label: "Mensal" },
      ],
    });
    expect(fieldsForCalculator("marcacao-mercado").map((field) => field.label)).toContain(
      "Título isento de IR",
    );
  });

  it("maps simulation results into summary cards and table rows", () => {
    expect(summaryCards(jurosResult)).toEqual([
      { key: "valor_final", label: "Valor final", value: "R$ 6.756,94", moneyValue: 6756.94 },
      { key: "total_investido", label: "Total investido", value: "R$ 6.500,00", moneyValue: 6500 },
      { key: "total_juros", label: "Total juros", value: "R$ 256,94", moneyValue: 256.94 },
    ]);
    expect(resultRows(jurosResult)).toEqual([
      {
        key: "1",
        month: "1",
        firstMetric: "R$ 3,22",
        firstMetricMoneyValue: 3.22,
        secondMetric: "R$ 503,22",
        secondMetricMoneyValue: 503.22,
      },
    ]);
  });

  it("renders cards and the time series table", () => {
    const html = renderToStaticMarkup(
      <PrivacyProvider>
        <SimulationResultPanel result={jurosResult} />
      </PrivacyProvider>,
    );

    expect(html).toContain("Valor final");
    expect(html).toContain("R$ 6.756,94");
    expect(html).toContain("Gráfico");
    expect(html).toContain("Série mensal");
    expect(html).toContain("R$ 503,22");
  });

  it("masks monetary simulation results when privacy mode is hidden", () => {
    const html = renderToStaticMarkup(
      <PrivacyProvider initialHidden>
        <SimulationResultPanel result={jurosResult} />
      </PrivacyProvider>,
    );

    expect(html).toContain('aria-label="valor oculto"');
    expect(html).not.toContain("R$ 6.756,94");
    expect(html).not.toContain("R$ 503,22");
  });

  it("renders market data default warnings returned by the API", () => {
    const html = renderToStaticMarkup(
      <PrivacyProvider>
        <SimulationResultPanel
          result={{
            ...jurosResult,
            avisos: [{ code: "default_cdi_aa", message: "CDI anual padrão usado: 11.5%." }],
          }}
        />
      </PrivacyProvider>,
    );

    expect(html).toContain("CDI anual padrão usado: 11.5%.");
  });

  it("moves the navigation item from simulador to simulacoes", () => {
    expect(menuItems).toContainEqual(
      expect.objectContaining({ href: "/simulacoes", label: "Simulações" }),
    );
    expect(menuItems.some((item) => item.href === "/simulador")).toBe(false);
  });

  it("redirects the old simulator route to the simulations hub", () => {
    const source = readFileSync(
      join(process.cwd(), "app", "(app)", "simulador", "page.tsx"),
      "utf8",
    );

    expect(source).toContain('redirect("/simulacoes")');
  });
});
