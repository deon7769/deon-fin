import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { InvestmentAportePanel } from "@/components/investimentos/InvestmentAportePanel";
import { aporteComprasFromSuggestions, buildAportePayload } from "@/lib/investments";
import { PrivacyProvider } from "@/providers/PrivacyProvider";
import type { InvestmentAporteResponse, InvestmentTargetsResponse } from "@/lib/types";

const targets: InvestmentTargetsResponse = {
  targets: {
    rf: 0,
    rf_int: 0,
    acoes_nac: 0,
    acoes_int: 100,
    fii: 0,
    reit: 0,
    cripto: 0,
  },
  classes: [
    { asset_class: "acoes_int", label: "Acoes internacionais", target_pct: 100 },
  ],
  perfil: "custom",
  ultimo_aporte: 1000,
  sum_pct: 100,
  valid: true,
};

const result: InvestmentAporteResponse = {
  patrimonio: 0,
  pl_alvo: 1000,
  troco: 0,
  sugestoes: [
    {
      id: 1,
      tipo: "acoes_int",
      asset_class: "acoes_int",
      ticker: "INT2",
      valor_atual: 0,
      preco: 10,
      nota: 2,
      sugest_rs: 111.11,
      sugest_un: 11.111,
      total_apos_aporte_pct: 11.11,
    },
    {
      id: 2,
      tipo: "acoes_int",
      asset_class: "acoes_int",
      ticker: "INT10",
      valor_atual: 0,
      preco: 250,
      nota: 10,
      sugest_rs: 555.56,
      sugest_un: 2.22224,
      total_apos_aporte_pct: 55.56,
    },
  ],
};

describe("investment aporte helpers", () => {
  it("normalizes aporte payload and builds confirmation purchases", () => {
    expect(buildAportePayload("1.000,50")).toEqual({ aporte: 1000.5 });
    expect(aporteComprasFromSuggestions(result)).toEqual({
      aporte: 666.67,
      compras: [
        { asset_id: 1, quantidade: 11.111 },
        { asset_id: 2, quantidade: 2.22224 },
      ],
    });
  });
});

describe("InvestmentAportePanel", () => {
  it("renders input, distribution summary, suggestions table and actions", () => {
    const html = renderToStaticMarkup(
      <PrivacyProvider>
        <InvestmentAportePanel
          targets={targets}
          result={result}
          calculating={false}
          confirming={false}
          error={null}
          onCalculate={() => undefined}
          onConfirmAll={() => undefined}
        />
      </PrivacyProvider>,
    );

    expect(html).toContain("Novo Aporte");
    expect(html).toContain("Valor do investimento");
    expect(html).toContain("Calcular");
    expect(html).toContain("Distribuicao do investimento");
    expect(html).toContain("Sugestoes de investimento");
    expect(html).toContain("INT10");
    expect(html).toContain("Aportar!");
    expect(html).toContain("Aportar tudo");
  });

  it("renders targets warning when allocation targets are invalid", () => {
    const html = renderToStaticMarkup(
      <InvestmentAportePanel
        targets={{ ...targets, valid: false, sum_pct: 80 }}
        result={null}
        calculating={false}
        confirming={false}
        error={null}
        onCalculate={() => undefined}
        onConfirmAll={() => undefined}
      />,
    );

    expect(html).toContain("ajuste as Metas da carteira para 100%");
    expect(html).toContain("/investimentos/metas");
  });
});
