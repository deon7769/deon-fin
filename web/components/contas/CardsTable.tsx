"use client";

import { CreditCard } from "lucide-react";
import { AccountActions } from "@/components/contas/AccountActions";
import { SyncStatusChip } from "@/components/contas/SyncStatusChip";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { MoneyText } from "@/components/ui/MoneyText";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { usageLabel } from "@/lib/accounts";
import type { AccountCard } from "@/lib/types";

type CardsTableProps = {
  cards: AccountCard[];
  busyAccountId?: string | null;
  onSync: (accountId: string) => void;
  onCredentials: (accountId: string) => void;
  onDelete: (accountId: string) => void;
};

export function CardsTable({
  cards,
  busyAccountId,
  onSync,
  onCredentials,
  onDelete,
}: CardsTableProps) {
  const columns: DataTableColumn<AccountCard>[] = [
    {
      key: "card",
      header: "Cartão",
      className: "min-w-[230px] px-3 py-3 align-top",
      cell: (card) => (
        <div className="min-w-0">
          <p className="truncate font-medium text-text">{card.name}</p>
          <p className="mt-1 truncate text-xs text-muted">
            {[card.brand, card.last4 ? `final ${card.last4}` : null].filter(Boolean).join(" - ") || "-"}
          </p>
        </div>
      ),
    },
    {
      key: "limit",
      header: "Limite",
      className: "min-w-[130px] px-3 py-3 text-right align-top",
      cell: (card) =>
        card.credit_limit === null ? (
          <span className="text-muted">--</span>
        ) : (
          <MoneyText value={card.credit_limit} className="font-semibold" />
        ),
    },
    {
      key: "used",
      header: "Utilizado",
      className: "min-w-[130px] px-3 py-3 text-right align-top",
      cell: (card) =>
        card.used === null ? (
          <span className="text-muted">--</span>
        ) : (
          <MoneyText value={card.used} className="font-semibold text-negative" />
        ),
    },
    {
      key: "available",
      header: "Disponível",
      className: "min-w-[130px] px-3 py-3 text-right align-top",
      cell: (card) =>
        card.available === null ? (
          <span className="text-muted">--</span>
        ) : (
          <MoneyText value={card.available} className="font-semibold" />
        ),
    },
    {
      key: "usage",
      header: "Uso",
      className: "min-w-[160px] px-3 py-3 align-top",
      cell: (card) => (
        <div className="space-y-2">
          <ProgressBar value={card.usage_pct ?? 0} />
          <p className="text-xs text-muted">{usageLabel(card.usage_pct)}</p>
        </div>
      ),
    },
    {
      key: "sync",
      header: "Sincronização",
      className: "min-w-[170px] px-3 py-3 align-top",
      cell: (card) => <SyncStatusChip status={card.sync_status} at={card.last_sync_at} />,
    },
    {
      key: "actions",
      header: "",
      className: "min-w-[140px] px-3 py-3 align-top text-right",
      cell: (card) => (
        <AccountActions
          accountId={card.id}
          canUsePluggy={Boolean(card.pluggy_item_id) && !card.manual}
          busy={busyAccountId === card.id}
          onSync={onSync}
          onCredentials={onCredentials}
          onDelete={onDelete}
        />
      ),
    },
  ];

  return (
    <DataTable
      columns={columns}
      rows={cards}
      getRowKey={(card) => card.id}
      empty={<EmptyState icon={<CreditCard size={28} aria-hidden />} title="Nenhum cartão" />}
    />
  );
}
