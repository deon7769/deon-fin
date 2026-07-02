import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { FilterMultiSelect } from "@/components/ui/FilterMultiSelect";

describe("FilterMultiSelect", () => {
  it("keeps URL-selected values visible and removable while options are still missing", () => {
    const html = renderToStaticMarkup(
      createElement(FilterMultiSelect<string>, {
        label: "Conta",
        values: ["acc-missing"],
        options: [],
        onChange: vi.fn(),
        placeholder: "Buscar em Contas",
      }),
    );

    expect(html).toContain("1 selecionado");
    expect(html).toContain("Conta: acc-missing");
    expect(html).toContain("Remover filtro Conta acc-missing");
  });
});
