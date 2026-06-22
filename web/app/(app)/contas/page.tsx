"use client";

import { useState } from "react";
import { AlertCircle, ArrowDown, ArrowUp, CreditCard, Landmark, List, SquareStack } from "lucide-react";
import { AccountCardGrid } from "@/components/contas/AccountCardGrid";
import { AccountsTable } from "@/components/contas/AccountsTable";
import { CardsTable } from "@/components/contas/CardsTable";
import { ConnectAccountButton } from "@/components/contas/ConnectAccountButton";
import { Header } from "@/components/layout/Header";
import { EmptyState } from "@/components/ui/EmptyState";
import { KpiCard } from "@/components/ui/KpiCard";
import { MoneyText } from "@/components/ui/MoneyText";
import { SectionCard } from "@/components/ui/SectionCard";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  useAccountCredentials,
  useAccounts,
  useDeleteAccount,
  useReorderAccounts,
  useSyncAccount,
} from "@/hooks/useAccounts";
import { openPluggyConnect } from "@/lib/pluggyConnect";

type ViewMode = "list" | "cards";

type SortableAccount = {
  id: string;
  name: string;
  detail: string;
};

function RetryState({
  error,
  onRetry,
}: {
  error: unknown;
  onRetry: () => void;
}) {
  return (
    <SectionCard>
      <EmptyState
        icon={<AlertCircle size={28} aria-hidden />}
        title="Não foi possível carregar as contas"
        description={error instanceof Error ? error.message : undefined}
        action={
          <button
            type="button"
            onClick={onRetry}
            className="h-9 rounded-md border border-border px-3 text-sm font-medium text-text transition hover:bg-surface2"
          >
            Tentar novamente
          </button>
        }
      />
    </SectionCard>
  );
}

function moveItem(items: string[], from: number, to: number): string[] {
  if (to < 0 || to >= items.length) {
    return items;
  }
  const next = [...items];
  const [item] = next.splice(from, 1);
  next.splice(to, 0, item);
  return next;
}

export default function ContasPage() {
  const [viewMode, setViewMode] = useState<ViewMode>("list");
  const [orderMode, setOrderMode] = useState(false);
  const [draftOrder, setDraftOrder] = useState<string[]>([]);
  const [connecting, setConnecting] = useState(false);
  const [connectMessage, setConnectMessage] = useState<string | null>(null);
  const [connectError, setConnectError] = useState<string | null>(null);
  const accounts = useAccounts();
  const syncAccount = useSyncAccount();
  const credentials = useAccountCredentials();
  const deleteAccount = useDeleteAccount();
  const reorder = useReorderAccounts();
  const data = accounts.data;
  const banks = data?.banks ?? [];
  const cards = data?.cards ?? [];
  const totalCount = banks.length + cards.length;

  const sortableAccounts: SortableAccount[] = [
    ...banks.map((bank) => ({
      id: bank.id,
      name: bank.name,
      detail: bank.institution ?? bank.connector_name ?? "Conta bancária",
    })),
    ...cards.map((card) => ({
      id: card.id,
      name: card.name,
      detail: [card.brand, card.last4 ? `final ${card.last4}` : null].filter(Boolean).join(" - ") || "Cartão",
    })),
  ];

  const busyAccountId =
    (syncAccount.isPending ? syncAccount.variables?.accountId : null) ??
    (credentials.isPending ? credentials.variables : null) ??
    (deleteAccount.isPending ? deleteAccount.variables : null);

  const handleCredentials = (accountId: string) => {
    credentials.mutate(accountId, {
      onSuccess: (response) => {
        if (typeof navigator !== "undefined" && navigator.clipboard) {
          void navigator.clipboard.writeText(response.accessToken);
        }
        window.alert("Token de atualização gerado.");
      },
    });
  };

  const handleDelete = (accountId: string) => {
    const confirmed = window.confirm(
      "Remover esta conexão? As transações já importadas serão mantidas.",
    );
    if (confirmed) {
      deleteAccount.mutate(accountId);
    }
  };

  const handleConnectAccount = async () => {
    setConnecting(true);
    setConnectError(null);
    setConnectMessage("Abrindo hub de conexões...");
    try {
      const result = await openPluggyConnect();
      if (result.status === "connected") {
        setConnectMessage("Conexão registrada. A sincronização foi agendada.");
        await accounts.refetch();
      } else {
        setConnectMessage("Hub fechado sem nova conexão.");
      }
    } catch (error) {
      setConnectMessage(null);
      setConnectError(error instanceof Error ? error.message : "Não foi possível abrir o hub de conexões.");
    } finally {
      setConnecting(false);
    }
  };

  const saveOrder = () => {
    reorder.mutate(draftOrder, {
      onSuccess: () => setOrderMode(false),
    });
  };

  const toggleOrderMode = () => {
    if (orderMode) {
      setOrderMode(false);
      setDraftOrder([]);
      return;
    }
    setDraftOrder(sortableAccounts.map((account) => account.id));
    setOrderMode(true);
  };

  return (
    <>
      <Header title="Contas" subtitle="Gerencie contas bancárias, cartões e sincronização." />

      <div className="space-y-5 p-4 sm:p-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="inline-flex w-fit rounded-md border border-border bg-surface p-1">
            <button
              type="button"
              onClick={() => setViewMode("list")}
              className={`inline-flex h-9 items-center gap-2 rounded px-3 text-sm transition ${
                viewMode === "list" ? "bg-accent text-black" : "text-muted hover:text-text"
              }`}
            >
              <List size={16} aria-hidden />
              Lista
            </button>
            <button
              type="button"
              onClick={() => setViewMode("cards")}
              className={`inline-flex h-9 items-center gap-2 rounded px-3 text-sm transition ${
                viewMode === "cards" ? "bg-accent text-black" : "text-muted hover:text-text"
              }`}
            >
              <SquareStack size={16} aria-hidden />
              Cards
            </button>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={!totalCount}
              onClick={toggleOrderMode}
              className="h-10 rounded-md border border-border bg-surface px-3 text-sm font-medium text-text transition hover:bg-surface2 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Ordenar contas
            </button>
            <ConnectAccountButton loading={connecting} onClick={handleConnectAccount} />
          </div>
        </div>
        {connectMessage || connectError ? (
          <div
            className={`rounded-md border px-3 py-2 text-sm ${
              connectError
                ? "border-negative/40 bg-negative/10 text-negative"
                : "border-accent/40 bg-accent/10 text-text"
            }`}
          >
            {connectError ?? connectMessage}
          </div>
        ) : null}

        {accounts.isError ? (
          <RetryState error={accounts.error} onRetry={() => void accounts.refetch()} />
        ) : (
          <>
            <div className="grid gap-4 md:grid-cols-3">
              {accounts.isLoading || !data ? (
                <>
                  <KpiCard title="Saldo em contas" value={<Skeleton className="h-8 w-32" />} />
                  <KpiCard title="Dívidas em cartões" value={<Skeleton className="h-8 w-32" />} />
                  <KpiCard title="Resultado do período" value={<Skeleton className="h-8 w-32" />} />
                </>
              ) : (
                <>
                  <KpiCard
                    title="Saldo em contas"
                    value={<MoneyText value={data.totals.accounts_balance} />}
                    subtitle={`${banks.length} conta(s) bancária(s)`}
                    icon={<Landmark size={18} aria-hidden />}
                  />
                  <KpiCard
                    title="Dívidas em cartões"
                    value={<MoneyText value={data.totals.card_debt} />}
                    subtitle={`${cards.length} cartão(ões)`}
                    tone={data.totals.card_debt > 0 ? "negative" : "default"}
                    icon={<CreditCard size={18} aria-hidden />}
                  />
                  <KpiCard
                    title="Resultado do período"
                    value={<MoneyText value={data.totals.period_result} />}
                    subtitle={data.sync.running ? "Sincronizando..." : data.sync.last_result ?? "Competência atual"}
                    tone={data.totals.period_result < 0 ? "negative" : "positive"}
                  />
                </>
              )}
            </div>

            {accounts.isLoading || !data ? (
              <SectionCard>
                <Skeleton className="h-72 w-full" />
              </SectionCard>
            ) : !totalCount ? (
              <SectionCard>
                <EmptyState
                  icon={<Landmark size={28} aria-hidden />}
                  title="Nenhuma conta conectada"
                  action={
                    <ConnectAccountButton loading={connecting} onClick={handleConnectAccount} />
                  }
                />
              </SectionCard>
            ) : (
              <>
                {orderMode ? (
                  <SectionCard
                    title="Ordenar contas"
                    actions={
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => {
                            setOrderMode(false);
                            setDraftOrder([]);
                          }}
                          className="h-9 rounded-md border border-border px-3 text-sm font-medium text-text transition hover:bg-surface2"
                        >
                          Cancelar
                        </button>
                        <button
                          type="button"
                          disabled={reorder.isPending}
                          onClick={saveOrder}
                          className="h-9 rounded-md bg-accent px-3 text-sm font-semibold text-black transition hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          Salvar ordem
                        </button>
                      </div>
                    }
                  >
                    <div className="space-y-2">
                      {draftOrder.map((accountId, index) => {
                        const account = sortableAccounts.find((item) => item.id === accountId);
                        if (!account) {
                          return null;
                        }
                        return (
                          <div
                            key={account.id}
                            className="flex items-center justify-between gap-3 rounded-md border border-border bg-surface2 px-3 py-2"
                          >
                            <div className="min-w-0">
                              <p className="truncate text-sm font-medium text-text">{account.name}</p>
                              <p className="truncate text-xs text-muted">{account.detail}</p>
                            </div>
                            <div className="flex gap-2">
                              <button
                                type="button"
                                aria-label="Mover para cima"
                                title="Mover para cima"
                                disabled={index === 0}
                                onClick={() => setDraftOrder((current) => moveItem(current, index, index - 1))}
                                className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-border text-muted transition hover:bg-surface hover:text-text disabled:cursor-not-allowed disabled:opacity-40"
                              >
                                <ArrowUp size={15} aria-hidden />
                              </button>
                              <button
                                type="button"
                                aria-label="Mover para baixo"
                                title="Mover para baixo"
                                disabled={index === draftOrder.length - 1}
                                onClick={() => setDraftOrder((current) => moveItem(current, index, index + 1))}
                                className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-border text-muted transition hover:bg-surface hover:text-text disabled:cursor-not-allowed disabled:opacity-40"
                              >
                                <ArrowDown size={15} aria-hidden />
                              </button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </SectionCard>
                ) : null}

                {viewMode === "cards" ? (
                  <SectionCard title="Contas e cartões">
                    <AccountCardGrid
                      banks={banks}
                      cards={cards}
                      busyAccountId={busyAccountId}
                      onSync={(accountId) => syncAccount.mutate({ accountId })}
                      onCredentials={handleCredentials}
                      onDelete={handleDelete}
                    />
                  </SectionCard>
                ) : (
                  <>
                    <SectionCard title={`Contas Bancárias (${banks.length})`}>
                      <AccountsTable
                        banks={banks}
                        busyAccountId={busyAccountId}
                        onSync={(accountId) => syncAccount.mutate({ accountId })}
                        onCredentials={handleCredentials}
                        onDelete={handleDelete}
                      />
                    </SectionCard>

                    <SectionCard title={`Cartões (${cards.length})`}>
                      <CardsTable
                        cards={cards}
                        busyAccountId={busyAccountId}
                        onSync={(accountId) => syncAccount.mutate({ accountId })}
                        onCredentials={handleCredentials}
                        onDelete={handleDelete}
                      />
                    </SectionCard>
                  </>
                )}
              </>
            )}
          </>
        )}
      </div>
    </>
  );
}
