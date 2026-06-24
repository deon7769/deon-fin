import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { CardPicker } from "@/components/faturas/CardPicker";
import { PrivacyProvider } from "@/providers/PrivacyProvider";
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

describe("CardPicker", () => {
  const cards = [
    {
      id: "card-a",
      name: "Cartao A",
      brand: "Visa",
      last4: "1111",
      credit_limit: 1000,
      available: 750,
      currency: "BRL",
    },
    {
      id: "card-b",
      name: "Cartao B",
      brand: "Mastercard",
      last4: "2222",
      credit_limit: 2000,
      available: 1500,
      currency: "BRL",
    },
  ];

  it("renders controls to reorder invoice cards", () => {
    const html = renderToStaticMarkup(
      createElement(
        PrivacyProvider,
        null,
        createElement(CardPicker, {
          cards,
          value: "card-a",
          onChange: vi.fn(),
          orderMode: true,
          savingOrder: false,
          onMove: vi.fn(),
          onSaveOrder: vi.fn(),
          onCancelOrder: vi.fn(),
        }),
      ),
    );

    expect(html).toContain("Salvar ordem");
    expect(html).toContain("Use as setas para reposicionar os cart");
    expect(html).toContain("Mover Cartao A para a direita");
    expect(html).toContain("Mover Cartao B para a esquerda");
  });
});
