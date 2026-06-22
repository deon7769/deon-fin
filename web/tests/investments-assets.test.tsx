import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { InvestmentAssetModal } from "@/components/investimentos/InvestmentAssetModal";
import { buildAssetPayload } from "@/lib/investments";
import type { InvestmentAsset } from "@/lib/types";

const asset: InvestmentAsset = {
  id: 7,
  asset_class: "acoes_nac",
  asset_class_label: "Ações nacionais",
  ticker: "WEGE3",
  name: "WEGE3",
  quantity: 10,
  source: "pluggy",
  external_id: "inv-wege",
  manual_value: null,
  current_value: 452.5,
  unit_price: 45.25,
  currency: "BRL",
  provider_type: "EQUITY",
  provider_subtype: "STOCK",
  status: "ACTIVE",
  as_of_date: "2026-06-21",
  manually_adjusted: false,
  manual_adjusted_at: null,
  price_source: "brapi",
  price_updated_at: "2026-06-22T10:00:00",
  pct_carteira: 8.63,
  created_at: "2026-06-22 10:00:00",
  updated_at: "2026-06-22 10:00:00",
};

describe("investment asset form", () => {
  it("builds ticker asset payload with normalized ticker and decimal quantity", () => {
    expect(
      buildAssetPayload({
        assetClass: "acoes_nac",
        ticker: " wege3 ",
        name: " Weg ",
        quantity: "10,5",
        manualValue: "",
      }),
    ).toEqual({
      asset_class: "acoes_nac",
      ticker: "WEGE3",
      name: "Weg",
      quantity: 10.5,
    });
  });

  it("builds fixed-income payload from manual value without ticker", () => {
    expect(
      buildAssetPayload({
        assetClass: "rf",
        ticker: "",
        name: " Tesouro Selic ",
        quantity: "",
        manualValue: "1.500,55",
      }),
    ).toEqual({
      asset_class: "rf",
      name: "Tesouro Selic",
      manual_value: 1500.55,
    });
  });

  it("renders create and edit modal fields", () => {
    const createHtml = renderToStaticMarkup(
      <InvestmentAssetModal
        open
        mode="create"
        onClose={() => undefined}
        onSubmit={() => undefined}
      />,
    );
    expect(createHtml).toContain("Adicionar ativo");
    expect(createHtml).toContain("Tipo de investimento");
    expect(createHtml).toContain("Ticker");
    expect(createHtml).toContain("Quantidade");

    const editHtml = renderToStaticMarkup(
      <InvestmentAssetModal
        open
        mode="edit"
        asset={asset}
        onClose={() => undefined}
        onSubmit={() => undefined}
        onDelete={() => undefined}
      />,
    );
    expect(editHtml).toContain("Editar ativo");
    expect(editHtml).toContain("WEGE3");
    expect(editHtml).toContain("Remover");
    expect(editHtml).toContain("Atualizar e fechar");
  });
});
