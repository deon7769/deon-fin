"use client";

import { Landmark } from "lucide-react";
import { AccountActions } from "@/components/contas/AccountActions";
import { SyncStatusChip } from "@/components/contas/SyncStatusChip";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { MoneyText } from "@/components/ui/MoneyText";
import { bankAccountLine } from "@/lib/accounts";
import type { AccountBank } from "@/lib/types";

type AccountsTableProps = {
  banks: AccountBank[];
  busyAccountId?: string | null;
  onSync: (accountId: string) => void;
  onCredentials: (accountId: string) => void;
  onDelete: (accountId: string) => void;
};

export function AccountsTable({
  banks,
  busyAccountId,
  onSync,
  onCredentials,
  onDelete,
}: AccountsTableProps) {
  const columns: DataTableColumn<AccountBank>[] = [
    {
      key: "bank",
      header: "Banco",
      className: "min-w-[220px] px-3 py-3 align-top",
      cell: (bank) => (
        <div className="min-w-0">
          <p className="truncate font-medium text-text">{bank.name}</p>
          <p className="mt-1 truncate text-xs text-muted">{bank.institution ?? bank.connector_name ?? "-"}</p>
        </div>
      ),
    },
    {
      key: "type",
      header: "Tipo",
      className: "min-w-[150px] px-3 py-3 align-top text-muted",
      cell: (bank) => bank.type,
    },
    {
      key: "account",
      header: "Agência / Conta",
      className: "min-w-[170px] px-3 py-3 align-top text-muted",
      cell: (bank) => bankAccountLine(bank.agency, bank.number),
    },
    {
      key: "balance",
      header: "Saldo",
      className: "min-w-[130px] px-3 py-3 text-right align-top",
      cell: (bank) => <MoneyText value={bank.balance} colorBySign className="font-semibold" />,
    },
    {
      key: "sync",
      header: "Sincronização",
      className: "min-w-[170px] px-3 py-3 align-top",
      cell: (bank) => <SyncStatusChip status={bank.sync_status} at={bank.last_sync_at} />,
    },
    {
      key: "actions",
      header: "",
      className: "min-w-[140px] px-3 py-3 align-top text-right",
      cell: (bank) => (
        <AccountActions
          accountId={bank.id}
          canUsePluggy={Boolean(bank.pluggy_item_id) && !bank.manual}
          busy={busyAccountId === bank.id}
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
      rows={banks}
      getRowKey={(bank) => bank.id}
      empty={<EmptyState icon={<Landmark size={28} aria-hidden />} title="Nenhuma conta bancária" />}
    />
  );
}
