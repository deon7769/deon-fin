import { describe, expect, it } from "vitest";
import { createElement, type ComponentType } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { EditableMaintenanceTable } from "@/components/manutencao/EditableMaintenanceTable";
import {
  buildMaintenanceSavePayload,
  buildMaintenanceHealth,
  buildMaintenanceSections,
  maintenanceToEditorState,
  maintenanceSummary,
  missingCategoryTranslations,
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
      imoveis: [
        {
          nome: "Casa",
          valor_mercado: 300000,
          saldo_devedor: 120000,
          taxa_juros_anual: 8.5,
          prazo_restante_meses: 180,
          custos: { financiamento: 1200, condominio: 450, iptu_lixo: 150 },
        },
      ],
    },
    observacao_livre: "preservar",
  },
  overrides: {
    categorias_pt: { groceries: "Mercado", rent: "Aluguel" },
    recorrencias: [{ match: "netflix", tipo: "assinatura", rotulo: "Netflix" }],
  },
  category_audit: {
    total_categories: 3,
    translated: 2,
    missing: [{ category: "Pet Shops", tx_count: 2, total_abs: 70 }],
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

  it("converts maintenance data to editable rows", () => {
    const editor = maintenanceToEditorState(sample);

    expect(editor.categorias).toEqual([
      { en: "groceries", pt: "Mercado" },
      { en: "rent", pt: "Aluguel" },
    ]);
    expect(editor.imoveis[0]).toMatchObject({
      nome: "Casa",
      valor_mercado: 300000,
      saldo_devedor: 120000,
      taxa_juros_anual: 8.5,
      prazo_restante_meses: 180,
      custo_financiamento: 1200,
      custo_condominio: 450,
      custo_iptu_lixo: 150,
    });
  });

  it("builds a save payload while preserving unknown profile fields", () => {
    const editor = maintenanceToEditorState(sample);
    editor.categorias = [
      { en: " Groceries ", pt: "Mercado atualizado" },
      { en: "", pt: "sem origem" },
      { en: "New Category", pt: "Nova categoria" },
    ];
    editor.imoveis = [
      {
        ...editor.imoveis[0],
        custo_financiamento: 1300,
        custo_condominio: 500,
        custo_iptu_lixo: 180,
      },
    ];

    const payload = buildMaintenanceSavePayload(sample, editor);

    expect(payload.family_profile.observacao_livre).toBe("preservar");
    expect(payload.overrides.categorias_pt).toEqual({
      groceries: "Mercado atualizado",
      "new category": "Nova categoria",
    });
    expect(payload.family_profile.patrimonio?.imoveis?.[0]).toMatchObject({
      nome: "Casa",
      custos: { financiamento: 1300, condominio: 500, iptu_lixo: 180 },
    });
  });

  it("maps missing category translations from the maintenance audit", () => {
    expect(missingCategoryTranslations(sample)).toEqual([
      { category: "Pet Shops", txCount: 2, totalAbs: 70 },
    ]);
    expect(missingCategoryTranslations({ family_profile: {}, overrides: {} })).toEqual([]);
  });

  it("renders wide editable sections as responsive field groups", () => {
    const Component = EditableMaintenanceTable as ComponentType<Record<string, unknown>>;
    const html = renderToStaticMarkup(
      createElement(Component, {
        section: "imoveis",
        title: "Imoveis",
        rows: [
          {
            nome: "Casa",
            valor_mercado: 300000,
            saldo_devedor: 120000,
            taxa_juros_anual: 8.5,
            prazo_restante_meses: 180,
            aluguel_receita: 0,
            custo_financiamento: 1200,
            custo_condominio: 450,
            custo_iptu_lixo: 150,
          },
        ],
        columns: [
          { key: "nome", label: "Imovel", type: "text" },
          { key: "valor_mercado", label: "Valor mercado", type: "number" },
          { key: "saldo_devedor", label: "Saldo devedor", type: "number" },
          { key: "taxa_juros_anual", label: "Juros", type: "number" },
          { key: "prazo_restante_meses", label: "Prazo", type: "number" },
          { key: "aluguel_receita", label: "Aluguel", type: "number" },
          { key: "custo_financiamento", label: "Financiamento", type: "number" },
          { key: "custo_condominio", label: "Condominio", type: "number" },
          { key: "custo_iptu_lixo", label: "IPTU", type: "number" },
        ],
        onChange: () => undefined,
      }),
    );

    expect(html).toContain('data-layout="cards"');
    expect(html).not.toContain("<table");
  });
});
