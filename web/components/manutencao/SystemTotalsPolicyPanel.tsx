"use client";

import { Save } from "lucide-react";
import { useMemo, useState } from "react";
import { SectionCard } from "@/components/ui/SectionCard";
import { Skeleton } from "@/components/ui/Skeleton";
import type {
  MaintenanceSystemTotalsPayload,
  MaintenanceSystemTotalsResponse,
} from "@/lib/types";

type Props = {
  data?: MaintenanceSystemTotalsResponse;
  loading?: boolean;
  saving?: boolean;
  error?: unknown;
  onSave: (payload: MaintenanceSystemTotalsPayload) => Promise<void>;
};

type AccountDraft = MaintenanceSystemTotalsResponse["accounts"][number];
type MovementDraft = MaintenanceSystemTotalsResponse["movements"][number];
type Draft = {
  sourceKey: string;
  savedKey: string;
  accounts: AccountDraft[];
  movements: MovementDraft[];
};

function accountDetail(account: AccountDraft): string {
  return [account.institution, account.type, account.source].filter(Boolean).join(" - ");
}

function policyKey(accounts: AccountDraft[], movements: MovementDraft[]): string {
  return JSON.stringify({
    accounts: accounts.map(({ id, include_balance, include_transactions }) => ({
      id,
      include_balance,
      include_transactions,
    })),
    movements: movements.map(({ key, include_in_totals }) => ({ key, include_in_totals })),
  });
}

export function SystemTotalsPolicyPanel({ data, loading, saving, error, onSave }: Props) {
  const sourceKey = useMemo(
    () => policyKey(data?.accounts ?? [], data?.movements ?? []),
    [data],
  );
  const [draft, setDraft] = useState<Draft>({
    sourceKey: "",
    savedKey: "",
    accounts: [],
    movements: [],
  });
  const [status, setStatus] = useState<string | null>(null);
  const currentDraft =
    draft.sourceKey === sourceKey
      ? draft
      : {
          sourceKey,
          savedKey: sourceKey,
          accounts: data?.accounts ?? [],
          movements: data?.movements ?? [],
        };
  const accounts = currentDraft.accounts;
  const movements = currentDraft.movements;
  const currentKey = policyKey(accounts, movements);

  const changed = Boolean(data) && currentKey !== currentDraft.savedKey;

  const updateAccount = (
    id: string,
    field: "include_balance" | "include_transactions",
    value: boolean,
  ) => {
    setDraft((current) => {
      const base = current.sourceKey === sourceKey ? current : currentDraft;
      return {
        ...base,
        accounts: base.accounts.map((account) =>
          account.id === id ? { ...account, [field]: value } : account,
        ),
      };
    });
  };

  const updateMovement = (key: string, value: boolean) => {
    setDraft((current) => {
      const base = current.sourceKey === sourceKey ? current : currentDraft;
      return {
        ...base,
        movements: base.movements.map((movement) =>
          movement.key === key ? { ...movement, include_in_totals: value } : movement,
        ),
      };
    });
  };

  const save = async () => {
    setStatus("Salvando...");
    try {
      await onSave({
        accounts: accounts.map((account) => ({
          account_id: account.id,
          include_balance: account.include_balance,
          include_transactions: account.include_transactions,
        })),
        movements: movements.map((movement) => ({
          movement_type: movement.key,
          include_in_totals: movement.include_in_totals,
        })),
      });
      setDraft({ sourceKey, savedKey: currentKey, accounts, movements });
      setStatus("Politica salva.");
    } catch (saveError) {
      setStatus(saveError instanceof Error ? saveError.message : "Falha ao salvar politica.");
    }
  };

  return (
    <SectionCard
      title="Somatorias do sistema"
      subtitle="Contas e movimentos que entram nos totais financeiros."
      actions={
        <button
          type="button"
          onClick={() => void save()}
          disabled={!changed || saving || loading}
          className="inline-flex h-9 items-center gap-2 rounded-md bg-accent px-3 text-sm font-semibold text-accentFg transition hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <Save size={15} aria-hidden />
          {saving ? "Salvando..." : "Salvar politica"}
        </button>
      }
    >
      {loading ? (
        <Skeleton className="h-56 w-full" />
      ) : error ? (
        <p className="rounded-md border border-negative/40 bg-negative/10 px-3 py-2 text-sm text-negative">
          {error instanceof Error ? error.message : "Nao foi possivel carregar a politica."}
        </p>
      ) : (
        <div className="grid gap-5 xl:grid-cols-[minmax(0,1.4fr)_minmax(320px,0.8fr)]">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[560px] text-left text-sm">
              <thead className="text-xs uppercase text-muted">
                <tr className="border-b border-border">
                  <th className="pb-2 pr-3 font-semibold">Conta</th>
                  <th className="w-28 pb-2 pr-3 text-center font-semibold">Saldo</th>
                  <th className="w-32 pb-2 text-center font-semibold">Transacoes</th>
                </tr>
              </thead>
              <tbody>
                {accounts.map((account) => (
                  <tr key={account.id} className="border-b border-border last:border-b-0">
                    <td className="py-3 pr-3">
                      <p className="font-medium text-text">{account.name}</p>
                      <p className="mt-0.5 text-xs text-muted">{accountDetail(account)}</p>
                    </td>
                    <td className="py-3 pr-3 text-center">
                      <input
                        type="checkbox"
                        checked={account.include_balance}
                        onChange={(event) =>
                          updateAccount(account.id, "include_balance", event.currentTarget.checked)
                        }
                        className="h-4 w-4 accent-accent"
                        aria-label={`${account.name}: saldo nos totais`}
                      />
                    </td>
                    <td className="py-3 text-center">
                      <input
                        type="checkbox"
                        checked={account.include_transactions}
                        onChange={(event) =>
                          updateAccount(
                            account.id,
                            "include_transactions",
                            event.currentTarget.checked,
                          )
                        }
                        className="h-4 w-4 accent-accent"
                        aria-label={`${account.name}: transacoes nos totais`}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="rounded-md border border-border bg-surface2">
            <div className="border-b border-border px-3 py-2">
              <h3 className="text-sm font-semibold text-text">Movimentos</h3>
            </div>
            <div className="divide-y divide-border">
              {movements.map((movement) => (
                <label
                  key={movement.key}
                  className="flex items-center justify-between gap-3 px-3 py-2 text-sm"
                >
                  <span className="text-text">{movement.label}</span>
                  <input
                    type="checkbox"
                    checked={movement.include_in_totals}
                    onChange={(event) => updateMovement(movement.key, event.currentTarget.checked)}
                    className="h-4 w-4 accent-accent"
                    aria-label={`${movement.label}: entrar nos totais`}
                  />
                </label>
              ))}
            </div>
          </div>
        </div>
      )}
      {status ? (
        <p className="mt-4 rounded-md border border-border bg-surface2 px-3 py-2 text-sm text-muted">
          {status}
        </p>
      ) : null}
    </SectionCard>
  );
}
