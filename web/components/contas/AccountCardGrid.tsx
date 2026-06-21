"use client";

import { CreditCard, Landmark } from "lucide-react";
import { AccountActions } from "@/components/contas/AccountActions";
import { SyncStatusChip } from "@/components/contas/SyncStatusChip";
import { MoneyText } from "@/components/ui/MoneyText";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { bankAccountLine, usageLabel } from "@/lib/accounts";
import type { AccountBank, AccountCard } from "@/lib/types";

type AccountCardGridProps = {
  banks: AccountBank[];
  cards: AccountCard[];
  busyAccountId?: string | null;
  onSync: (accountId: string) => void;
  onCredentials: (accountId: string) => void;
  onDelete: (accountId: string) => void;
};

export function AccountCardGrid({
  banks,
  cards,
  busyAccountId,
  onSync,
  onCredentials,
  onDelete,
}: AccountCardGridProps) {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {banks.map((bank) => (
        <article key={bank.id} className="min-h-[220px] rounded-card border border-border bg-surface2 p-4">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="truncate text-sm text-muted">{bank.type}</p>
              <h3 className="mt-1 truncate text-base font-semibold text-text">{bank.name}</h3>
            </div>
            <div className="rounded-md bg-surface p-2 text-muted">
              <Landmark size={18} aria-hidden />
            </div>
          </div>
          <p className="mt-3 text-sm text-muted">{bankAccountLine(bank.agency, bank.number)}</p>
          <div className="mt-5">
            <p className="text-xs text-muted">Saldo</p>
            <p className="mt-1 text-2xl font-semibold">
              <MoneyText value={bank.balance} colorBySign />
            </p>
          </div>
          <div className="mt-4 flex items-end justify-between gap-3">
            <SyncStatusChip status={bank.sync_status} at={bank.last_sync_at} />
            <AccountActions
              accountId={bank.id}
              canUsePluggy={Boolean(bank.pluggy_item_id) && !bank.manual}
              busy={busyAccountId === bank.id}
              onSync={onSync}
              onCredentials={onCredentials}
              onDelete={onDelete}
            />
          </div>
        </article>
      ))}

      {cards.map((card) => (
        <article key={card.id} className="min-h-[220px] rounded-card border border-border bg-surface2 p-4">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="truncate text-sm text-muted">
                {[card.brand, card.last4 ? `final ${card.last4}` : null].filter(Boolean).join(" - ") || "Cartão"}
              </p>
              <h3 className="mt-1 truncate text-base font-semibold text-text">{card.name}</h3>
            </div>
            <div className="rounded-md bg-surface p-2 text-muted">
              <CreditCard size={18} aria-hidden />
            </div>
          </div>
          <div className="mt-5 grid grid-cols-2 gap-3">
            <div>
              <p className="text-xs text-muted">Utilizado</p>
              <p className="mt-1 font-semibold text-negative">
                {card.used === null ? "--" : <MoneyText value={card.used} />}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted">Disponível</p>
              <p className="mt-1 font-semibold">
                {card.available === null ? "--" : <MoneyText value={card.available} />}
              </p>
            </div>
          </div>
          <div className="mt-4 space-y-2">
            <ProgressBar value={card.usage_pct ?? 0} />
            <p className="text-xs text-muted">{usageLabel(card.usage_pct)}</p>
          </div>
          <div className="mt-4 flex items-end justify-between gap-3">
            <SyncStatusChip status={card.sync_status} at={card.last_sync_at} />
            <AccountActions
              accountId={card.id}
              canUsePluggy={Boolean(card.pluggy_item_id) && !card.manual}
              busy={busyAccountId === card.id}
              onSync={onSync}
              onCredentials={onCredentials}
              onDelete={onDelete}
            />
          </div>
        </article>
      ))}
    </div>
  );
}
