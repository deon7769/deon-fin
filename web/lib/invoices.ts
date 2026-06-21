import type { InvoiceInstallment } from "./types";

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
