import { describe, expect, it } from "vitest";
import { createElement, type ComponentType } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { ClassificationHealthPanel } from "@/components/manutencao/ClassificationHealthPanel";
import { ClassificationAuditPanel } from "@/components/manutencao/ClassificationAuditPanel";
import { ClassificationRulesPanel } from "@/components/manutencao/ClassificationRulesPanel";
import { EditableMaintenanceTable } from "@/components/manutencao/EditableMaintenanceTable";
import { PrivacyProvider } from "@/providers/PrivacyProvider";
import {
  buildMaintenanceSavePayload,
  buildMaintenanceHealth,
  buildMaintenanceSections,
  classificationCoverage,
  classificationIssueRows,
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
  classification_health: {
    total_transactions: 10,
    tagged: 7,
    untagged: 3,
    bucketed: 8,
    unbucketed: 2,
    tag_sources: { manual: 2, rule: 1, auto: 4, none: 3 },
    bucket_sources: { manual: 3, rule: 1, auto: 4, none: 2 },
    missing_tag_review_count: 1,
    missing_bucket_review_count: 1,
    ignored_tag_policy_count: 1,
    ignored_bucket_policy_count: 2,
    missing_tag: [
      {
        id: "tx-missing-tag",
        date: "2026-06-02",
        description: "Pet shop",
        account_name: "Bank",
        category: "Pet Shops",
        category_label: "Pet Shops",
        amount_abs: 70,
      },
    ],
    missing_bucket: [
      {
        id: "tx-missing-bucket",
        date: "2026-06-03",
        description: "Sem meta",
        account_name: "Card",
        category: "Services",
        category_label: "Serviços",
        amount_abs: 120,
      },
    ],
    ignored_tag_policy: [
      {
        id: "tx-card-payment",
        date: "2026-06-04",
        description: "Pagamento fatura",
        account_name: "Card",
        category: "Payment",
        category_label: "Payment",
        amount_abs: 900,
        reason: "card_payment",
        reason_label: "Pagamento de fatura",
      },
    ],
    ignored_bucket_policy: [
      {
        id: "tx-card-payment",
        date: "2026-06-04",
        description: "Pagamento fatura",
        account_name: "Card",
        category: "Payment",
        category_label: "Payment",
        amount_abs: 900,
        reason: "card_payment",
        reason_label: "Pagamento de fatura",
      },
      {
        id: "tx-iof",
        date: "2026-06-05",
        description: "IOF",
        account_name: "Bank",
        category: "Tax on financial operations",
        category_label: "Tax on financial operations",
        amount_abs: 22,
        reason: "financial_cost",
        reason_label: "Custo financeiro sem pote",
      },
    ],
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

  it("computes classification coverage from maintenance health", () => {
    expect(classificationCoverage(sample)).toEqual({
      tagPct: 70,
      bucketPct: 80,
      tagLabel: "7 de 10",
      bucketLabel: "8 de 10",
      missingTagReviewCount: 1,
      missingBucketReviewCount: 1,
    });
    expect(classificationCoverage({ family_profile: {}, overrides: {} })).toEqual({
      tagPct: 0,
      bucketPct: 0,
      tagLabel: "0 de 0",
      bucketLabel: "0 de 0",
      missingTagReviewCount: 0,
      missingBucketReviewCount: 0,
    });
  });

  it("maps classification issue queues to renderable rows", () => {
    expect(classificationIssueRows(sample, "missing_tag")).toEqual([
      {
        id: "tx-missing-tag",
        date: "2026-06-02",
        description: "Pet shop",
        accountName: "Bank",
        categoryLabel: "Pet Shops",
        amountAbs: 70,
      },
    ]);
    expect(classificationIssueRows(sample, "missing_bucket")[0]).toMatchObject({
      id: "tx-missing-bucket",
      accountName: "Card",
      categoryLabel: "Serviços",
      amountAbs: 120,
    });
  });

  it("renders classification health panel with coverage and issue queues", () => {
    const html = renderToStaticMarkup(
      createElement(
        PrivacyProvider,
        null,
        createElement(ClassificationHealthPanel, { data: sample, month: "2026-06" }),
      ),
    );

    expect(html).toContain("Cobertura de Tags");
    expect(html).toContain("7 de 10");
    expect(html).toContain("Cobertura de Metas");
    expect(html).toContain("8 de 10");
    expect(html).toContain("Pet shop");
    expect(html).toContain("Sem meta");
    expect(html).toContain("Abrir fila sem Tag");
    expect(html).toContain("month=2026-06");
    expect(html).toContain("quality=missing_tag");
    expect(html).toContain("Abrir fila sem Meta");
    expect(html).toContain("quality=missing_bucket");
    expect(html).toContain("Ignorados por política");
    expect(html).toContain("Pagamento de fatura");
    expect(html).toContain("Custo financeiro sem pote");
  });

  it("renders classification action controls for reprocess and bulk preview", () => {
    const html = renderToStaticMarkup(
      createElement(
        PrivacyProvider,
        null,
        createElement(ClassificationHealthPanel, {
          data: sample,
          month: "2026-06",
          buckets: [{ id: 1, key: "conforto", name: "Conforto", color: "#06b6d4" }],
          tags: [{ id: 2, name: "Mercado", color: "#22c55e" }],
          onReprocess: async () => ({ changed: 0 }),
          onPreviewBulk: async () => ({
            kind: "tag" as const,
            target_id: 2,
            target_name: "Mercado",
            total: 1,
            total_abs: 70,
            items: [],
          }),
          onApplyBulk: async () => ({
            kind: "tag" as const,
            target_id: 2,
            target_name: "Mercado",
            preview_total: 1,
            updated: 1,
            not_found: [],
          }),
        }),
      ),
    );

    expect(html).toContain("Reprocessar classificação");
    expect(html).toContain("Prévia de aplicação em massa");
    expect(html).toContain("Tag para aplicar");
    expect(html).toContain("Sem Meta");
    expect(html).toContain("Gerar prévia");
    expect(html).toContain("Aplicar em massa");
  });

  it("renders structured classification suggestions", () => {
    const html = renderToStaticMarkup(
      createElement(
        PrivacyProvider,
        null,
        createElement(ClassificationHealthPanel, {
          data: sample,
          month: "2026-06",
          suggestions: {
            month: "2026-06",
            total: 1,
            items: [
              {
                raw_category: "Digital services",
                category_label: "Servi\u00e7os digitais",
                suggested_translation: "Servi\u00e7os digitais",
                transaction_count: 2,
                missing_tag_count: 2,
                missing_bucket_count: 2,
                total_abs: 240,
                suggested_tag: {
                  id: null,
                  name: "Servi\u00e7os digitais",
                  color: "#0ea5e9",
                  bucket_id: 1,
                  bucket_key: "prazeres",
                  bucket_name: "Prazeres",
                  source: "category",
                },
                suggested_bucket: {
                  id: 1,
                  key: "prazeres",
                  name: "Prazeres",
                  color: "#f97316",
                },
                examples: [
                  {
                    id: "tx-openai",
                    date: "2026-06-10",
                    description: "OpenAI ChatGPT",
                    account_name: "Card",
                    category: "Digital services",
                    category_label: "Servi\u00e7os digitais",
                    amount_abs: 120,
                  },
                ],
              },
            ],
          },
        }),
      ),
    );

    expect(html).toContain("Sugest\u00f5es de classifica\u00e7\u00e3o");
    expect(html).toContain("Servi\u00e7os digitais");
    expect(html).toContain("Tag sugerida");
    expect(html).toContain("Meta sugerida");
    expect(html).toContain("2 lan\u00e7amento(s)");
    expect(html).toContain("OpenAI ChatGPT");
  });

  it("renders classification rules review panel", () => {
    const html = renderToStaticMarkup(
      createElement(ClassificationRulesPanel, {
        rules: {
          tag_rules: [
            {
              kind: "tag",
              match_key: "-ifood mercado",
              target_id: 2,
              target_name: "Mercado",
              target_color: "#22c55e",
            },
          ],
          bucket_rules: [
            {
              kind: "bucket",
              match_key: "-uber viagem",
              target_id: 1,
              target_name: "Conforto",
              target_color: "#06b6d4",
            },
          ],
        },
        buckets: [{ id: 1, key: "conforto", name: "Conforto", color: "#06b6d4" }],
        tags: [{ id: 2, name: "Mercado", color: "#22c55e" }],
        onSaveRule: async () => undefined,
      }),
    );

    expect(html).toContain("Regras aprendidas");
    expect(html).toContain("-ifood mercado");
    expect(html).toContain("Mercado");
    expect(html.indexOf("Mercado")).toBeLessThan(html.indexOf("-ifood mercado"));
    expect(html).toContain("-uber viagem");
    expect(html).toContain("Conforto");
    expect(html).toContain("Remover regra");
    expect(html).not.toContain("<select");
  });

  it("renders classification audit history", () => {
    const html = renderToStaticMarkup(
      createElement(ClassificationAuditPanel, {
        data: {
          items: [
            {
              id: 3,
              action: "rule_update",
              kind: "tag",
              target_id: 2,
              target_name: "Mercado",
              match_key: "-ifood mercado",
              affected_count: 0,
              preview_total: 0,
              metadata: {},
              created_at: "2026-06-23T10:00:00",
            },
            {
              id: 2,
              action: "bulk_apply",
              kind: "bucket",
              target_id: 1,
              target_name: "Conforto",
              match_key: null,
              affected_count: 4,
              preview_total: 4,
              metadata: { month: "2026-06", not_found: [] },
              created_at: "2026-06-23T09:00:00",
            },
          ],
        },
      }),
    );

    expect(html).toContain("Auditoria de classificação");
    expect(html).toContain("Regra atualizada");
    expect(html).toContain("Aplicação em massa");
    expect(html).toContain("Mercado");
    expect(html).toContain("-ifood mercado");
    expect(html.indexOf("Mercado")).toBeLessThan(html.indexOf("-ifood mercado"));
    expect(html).toContain("4 de 4");
  });

  it("renders compact editable sections as responsive field groups", () => {
    const Component = EditableMaintenanceTable as ComponentType<Record<string, unknown>>;
    const html = renderToStaticMarkup(
      createElement(Component, {
        section: "receitas",
        title: "Receitas",
        rows: [{ membro: "Davi", valor: 5000 }],
        columns: [
          { key: "membro", label: "Membro", type: "text" },
          { key: "valor", label: "Valor", type: "number" },
        ],
        onChange: () => undefined,
      }),
    );

    expect(html).toContain('data-layout="cards"');
    expect(html).not.toContain("<table");
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
