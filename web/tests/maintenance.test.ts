import { describe, expect, it } from "vitest";

import {
  buildMaintenanceHealth,
  buildMaintenanceSections,
  maintenanceSummary,
  recurrenceTypeLabel,
} from "@/lib/maintenance";
import type { MaintenanceResponse } from "@/lib/types";

const sample: MaintenanceResponse = {
  family_profile: {
    receitas: [{ membro: "Davi", valor: 5000 }],
    provisoes: [{ nome: "IPTU", mensal: 200 }],
    metas: [{ nome: "Reserva", alvo: 20000, atual: 3500 }],
    wishlist: [{ nome: "Viagem", valor_alvo: 7000, prazo_meses: 10, guardado: 1000 }],
    patrimonio: {
      investimentos_caixa: [{ local: "Inter", valor: 12000, aporte_mensal_recorrente: 500 }],
      imoveis: [{ nome: "Casa", valor_mercado: 300000, saldo_devedor: 120000 }],
    },
  },
  overrides: {
    categorias_pt: { groceries: "Mercado", rent: "Aluguel" },
    recorrencias: [{ match: "netflix", tipo: "assinatura", rotulo: "Netflix" }],
  },
};

describe("maintenance helpers", () => {
  it("summarizes configured sections", () => {
    expect(maintenanceSummary(sample)).toEqual({
      incomeTotal: 5000,
      cashTotal: 12000,
      provisionMonthlyTotal: 200,
      propertyEquity: 180000,
      categoryCount: 2,
      recurrenceCount: 1,
      configuredSections: 8,
      missingSections: 0,
    });
  });

  it("builds section rows with counts and totals", () => {
    expect(buildMaintenanceSections(sample).map((section) => section.key)).toEqual([
      "receitas",
      "caixa",
      "provisoes",
      "metas",
      "wishlist",
      "imoveis",
      "categorias",
      "recorrencias",
    ]);
  });

  it("reports missing sections as review items", () => {
    const health = buildMaintenanceHealth({
      family_profile: {},
      overrides: { categorias_pt: {}, recorrencias: [] },
    });

    expect(health.status).toBe("review");
    expect(health.items.map((item) => item.key)).toContain("receitas");
    expect(health.items.map((item) => item.key)).toContain("categorias");
  });

  it("labels recurrence types", () => {
    expect(recurrenceTypeLabel("assinatura")).toBe("Assinatura");
    expect(recurrenceTypeLabel("recorrencia")).toBe("Recorrência");
    expect(recurrenceTypeLabel("ignorar")).toBe("Ignorar");
    expect(recurrenceTypeLabel("x")).toBe("x");
  });
});
