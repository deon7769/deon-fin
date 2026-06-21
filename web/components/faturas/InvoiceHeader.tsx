"use client";

import { CalendarDays, ReceiptText } from "lucide-react";
import { MoneyText } from "@/components/ui/MoneyText";
import { Pill } from "@/components/ui/Pill";
import { SectionCard } from "@/components/ui/SectionCard";
import { formatDate } from "@/lib/format";
import { invoiceStatusLabel } from "@/lib/invoices";
import type { Invoice } from "@/lib/types";

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted">{label}</p>
      <p className="mt-1 text-sm font-medium text-text">{value}</p>
    </div>
  );
}

export function InvoiceHeader({ invoice }: { invoice: Invoice }) {
  return (
    <SectionCard title={invoice.account_name}>
      <div className="flex flex-wrap items-end gap-5">
        <div className="min-w-52">
          <p className="text-sm text-muted">Total da fatura</p>
          <div className="mt-1 text-2xl font-semibold text-negative">
            <MoneyText value={invoice.total} />
          </div>
        </div>
        <Field label="Fechamento" value={formatDate(invoice.closing_date)} />
        <Field label="Vencimento" value={formatDate(invoice.due_date)} />
        <Pill className={invoice.paid ? "text-positive" : "text-accent"}>
          <ReceiptText size={14} aria-hidden />
          {invoiceStatusLabel(invoice.paid)}
        </Pill>
        {invoice.approximate_dates ? (
          <Pill>
            <CalendarDays size={14} aria-hidden />
            Datas estimadas
          </Pill>
        ) : null}
        <span className="text-sm text-muted">{invoice.count} lançamentos</span>
      </div>
    </SectionCard>
  );
}
