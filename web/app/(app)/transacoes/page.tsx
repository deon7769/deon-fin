"use client";

import { useCallback, useMemo, useState, type FormEvent } from "react";
import {
  ArrowDownCircle,
  ArrowLeftRight,
  ArrowUpCircle,
  Eye,
  EyeOff,
  Filter,
  Plus,
  RefreshCw,
  Search,
  Trash2,
  Wallet,
  X,
} from "lucide-react";
import { Header } from "@/components/layout/Header";
import { TransactionAdvancedFilters } from "@/components/transacoes/TransactionAdvancedFilters";
import { BucketSelect } from "@/components/ui/BucketSelect";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { KpiCard } from "@/components/ui/KpiCard";
import { MoneyText } from "@/components/ui/MoneyText";
import { SectionCard } from "@/components/ui/SectionCard";
import { SavingsGoalSelect } from "@/components/ui/SavingsGoalSelect";
import { TagSelect } from "@/components/ui/TagSelect";
import { useBuckets } from "@/hooks/useBuckets";
import { useAccounts } from "@/hooks/useAccounts";
import { useSavingsGoals } from "@/hooks/useMetas";
import { useSetBucket } from "@/hooks/useSetBucket";
import { useSetTag } from "@/hooks/useSetTag";
import { useCreateTag } from "@/hooks/useTagMutations";
import { useTags } from "@/hooks/useTags";
import { useTransactionFilters } from "@/hooks/useTransactionFilters";
import {
  useCreateTransaction,
  useDeleteTransaction,
  useUpdateTransaction,
} from "@/hooks/useTransactionMutations";
import { useTransactions } from "@/hooks/useTransactions";
import { cn } from "@/lib/cn";
import { formatDate } from "@/lib/format";
import { tagSourceLabel } from "@/lib/tags";
import {
  parseTransactionAmountInput,
  transactionCategoryLabel,
  transactionClassificationFeedback,
  transactionDisplayValue,
  transactionFilterBadges,
} from "@/lib/transactions";
import type { Tag, Transaction, TransactionType } from "@/lib/types";

const EMPTY_TRANSACTIONS: Transaction[] = [];

function errorMessage(error: unknown): string | null {
  return error instanceof Error ? error.message : null;
}

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

function NoteCell({
  tx,
  onSave,
  saving,
}: {
  tx: Transaction;
  onSave: (note: string | null) => void;
  saving: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(tx.note ?? "");

  if (!editing) {
    return (
      <button
        type="button"
        onClick={() => setEditing(true)}
        className="mt-1 max-w-[18rem] truncate text-left text-xs text-muted transition hover:text-text"
      >
        {tx.note ? tx.note : "Adicionar observação"}
      </button>
    );
  }

  return (
    <form
      className="mt-2 flex max-w-[20rem] items-center gap-2"
      onSubmit={(event) => {
        event.preventDefault();
        onSave(value.trim() || null);
        setEditing(false);
      }}
    >
      <input
        value={value}
        onChange={(event) => setValue(event.target.value)}
        className="h-8 min-w-0 flex-1 rounded-md border border-border bg-bg px-2 text-xs text-text outline-none"
        aria-label="Observação"
      />
      <button
        type="submit"
        disabled={saving}
        className="inline-flex h-8 items-center rounded-md bg-accent px-2 text-xs font-semibold text-accentFg disabled:opacity-60"
      >
        OK
      </button>
      <button
        type="button"
        onClick={() => {
          setValue(tx.note ?? "");
          setEditing(false);
        }}
        aria-label="Cancelar observação"
        className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted hover:bg-surface2 hover:text-text"
      >
        <X size={14} aria-hidden />
      </button>
    </form>
  );
}

function ReferenceMonthCell({
  tx,
  onSave,
  saving,
}: {
  tx: Transaction;
  onSave: (month: string) => void;
  saving: boolean;
}) {
  const [value, setValue] = useState(tx.reference_month ?? "");

  return (
    <input
      type="month"
      value={value}
      disabled={saving}
      onChange={(event) => setValue(event.target.value)}
      onBlur={() => {
        if (value && value !== tx.reference_month) {
          onSave(value);
        }
      }}
      aria-label="Mês de referência"
      className="h-9 w-36 rounded-md border border-border bg-surface2 px-2 text-sm text-text outline-none disabled:opacity-60"
    />
  );
}

function NewTransactionPanel({
  open,
  defaultAccountId,
  accountOptions,
  buckets,
  tags,
  saving,
  error,
  onClose,
  onCreateTag,
  onSubmit,
}: {
  open: boolean;
  defaultAccountId?: string;
  accountOptions: Array<{ id: string; label: string }>;
  buckets: ReturnType<typeof useBuckets>["data"];
  tags: Tag[];
  saving: boolean;
  error: string | null;
  onClose: () => void;
  onCreateTag: (name: string) => Promise<Tag>;
  onSubmit: (input: {
    account_id: string;
    posted_at: string;
    amount: number;
    type: TransactionType;
    description: string;
    bucket_id: number | null;
    tag_id: number | null;
    note: string | null;
  }) => Promise<void>;
}) {
  const [accountId, setAccountId] = useState(defaultAccountId ?? "");
  const [postedAt, setPostedAt] = useState(todayISO());
  const [type, setType] = useState<TransactionType>("expense");
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("");
  const [bucketId, setBucketId] = useState<number | null>(null);
  const [tagId, setTagId] = useState<number | null>(null);
  const [note, setNote] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  if (!open) {
    return null;
  }

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const parsedAmount = parseTransactionAmountInput(amount);
    if (parsedAmount === null) {
      setFormError("Informe um valor válido.");
      return;
    }
    setFormError(null);
    await onSubmit({
      account_id: accountId.trim(),
      posted_at: postedAt,
      amount: parsedAmount,
      type,
      description,
      bucket_id: bucketId,
      tag_id: tagId,
      note: note.trim() || null,
    });
    setAmount("");
    setDescription("");
    setNote("");
  };

  return (
    <SectionCard
      title="Nova transação"
      actions={
        <button
          type="button"
          onClick={onClose}
          aria-label="Fechar"
          className="inline-flex h-9 w-9 items-center justify-center rounded-md text-muted transition hover:bg-surface2 hover:text-text"
        >
          <X size={16} aria-hidden />
        </button>
      }
    >
      <form onSubmit={submit} className="grid gap-4 lg:grid-cols-6">
        <label className="space-y-1 lg:col-span-2">
          <span className="text-xs font-medium text-muted">Conta</span>
          <input
            value={accountId}
            onChange={(event) => setAccountId(event.target.value)}
            required
            list="transaction-account-options"
            className="h-10 w-full rounded-md border border-border bg-bg px-3 text-sm text-text outline-none"
          />
          <datalist id="transaction-account-options">
            {accountOptions.map((account) => (
              <option key={account.id} value={account.id}>
                {account.label}
              </option>
            ))}
          </datalist>
        </label>
        <label className="space-y-1">
          <span className="text-xs font-medium text-muted">Data</span>
          <input
            type="date"
            value={postedAt}
            onChange={(event) => setPostedAt(event.target.value)}
            required
            className="h-10 w-full rounded-md border border-border bg-bg px-3 text-sm text-text outline-none"
          />
        </label>
        <label className="space-y-1">
          <span className="text-xs font-medium text-muted">Tipo</span>
          <select
            value={type}
            onChange={(event) => setType(event.target.value as TransactionType)}
            className="h-10 w-full rounded-md border border-border bg-bg px-3 text-sm text-text outline-none"
          >
            <option value="expense">Despesa</option>
            <option value="income">Receita</option>
          </select>
        </label>
        <label className="space-y-1">
          <span className="text-xs font-medium text-muted">Valor</span>
          <input
            value={amount}
            onChange={(event) => {
              setAmount(event.target.value);
              setFormError(null);
            }}
            required
            inputMode="decimal"
            className="h-10 w-full rounded-md border border-border bg-bg px-3 text-sm text-text outline-none"
          />
        </label>
        <label className="space-y-1 lg:col-span-3">
          <span className="text-xs font-medium text-muted">Descrição</span>
          <input
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            required
            className="h-10 w-full rounded-md border border-border bg-bg px-3 text-sm text-text outline-none"
          />
        </label>
        <div className="space-y-1">
          <span className="text-xs font-medium text-muted">Meta</span>
          <BucketSelect value={bucketId} options={buckets ?? []} onChange={setBucketId} />
        </div>
        <div className="space-y-1">
          <span className="text-xs font-medium text-muted">Tag</span>
          <TagSelect value={tagId} options={tags} onChange={setTagId} onCreate={onCreateTag} />
        </div>
        <label className="space-y-1 lg:col-span-4">
          <span className="text-xs font-medium text-muted">Observação</span>
          <input
            value={note}
            onChange={(event) => setNote(event.target.value)}
            className="h-10 w-full rounded-md border border-border bg-bg px-3 text-sm text-text outline-none"
          />
        </label>
        {formError || error ? (
          <div className="rounded-md border border-negative/40 bg-negative/10 px-3 py-2 text-sm text-negative lg:col-span-6">
            {formError ?? error}
          </div>
        ) : null}
        <div className="flex items-center justify-end gap-2 lg:col-span-6">
          <button
            type="button"
            onClick={onClose}
            className="inline-flex h-10 items-center rounded-md border border-border px-4 text-sm font-medium text-muted transition hover:bg-surface2 hover:text-text"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={saving}
            className="inline-flex h-10 items-center gap-2 rounded-md bg-accent px-4 text-sm font-semibold text-accentFg transition hover:brightness-95 disabled:opacity-60"
          >
            <Plus size={16} aria-hidden />
            <span>{saving ? "Salvando..." : "Criar"}</span>
          </button>
        </div>
      </form>
    </SectionCard>
  );
}

export default function TransacoesPage() {
  const [newOpen, setNewOpen] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const {
    filters,
    hasFilters,
    setSearch,
    applyAdvancedFilters,
    setPage,
    setPageSize,
    clearFilters,
  } = useTransactionFilters();
  const transactionsQuery = useTransactions(filters);
  const accountsQuery = useAccounts();
  const bucketsQuery = useBuckets();
  const savingsGoalsQuery = useSavingsGoals();
  const tagsQuery = useTags();
  const setBucket = useSetBucket();
  const setTag = useSetTag();
  const createTag = useCreateTag();
  const updateTx = useUpdateTransaction();
  const createTx = useCreateTransaction();
  const deleteTx = useDeleteTransaction();
  const [classificationStatus, setClassificationStatus] = useState<string | null>(null);
  const data = transactionsQuery.data;
  const rows = data?.items ?? EMPTY_TRANSACTIONS;
  const summary = data?.summary ?? { income: 0, expense: 0, balance: 0 };
  const page = filters.page ?? 1;
  const pageSize = filters.pageSize ?? 25;
  const totalPages = Math.max(1, Math.ceil((data?.total ?? 0) / pageSize));
  const from = data && data.total > 0 ? (page - 1) * pageSize + 1 : 0;
  const to = data ? Math.min(page * pageSize, data.total) : 0;
  const defaultAccountId = rows[0]?.account_id;
  const activeFilterBadges = transactionFilterBadges(filters, {
    buckets: bucketsQuery.data ?? [],
    tags: tagsQuery.data ?? [],
    savingsGoals: savingsGoalsQuery.data?.goals ?? [],
    accounts: [
      ...(accountsQuery.data?.banks ?? []).map((account) => ({
        id: account.id,
        name: account.name ?? account.institution ?? account.id,
      })),
      ...(accountsQuery.data?.cards ?? []).map((account) => ({
        id: account.id,
        name: account.name ?? account.id,
      })),
    ],
  });
  const accountOptions = useMemo(() => {
    const byId = new Map<string, string>();
    for (const account of accountsQuery.data?.banks ?? []) {
      byId.set(account.id, account.name ?? account.institution ?? account.id);
    }
    for (const account of accountsQuery.data?.cards ?? []) {
      byId.set(account.id, account.name ?? account.id);
    }
    for (const tx of rows) {
      if (!byId.has(tx.account_id)) {
        byId.set(tx.account_id, tx.account_name ?? tx.account_id);
      }
    }
    return Array.from(byId, ([id, label]) => ({ id, label }));
  }, [accountsQuery.data, rows]);

  const createInlineTag = useCallback(
    async (name: string) => createTag.mutateAsync({ name, color: null }),
    [createTag],
  );
  const setTransactionBucket = useCallback(
    async (tx: Transaction, bucketId: number | null, applyToSimilar: boolean) => {
      setClassificationStatus("Atualizando Meta...");
      try {
        const result = await setBucket.mutateAsync({ txId: tx.id, bucketId, applyToSimilar });
        setClassificationStatus(transactionClassificationFeedback("bucket", result));
      } catch (error) {
        setClassificationStatus(errorMessage(error) ?? "Falha ao atualizar Meta.");
      }
    },
    [setBucket],
  );
  const setTransactionTag = useCallback(
    async (tx: Transaction, tagId: number | null, applyToSimilar: boolean) => {
      setClassificationStatus("Atualizando Tag...");
      try {
        const result = await setTag.mutateAsync({ txId: tx.id, tagId, applyToSimilar });
        setClassificationStatus(transactionClassificationFeedback("tag", result));
      } catch (error) {
        setClassificationStatus(errorMessage(error) ?? "Falha ao atualizar Tag.");
      }
    },
    [setTag],
  );

  const columns = useMemo<DataTableColumn<Transaction>[]>(
    () => [
      {
        key: "description",
        header: "Descrição",
        className: "min-w-[260px] px-3 py-3 align-top",
        cell: (tx) => (
          <div>
            <p className="font-medium text-text">{tx.description}</p>
            <p className="mt-1 text-xs text-muted">{transactionCategoryLabel(tx)}</p>
            <NoteCell
              tx={tx}
              saving={updateTx.isPending}
              onSave={(note) => updateTx.mutate({ id: tx.id, input: { note } })}
            />
          </div>
        ),
      },
      {
        key: "value",
        header: "Valor",
        className: "min-w-[130px] px-3 py-3 text-right align-top",
        cell: (tx) => (
          <MoneyText
            value={transactionDisplayValue(tx)}
            colorBySign="auto"
            className="font-semibold"
          />
        ),
      },
      {
        key: "posted_at",
        header: "Data",
        className: "min-w-[110px] px-3 py-3 align-top",
        cell: (tx) => <span className="text-muted">{formatDate(tx.posted_at)}</span>,
      },
      {
        key: "reference_month",
        header: "Referência",
        className: "min-w-[150px] px-3 py-3 align-top",
        cell: (tx) => (
          <ReferenceMonthCell
            tx={tx}
            saving={updateTx.isPending}
            onSave={(reference_month) =>
              updateTx.mutate({ id: tx.id, input: { reference_month } })
            }
          />
        ),
      },
      {
        key: "account",
        header: "Conta",
        className: "min-w-[170px] px-3 py-3 align-top",
        cell: (tx) => (
          <div>
            <p className="text-sm text-text">{tx.account_name ?? "Conta"}</p>
            <p className="mt-1 text-xs text-muted">{tx.account_type ?? tx.account_id}</p>
          </div>
        ),
      },
      {
        key: "bucket",
        header: "Meta",
        className: "min-w-[190px] px-3 py-3 align-top",
        cell: (tx) => (
          <BucketSelect
            value={tx.bucket_id ?? null}
            options={bucketsQuery.data ?? []}
            loading={bucketsQuery.isLoading}
            disabled={setBucket.isPending}
            onChangeWithPropagation={(bucketId, applyToSimilar) =>
              void setTransactionBucket(tx, bucketId, applyToSimilar)
            }
          />
        ),
      },
      {
        key: "tag",
        header: "Tag",
        className: "min-w-[190px] px-3 py-3 align-top",
        cell: (tx) => {
          const sourceLabel = tagSourceLabel(tx.tag_source);
          return (
            <div className="space-y-1">
              <TagSelect
                value={tx.tag_id ?? null}
                options={tagsQuery.data ?? []}
                loading={tagsQuery.isLoading}
                disabled={setTag.isPending || createTag.isPending}
                onChangeWithPropagation={(tagId, applyToSimilar) =>
                  void setTransactionTag(tx, tagId, applyToSimilar)
                }
                onCreate={createInlineTag}
              />
              {sourceLabel ? (
                <p className="text-xs text-muted">{sourceLabel}</p>
              ) : null}
            </div>
          );
        },
      },
      {
        key: "savings_goal",
        header: "Meta poupança",
        className: "min-w-[210px] px-3 py-3 align-top",
        cell: (tx) => (
          <SavingsGoalSelect
            value={tx.savings_goal_id ?? null}
            options={savingsGoalsQuery.data?.goals ?? []}
            loading={savingsGoalsQuery.isLoading}
            disabled={updateTx.isPending}
            onChange={(savings_goal_id) =>
              updateTx.mutate({ id: tx.id, input: { savings_goal_id } })
            }
          />
        ),
      },
      {
        key: "hidden",
        header: "Ocultar",
        className: "w-24 px-3 py-3 text-center align-top",
        cell: (tx) => (
          <button
            type="button"
            onClick={() => updateTx.mutate({ id: tx.id, input: { hidden: !tx.hidden } })}
            aria-label={tx.hidden ? "Mostrar nos relatórios" : "Ocultar dos relatórios"}
            aria-pressed={tx.hidden}
            title={tx.hidden ? "Mostrar nos relatórios" : "Ocultar dos relatórios"}
            className={cn(
              "inline-flex h-9 w-9 items-center justify-center rounded-md border border-border transition",
              tx.hidden
                ? "bg-accent text-accentFg"
                : "bg-surface2 text-muted hover:bg-surface hover:text-text",
            )}
          >
            {tx.hidden ? <EyeOff size={16} aria-hidden /> : <Eye size={16} aria-hidden />}
          </button>
        ),
      },
      {
        key: "actions",
        header: "",
        className: "w-16 px-3 py-3 text-right align-top",
        cell: (tx) => (
          <button
            type="button"
            onClick={() => {
              if (window.confirm("Excluir esta transação?")) {
                deleteTx.mutate(tx.id);
              }
            }}
            aria-label="Excluir transação"
            title="Excluir"
            className="inline-flex h-9 w-9 items-center justify-center rounded-md text-muted transition hover:bg-surface2 hover:text-negative"
          >
            <Trash2 size={16} aria-hidden />
          </button>
        ),
      },
    ],
    [
      bucketsQuery.data,
      bucketsQuery.isLoading,
      createTag.isPending,
      createInlineTag,
      deleteTx,
      savingsGoalsQuery.data,
      savingsGoalsQuery.isLoading,
      setBucket,
      setTransactionBucket,
      setTransactionTag,
      setTag,
      tagsQuery.data,
      tagsQuery.isLoading,
      updateTx,
    ],
  );

  return (
    <>
      <Header title="Transações" />
      <div className="space-y-4 p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => transactionsQuery.refetch()}
              className="inline-flex h-10 items-center gap-2 rounded-md border border-border px-3 text-sm font-medium text-muted transition hover:bg-surface2 hover:text-text"
            >
              <RefreshCw size={16} aria-hidden className={transactionsQuery.isFetching ? "animate-spin" : ""} />
              <span>Atualizar</span>
            </button>
          </div>
          <button
            type="button"
            onClick={() => {
              createTx.reset();
              setNewOpen(true);
            }}
            className="inline-flex h-10 items-center gap-2 rounded-md bg-accent px-4 text-sm font-semibold text-accentFg transition hover:brightness-95"
          >
            <Plus size={17} aria-hidden />
            <span>Nova transação</span>
          </button>
        </div>

        <NewTransactionPanel
          key={defaultAccountId ?? "no-account"}
          open={newOpen}
          defaultAccountId={defaultAccountId}
          accountOptions={accountOptions}
          buckets={bucketsQuery.data}
          tags={tagsQuery.data ?? []}
          saving={createTx.isPending}
          error={errorMessage(createTx.error)}
          onClose={() => setNewOpen(false)}
          onCreateTag={createInlineTag}
          onSubmit={async (input) => {
            await createTx.mutateAsync(input);
            setNewOpen(false);
          }}
        />

        <div className="grid gap-4 md:grid-cols-3">
          <KpiCard
            title="Entradas"
            value={<MoneyText value={summary.income} />}
            icon={<ArrowUpCircle size={18} aria-hidden />}
            tone="positive"
          />
          <KpiCard
            title="Saídas"
            value={<MoneyText value={summary.expense} />}
            icon={<ArrowDownCircle size={18} aria-hidden />}
            tone="negative"
          />
          <KpiCard
            title="Saldo"
            value={<MoneyText value={summary.balance} colorBySign="auto" />}
            icon={<Wallet size={18} aria-hidden />}
            tone={summary.balance >= 0 ? "positive" : "negative"}
          />
        </div>

        <SectionCard>
          <div className="space-y-4">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
              <label className="flex h-10 min-w-0 items-center gap-2 rounded-md border border-border bg-bg px-3 text-muted lg:flex-1">
                <Search size={16} aria-hidden />
                <input
                  value={filters.q ?? ""}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Buscar transação"
                  className="min-w-0 flex-1 bg-transparent text-sm text-text outline-none placeholder:text-muted"
                />
              </label>
              <button
                type="button"
                onClick={() => setAdvancedOpen(true)}
                className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-border px-3 text-sm font-semibold text-text transition hover:bg-surface2"
              >
                <Filter size={15} aria-hidden />
                <span>Mais filtros</span>
              </button>
            </div>

            {activeFilterBadges.length ? (
              <div className="flex flex-wrap items-center gap-2" aria-label="Filtros ativos">
                {activeFilterBadges.map((badge) => (
                  <span
                    key={badge}
                    className="rounded-md border border-accent/40 bg-accent/10 px-2 py-1 text-xs font-medium text-text"
                  >
                    {badge}
                  </span>
                ))}
              </div>
            ) : null}
          </div>
        </SectionCard>

        {advancedOpen ? (
          <TransactionAdvancedFilters
            open={advancedOpen}
            filters={filters}
            buckets={bucketsQuery.data ?? []}
            tags={tagsQuery.data ?? []}
            accounts={accountOptions.map((account) => ({ id: account.id, name: account.label }))}
            savingsGoals={savingsGoalsQuery.data?.goals ?? []}
            onApply={applyAdvancedFilters}
            onClear={clearFilters}
            onClose={() => setAdvancedOpen(false)}
          />
        ) : null}

        <SectionCard>
          <div className="space-y-4">
            {transactionsQuery.isError ? (
              <div className="rounded-md border border-negative/40 bg-negative/10 px-4 py-3 text-sm text-negative">
                {errorMessage(transactionsQuery.error) ?? "Não foi possível carregar as transações."}
              </div>
            ) : null}

            {classificationStatus ? (
              <div className="rounded-md border border-border bg-surface2 px-4 py-3 text-sm text-muted">
                {classificationStatus}
              </div>
            ) : null}

            <DataTable
              columns={columns}
              rows={rows}
              getRowKey={(tx) => tx.id}
              loading={transactionsQuery.isLoading}
              empty={
                <EmptyState
                  icon={<ArrowLeftRight size={28} aria-hidden />}
                  title={
                    hasFilters
                      ? "Nenhuma transação para esses filtros"
                      : "Nenhuma transação neste período"
                  }
                  action={
                    hasFilters ? (
                      <button
                        type="button"
                        onClick={clearFilters}
                        className="inline-flex h-10 items-center rounded-md border border-border px-4 text-sm font-medium text-muted transition hover:bg-surface2 hover:text-text"
                      >
                        Limpar filtros
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={() => setNewOpen(true)}
                        className="inline-flex h-10 items-center gap-2 rounded-md bg-accent px-4 text-sm font-semibold text-accentFg transition hover:brightness-95"
                      >
                        <Plus size={17} aria-hidden />
                        <span>Nova transação</span>
                      </button>
                    )
                  }
                />
              }
            />

            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4 text-sm text-muted">
              <span>
                Mostrando {from}-{to} de {data?.total ?? 0}
              </span>
              <div className="flex items-center gap-2">
                <select
                  value={pageSize}
                  onChange={(event) => setPageSize(Number(event.target.value))}
                  className="h-9 rounded-md border border-border bg-bg px-2 text-sm text-text outline-none"
                  aria-label="Itens por página"
                >
                  <option value={10}>10</option>
                  <option value={25}>25</option>
                  <option value={50}>50</option>
                </select>
                <button
                  type="button"
                  disabled={page <= 1}
                  onClick={() => setPage(page - 1)}
                  className="h-9 rounded-md border border-border px-3 text-sm font-medium text-muted transition hover:bg-surface2 hover:text-text disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Anterior
                </button>
                <span className="min-w-24 text-center text-xs">
                  Página {page} de {totalPages}
                </span>
                <button
                  type="button"
                  disabled={page >= totalPages}
                  onClick={() => setPage(page + 1)}
                  className="h-9 rounded-md border border-border px-3 text-sm font-medium text-muted transition hover:bg-surface2 hover:text-text disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Próxima
                </button>
              </div>
            </div>
          </div>
        </SectionCard>
      </div>
    </>
  );
}
