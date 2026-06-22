import type { InvoiceCategory, InvoiceInstallment, InvoiceItem } from "./types";

export function installmentLabel(installment: InvoiceInstallment | null): string {
  return installment ? `${installment.n}/${installment.of}` : "--";
}

export function invoiceStatusLabel(paid: boolean): string {
  return paid ? "Paga" : "Aberta";
}

export function cardDetailLine(card: { brand?: string | null; last4?: string | null }): string {
  const parts = [];
  if (card.brand) {
    parts.push(card.brand);
  }
  if (card.last4) {
    parts.push(`final ${card.last4}`);
  }
  return parts.join(" - ");
}

export function invoiceItemCategoryLabel(
  item: Pick<InvoiceItem, "category" | "category_label">,
): string {
  return item.category_label?.trim() || item.category.trim() || "Sem categoria";
}

export function invoiceCategoryLabel(category: Pick<InvoiceCategory, "name" | "label">): string {
  return category.label?.trim() || category.name.trim() || "Sem categoria";
}
