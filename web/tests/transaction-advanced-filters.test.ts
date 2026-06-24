import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { TransactionAdvancedFilters } from "@/components/transacoes/TransactionAdvancedFilters";

describe("TransactionAdvancedFilters", () => {
  it("renders the advanced filters available in the reference screenshots", () => {
    const html = renderToStaticMarkup(
      createElement(TransactionAdvancedFilters, {
        open: true,
        filters: { month: "2026-06", hidden: "exclude" },
        buckets: [
          { id: 1, key: "freedom", name: "Liberdade Financeira", color: "#6d5bd0" },
          { id: 2, key: "fixed", name: "Custos Fixos", color: "#1982f5" },
        ],
        tags: [{ id: 3, name: "Mercado", color: "#34d399" }],
        accounts: [{ id: "acc-1", name: "Banco Inter" }],
        savingsGoals: [],
        onApply: vi.fn(),
        onClear: vi.fn(),
        onClose: vi.fn(),
      }),
    );

    expect(html).toContain("Filtros Avançados");
    expect(html).toContain("Período");
    expect(html).toContain("Mês de referência");
    expect(html).toContain("Faixa de Valor");
    expect(html).toContain("Tipo de Transação");
    expect(html).toContain("Metas");
    expect(html).toContain("Tags");
    expect(html).toContain("Contas");
    expect(html).toContain("Ocultar dos Relatórios");
    expect(html).toContain("Transf. de Mesma Titularidade");
    expect(html).toContain("Origem da Meta");
    expect(html).toContain("Origem da Tag");
    expect(html).toContain("Aplicar Filtros");
  });

  it("renders multivalue filters as searchable chip controls instead of native multiselects", () => {
    const html = renderToStaticMarkup(
      createElement(TransactionAdvancedFilters, {
        open: true,
        filters: {
          month: "2026-06",
          hidden: "exclude",
          tagIds: [3],
          accountIds: ["acc-1"],
          bucketSources: ["manual"],
          tagSources: ["auto"],
          savingsGoalIds: [8],
        },
        buckets: [],
        tags: [{ id: 3, name: "Mercado", color: "#34d399" }],
        accounts: [{ id: "acc-1", name: "Banco Inter" }],
        savingsGoals: [{ id: 8, name: "Reserva" }],
        onApply: vi.fn(),
        onClear: vi.fn(),
        onClose: vi.fn(),
      }),
    );

    expect(html).not.toContain("multiple");
    expect(html).toContain("Remover filtro Tag Mercado");
    expect(html).toContain("Remover filtro Conta Banco Inter");
    expect(html).toContain("Remover filtro Origem da Meta Manual");
    expect(html).toContain("Remover filtro Origem da Tag Autom");
    expect(html).toContain("Remover filtro Meta poup");
    expect(html).toContain("Buscar em Tags");
    expect(html).toContain("Buscar em Contas");
  });

  it("renders range period as start and end dates without a competing month input", () => {
    const html = renderToStaticMarkup(
      createElement(TransactionAdvancedFilters, {
        open: true,
        filters: {
          range: { from: "2026-06-01", to: "2026-06-30" },
          hidden: "exclude",
        },
        buckets: [],
        tags: [],
        accounts: [],
        savingsGoals: [],
        onApply: vi.fn(),
        onClear: vi.fn(),
        onClose: vi.fn(),
      }),
    );

    expect(html).toContain("Data inicial");
    expect(html).toContain("Data final");
    expect(html).toContain('value="2026-06-01"');
    expect(html).toContain('value="2026-06-30"');
    expect(html).not.toContain('type="month"');
  });
});
