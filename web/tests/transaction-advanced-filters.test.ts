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
    expect(html).toContain("Aplicar Filtros");
  });
});
