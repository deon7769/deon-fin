import { describe, expect, it } from "vitest";

import {
  cardDetailLine,
  installmentLabel,
  invoiceCategoryLabel,
  invoiceItemCategoryLabel,
  invoiceStatusLabel,
} from "@/lib/invoices";

describe("invoice helpers", () => {
  it("formats installment labels", () => {
    expect(installmentLabel({ n: 3, of: 10 })).toBe("3/10");
    expect(installmentLabel(null)).toBe("--");
  });

  it("formats inferred status labels", () => {
    expect(invoiceStatusLabel(true)).toBe("Paga");
    expect(invoiceStatusLabel(false)).toBe("Aberta");
  });

  it("builds a compact card detail line from available metadata", () => {
    expect(cardDetailLine({ brand: "Visa", last4: "1234" })).toBe("Visa - final 1234");
    expect(cardDetailLine({ brand: null, last4: "9876" })).toBe("final 9876");
    expect(cardDetailLine({ brand: null, last4: null })).toBe("");
  });

  it("prefers translated category labels for items and summaries", () => {
    expect(invoiceItemCategoryLabel({ category: "Shopping", category_label: "Compras" })).toBe("Compras");
    expect(invoiceItemCategoryLabel({ category: "Shopping", category_label: "" })).toBe("Shopping");
    expect(invoiceCategoryLabel({ name: "Eating out", label: "Restaurantes" })).toBe("Restaurantes");
    expect(invoiceCategoryLabel({ name: "Groceries", label: " " })).toBe("Groceries");
  });
});
