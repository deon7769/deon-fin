import { describe, expect, it } from "vitest";

import {
  DEFAULT_AMORTIZATION_INPUT,
  DEFAULT_SCENARIO_INPUT,
  amortizationRows,
  propertyToAmortizationInput,
  scenarioSummary,
  validateAmortizationInput,
  validateScenarioInput,
} from "@/lib/simulator";
import type {
  AmortizationResponse,
  MaintenanceResponse,
  ScenarioSimulationResponse,
} from "@/lib/types";

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

describe("simulator helpers", () => {
  it("rejects invalid scenario inputs before API calls", () => {
    expect(validateScenarioInput({ ...DEFAULT_SCENARIO_INPUT, preco: 0 })).toEqual({
      valid: false,
      message: "Informe um preço maior que zero.",
    });
    expect(validateScenarioInput({ ...DEFAULT_SCENARIO_INPUT, preco: 50000, entrada: 60000 })).toEqual({
      valid: false,
      message: "A entrada não pode ser maior que o preço.",
    });
    expect(validateScenarioInput({ ...DEFAULT_SCENARIO_INPUT, prazo_meses: 48 })).toEqual({
      valid: true,
    });
  });

  it("rejects amortization inputs that cannot pay first-month interest", () => {
    expect(validateAmortizationInput({ ...DEFAULT_AMORTIZATION_INPUT, saldo: 100000, juros_aa: 60, parcela: 100 })).toEqual({
      valid: false,
      message: "A parcela precisa cobrir os juros do primeiro mês.",
    });
    expect(validateAmortizationInput({ ...DEFAULT_AMORTIZATION_INPUT, saldo: 30000, juros_aa: 12, parcela: 1000 })).toEqual({
      valid: true,
    });
  });

  it("maps scenario responses into strategy cards", () => {
    const summary = scenarioSummary(scenarioResult);

    expect(summary.map((card) => card.key)).toEqual(["financiar", "consorcio", "juntar"]);
    expect(summary[0].title).toBe("Financiar");
    expect(summary[0].items).toContainEqual({
      label: "Parcela Price",
      value: "R$ 1.304,40/mês",
      tone: "neutral",
    });
    expect(summary[2].items).toContainEqual({
      label: "Economia vs. Price",
      value: "R$ 22.611,20",
      tone: "positive",
    });
  });

  it("maps amortization responses into table rows", () => {
    expect(amortizationRows(amortizationResult)).toEqual([
      { key: "sem_extra", label: "Sem aporte extra", months: "35 meses", interest: "R$ 4.360,39", tone: "neutral" },
      { key: "com_extra", label: "Com aporte de R$ 500,00/mês", months: "22 meses", interest: "R$ 2.683,55", tone: "positive" },
      { key: "economia", label: "Você economiza", months: "13 meses", interest: "R$ 1.676,84", tone: "positive" },
    ]);
  });

  it("extracts amortization defaults from the first configured property", () => {
    const maintenance: MaintenanceResponse = {
      family_profile: {
        patrimonio: {
          imoveis: [
            {
              nome: "Apê",
              saldo_devedor: 32200.6,
              taxa_juros_anual: 4.5,
              custos: { financiamento: 395 },
            },
          ],
        },
      },
      overrides: {},
    };

    expect(propertyToAmortizationInput(maintenance)).toEqual({
      saldo: 32200.6,
      juros_aa: 4.5,
      parcela: 395,
      aporte_extra: DEFAULT_AMORTIZATION_INPUT.aporte_extra,
    });
  });
});
