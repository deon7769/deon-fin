import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { BucketAllocationPanel } from "@/components/metas/BucketAllocationPanel";
import type { BucketPlanItem } from "@/lib/types";
import { PrivacyProvider } from "@/providers/PrivacyProvider";

const buckets: BucketPlanItem[] = [
  {
    id: 1,
    key: "liberdade_financeira",
    name: "Liberdade Financeira",
    color: "#6D5BD0",
    planned_kind: "percent",
    planned_value: 25,
    planned_amount: 2500,
    spent_month: 1000,
  },
  {
    id: 2,
    key: "custos_fixos",
    name: "Custos Fixos",
    color: "#1683F7",
    planned_kind: "percent",
    planned_value: 30,
    planned_amount: 3000,
    spent_month: 2800,
  },
  {
    id: 3,
    key: "prazeres",
    name: "Prazeres",
    color: "#FF7A00",
    planned_kind: "percent",
    planned_value: 10,
    planned_amount: 1000,
    spent_month: 500,
  },
];

describe("BucketAllocationPanel", () => {
  it("renders a slider allocation editor and disables save when total is not 100", () => {
    const html = renderToStaticMarkup(
      <PrivacyProvider>
        <BucketAllocationPanel
          buckets={buckets}
          income={10000}
          saving={false}
          onSave={() => undefined}
        />
      </PrivacyProvider>,
    );

    expect(html).toContain("Visualização de uso");
    expect(html).toContain("Controle de Metas");
    expect(html).toContain("type=\"range\"");
    expect(html).toContain("Total: 65%");
    expect(html).toContain("Faltam 35% para 100%");
    expect(html).toContain("Salvar metas");
    expect(html).toContain("disabled");
  });
});
