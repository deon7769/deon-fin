import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { BucketBudgetCard } from "@/components/budget/BucketBudgetCard";
import type { BudgetCategory } from "@/lib/types";
import { PrivacyProvider } from "@/providers/PrivacyProvider";

const category: BudgetCategory = {
  id: 2,
  key: "metas",
  name: "Metas",
  color: "#3B82F6",
  planned_kind: "percent",
  planned_value: 10,
  planned: 1000,
  spent: 250,
  remaining: 750,
  used_pct: 25,
  exceeded: false,
  tx_count: 3,
};

describe("BucketBudgetCard", () => {
  it("links to transactions with the bucket and expense type filters visible", () => {
    const html = renderToStaticMarkup(
      <PrivacyProvider>
        <BucketBudgetCard category={category} month="2026-06" />
      </PrivacyProvider>,
    );

    expect(html).toContain(
      'href="/transacoes?month=2026-06&amp;bucket_ids=2&amp;type=expense"',
    );
  });
});
