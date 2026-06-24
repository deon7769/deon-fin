"use client";

import { useMemo, useState, type ReactNode } from "react";
import { Filter, X } from "lucide-react";
import { FilterMultiSelect, type FilterMultiSelectOption } from "@/components/ui/FilterMultiSelect";
import { cn } from "@/lib/cn";
import type {
  TransactionAdvancedFilterPatch,
  TransactionClassificationSourceFilter,
  TransactionFilters,
  TransactionInternalTransferFilter,
  TransactionQualityFilter,
} from "@/lib/transactions";
import type { Bucket, Tag, TransactionHiddenFilter, TransactionType } from "@/lib/types";

type AccountFilterOption = {
  id: string;
  name: string;
};

type SavingsGoalFilterOption = {
  id: number;
  name: string;
};

type DraftState = {
  periodMode: "month" | "range";
  month: string;
  rangeFrom: string;
  rangeTo: string;
  amountMin: string;
  amountMax: string;
  type: TransactionType | "";
  hidden: TransactionHiddenFilter;
  bucketIds: Array<number | null>;
  tagIds: Array<number | null>;
  bucketSources: TransactionClassificationSourceFilter[];
  tagSources: TransactionClassificationSourceFilter[];
  accountIds: string[];
  savingsGoalIds: Array<number | null>;
  quality: TransactionQualityFilter | "";
  internalTransfer: TransactionInternalTransferFilter | "";
};

type TransactionAdvancedFiltersProps = {
  open: boolean;
  filters: TransactionFilters;
  buckets: Bucket[];
  tags: Tag[];
  accounts: AccountFilterOption[];
  savingsGoals: SavingsGoalFilterOption[];
  onApply: (patch: TransactionAdvancedFilterPatch) => void;
  onClear: () => void;
  onClose: () => void;
};

function draftFromFilters(filters: TransactionFilters): DraftState {
  return {
    periodMode: filters.range ? "range" : "month",
    month: filters.month ?? "",
    rangeFrom: filters.range?.from ?? "",
    rangeTo: filters.range?.to ?? "",
    amountMin: filters.amountMin === null || filters.amountMin === undefined ? "" : String(filters.amountMin),
    amountMax: filters.amountMax === null || filters.amountMax === undefined ? "" : String(filters.amountMax),
    type: filters.type ?? "",
    hidden: filters.hidden ?? "exclude",
    bucketIds: filters.bucketIds ?? [],
    tagIds: filters.tagIds ?? [],
    bucketSources: [...(filters.bucketSources ?? [])],
    tagSources: [...(filters.tagSources ?? [])],
    accountIds: filters.accountIds ?? (filters.accountId ? [filters.accountId] : []),
    savingsGoalIds: filters.savingsGoalIds ?? [],
    quality: filters.quality ?? "",
    internalTransfer: filters.internalTransfer ?? "",
  };
}

function parseAmount(value: string): number | null {
  const normalized = value.trim().replace(",", ".");
  if (!normalized) {
    return null;
  }
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

function toggleNullableId(values: Array<number | null>, next: number | null): Array<number | null> {
  const exists = values.some((value) => value === next);
  return exists ? values.filter((value) => value !== next) : [...values, next];
}

const CLASSIFICATION_SOURCE_OPTIONS: Array<
  FilterMultiSelectOption<TransactionClassificationSourceFilter>
> = [
  { value: "manual", label: "Manual" },
  { value: "rule", label: "Regra" },
  { value: "auto", label: "Automática" },
  { value: "none", label: "Sem origem" },
];

function FieldGroup({
  title,
  children,
  onClear,
}: {
  title: string;
  children: ReactNode;
  onClear?: () => void;
}) {
  return (
    <section className="space-y-2">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-text">{title}</h3>
        {onClear ? (
          <button
            type="button"
            onClick={onClear}
            className="text-xs font-semibold text-muted transition hover:text-text"
          >
            Limpar
          </button>
        ) : null}
      </div>
      {children}
    </section>
  );
}

function ToggleButton({
  selected,
  children,
  onClick,
}: {
  selected: boolean;
  children: ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-md border px-3 py-2 text-sm font-semibold transition",
        selected
          ? "border-accent bg-accent text-accentFg"
          : "border-border bg-bg text-text hover:bg-surface2",
      )}
    >
      {children}
    </button>
  );
}

function Chip({
  selected,
  children,
  onClick,
}: {
  selected: boolean;
  children: ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-pill border px-3 py-1.5 text-xs font-semibold transition",
        selected
          ? "border-accent bg-accent text-accentFg"
          : "border-border bg-bg text-text hover:bg-surface2",
      )}
    >
      {children}
    </button>
  );
}

export function TransactionAdvancedFilters({
  open,
  filters,
  buckets,
  tags,
  accounts,
  savingsGoals,
  onApply,
  onClear,
  onClose,
}: TransactionAdvancedFiltersProps) {
  const [draft, setDraft] = useState(() => draftFromFilters(filters));

  const sortedBuckets = useMemo(
    () => [...buckets].sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0)),
    [buckets],
  );
  const tagOptions = useMemo<Array<FilterMultiSelectOption<number | null>>>(
    () => [
      { value: null, label: "Sem tag" },
      ...tags.map((tag) => ({
        value: tag.id,
        label: tag.name,
        color: tag.color,
        searchText: tag.bucket_name ?? "",
      })),
    ],
    [tags],
  );
  const accountOptions = useMemo<Array<FilterMultiSelectOption<string>>>(
    () => accounts.map((account) => ({ value: account.id, label: account.name })),
    [accounts],
  );
  const savingsGoalOptions = useMemo<Array<FilterMultiSelectOption<number | null>>>(
    () => [
      { value: null, label: "Sem meta poupança" },
      ...savingsGoals.map((goal) => ({ value: goal.id, label: goal.name })),
    ],
    [savingsGoals],
  );
  const rangeInvalid =
    draft.periodMode === "range" &&
    (!draft.rangeFrom || !draft.rangeTo || draft.rangeFrom > draft.rangeTo);

  if (!open) {
    return null;
  }

  const apply = () => {
    const range =
      draft.periodMode === "range" && !rangeInvalid
        ? { from: draft.rangeFrom, to: draft.rangeTo }
        : null;

    onApply({
      range,
      month: draft.periodMode === "month" ? draft.month || null : null,
      type: draft.type || null,
      hidden: draft.hidden,
      amountMin: parseAmount(draft.amountMin),
      amountMax: parseAmount(draft.amountMax),
      accountIds: draft.accountIds,
      bucketIds: draft.bucketIds,
      tagIds: draft.tagIds,
      bucketSources: draft.bucketSources,
      tagSources: draft.tagSources,
      savingsGoalIds: draft.savingsGoalIds,
      quality: draft.quality || null,
      internalTransfer: draft.internalTransfer || null,
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/55">
      <button
        type="button"
        className="hidden flex-1 cursor-default md:block"
        aria-label="Fechar filtros"
        onClick={onClose}
      />
      <aside className="flex h-full w-full max-w-md flex-col border-l border-border bg-surface shadow-2xl">
        <div className="flex items-start justify-between gap-3 border-b border-border px-5 py-4">
          <div>
            <h2 className="text-base font-semibold text-text">Filtros Avançados</h2>
            <p className="mt-1 text-sm text-muted">
              Personalize a visualização das suas transações.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Fechar filtros"
            className="inline-flex h-9 w-9 items-center justify-center rounded-md text-muted transition hover:bg-surface2 hover:text-text"
          >
            <X size={18} aria-hidden />
          </button>
        </div>

        <div className="flex-1 space-y-6 overflow-y-auto px-5 py-5">
          <FieldGroup
            title="Período"
            onClear={() =>
              setDraft((value) => ({
                ...value,
                periodMode: "month",
                month: "",
                rangeFrom: "",
                rangeTo: "",
              }))
            }
          >
            <div className="grid grid-cols-2 gap-2">
              <ToggleButton
                selected={draft.periodMode === "month"}
                onClick={() => setDraft((value) => ({ ...value, periodMode: "month" }))}
              >
                Mês de referência
              </ToggleButton>
              <ToggleButton
                selected={draft.periodMode === "range"}
                onClick={() => setDraft((value) => ({ ...value, periodMode: "range" }))}
              >
                Intervalo
              </ToggleButton>
            </div>

            {draft.periodMode === "month" ? (
              <input
                type="month"
                value={draft.month}
                onChange={(event) =>
                  setDraft((value) => ({ ...value, month: event.target.value }))
                }
                className="h-10 w-full rounded-md border border-border bg-bg px-3 text-sm text-text outline-none"
                aria-label="Selecione um mês de referência"
              />
            ) : (
              <div className="grid grid-cols-2 gap-2">
                <label className="space-y-1 text-xs font-medium text-muted">
                  Data inicial
                  <input
                    type="date"
                    value={draft.rangeFrom}
                    onChange={(event) =>
                      setDraft((value) => ({ ...value, rangeFrom: event.target.value }))
                    }
                    className="h-10 w-full rounded-md border border-border bg-bg px-3 text-sm text-text outline-none"
                  />
                </label>
                <label className="space-y-1 text-xs font-medium text-muted">
                  Data final
                  <input
                    type="date"
                    value={draft.rangeTo}
                    onChange={(event) =>
                      setDraft((value) => ({ ...value, rangeTo: event.target.value }))
                    }
                    className="h-10 w-full rounded-md border border-border bg-bg px-3 text-sm text-text outline-none"
                  />
                </label>
                {rangeInvalid ? (
                  <p className="col-span-2 text-xs text-negative">
                    Informe data inicial e final em ordem cronológica.
                  </p>
                ) : null}
              </div>
            )}
          </FieldGroup>

          <FieldGroup
            title="Faixa de Valor"
            onClear={() => setDraft((value) => ({ ...value, amountMin: "", amountMax: "" }))}
          >
            <div className="grid grid-cols-2 gap-2">
              <label className="flex h-10 items-center gap-2 rounded-md border border-border bg-bg px-3 text-sm text-muted">
                <span>R$</span>
                <input
                  value={draft.amountMin}
                  onChange={(event) =>
                    setDraft((value) => ({ ...value, amountMin: event.target.value }))
                  }
                  inputMode="decimal"
                  placeholder="Valor mínimo"
                  className="min-w-0 flex-1 bg-transparent text-text outline-none placeholder:text-muted"
                />
              </label>
              <label className="flex h-10 items-center gap-2 rounded-md border border-border bg-bg px-3 text-sm text-muted">
                <span>R$</span>
                <input
                  value={draft.amountMax}
                  onChange={(event) =>
                    setDraft((value) => ({ ...value, amountMax: event.target.value }))
                  }
                  inputMode="decimal"
                  placeholder="Valor máximo"
                  className="min-w-0 flex-1 bg-transparent text-text outline-none placeholder:text-muted"
                />
              </label>
            </div>
          </FieldGroup>

          <FieldGroup
            title="Tipo de Transação"
            onClear={() => setDraft((value) => ({ ...value, type: "" }))}
          >
            <div className="grid grid-cols-2 gap-2">
              <ToggleButton
                selected={draft.type === "income"}
                onClick={() =>
                  setDraft((value) => ({
                    ...value,
                    type: value.type === "income" ? "" : "income",
                  }))
                }
              >
                Receitas
              </ToggleButton>
              <ToggleButton
                selected={draft.type === "expense"}
                onClick={() =>
                  setDraft((value) => ({
                    ...value,
                    type: value.type === "expense" ? "" : "expense",
                  }))
                }
              >
                Despesas
              </ToggleButton>
            </div>
          </FieldGroup>

          <FieldGroup
            title="Metas"
            onClear={() => setDraft((value) => ({ ...value, bucketIds: [] }))}
          >
            <div className="flex flex-wrap gap-2">
              <Chip
                selected={draft.bucketIds.some((value) => value === null)}
                onClick={() =>
                  setDraft((value) => ({
                    ...value,
                    bucketIds: toggleNullableId(value.bucketIds, null),
                  }))
                }
              >
                Sem meta
              </Chip>
              {sortedBuckets.map((bucket) => (
                <Chip
                  key={bucket.id}
                  selected={draft.bucketIds.includes(bucket.id)}
                  onClick={() =>
                    setDraft((value) => ({
                      ...value,
                      bucketIds: toggleNullableId(value.bucketIds, bucket.id),
                    }))
                  }
                >
                  {bucket.name}
                </Chip>
              ))}
            </div>
          </FieldGroup>

          <FieldGroup title="Tags" onClear={() => setDraft((value) => ({ ...value, tagIds: [] }))}>
            <FilterMultiSelect
              label="Tag"
              values={draft.tagIds}
              options={tagOptions}
              onChange={(tagIds) => setDraft((value) => ({ ...value, tagIds }))}
              placeholder="Buscar em Tags"
              searchPlaceholder="Buscar em Tags"
            />
          </FieldGroup>

          <FieldGroup
            title="Origem da Meta"
            onClear={() => setDraft((value) => ({ ...value, bucketSources: [] }))}
          >
            <FilterMultiSelect
              label="Origem da Meta"
              values={draft.bucketSources}
              options={CLASSIFICATION_SOURCE_OPTIONS}
              onChange={(bucketSources) =>
                setDraft((value) => ({ ...value, bucketSources }))
              }
              placeholder="Buscar em Origem da Meta"
              searchPlaceholder="Buscar em Origem da Meta"
            />
          </FieldGroup>

          <FieldGroup
            title="Origem da Tag"
            onClear={() => setDraft((value) => ({ ...value, tagSources: [] }))}
          >
            <FilterMultiSelect
              label="Origem da Tag"
              values={draft.tagSources}
              options={CLASSIFICATION_SOURCE_OPTIONS}
              onChange={(tagSources) => setDraft((value) => ({ ...value, tagSources }))}
              placeholder="Buscar em Origem da Tag"
              searchPlaceholder="Buscar em Origem da Tag"
            />
          </FieldGroup>

          <FieldGroup
            title="Contas"
            onClear={() => setDraft((value) => ({ ...value, accountIds: [] }))}
          >
            <FilterMultiSelect
              label="Conta"
              values={draft.accountIds}
              options={accountOptions}
              onChange={(accountIds) => setDraft((value) => ({ ...value, accountIds }))}
              placeholder="Buscar em Contas"
              searchPlaceholder="Buscar em Contas"
            />
          </FieldGroup>

          <FieldGroup
            title="Ocultar dos Relatórios"
            onClear={() => setDraft((value) => ({ ...value, hidden: "exclude" }))}
          >
            <select
              value={draft.hidden}
              onChange={(event) =>
                setDraft((value) => ({
                  ...value,
                  hidden: event.target.value as TransactionHiddenFilter,
                }))
              }
              className="h-10 w-full rounded-md border border-border bg-bg px-3 text-sm text-text outline-none"
            >
              <option value="exclude">Visíveis nos relatórios</option>
              <option value="include">Todos</option>
              <option value="only">Ocultos dos relatórios</option>
            </select>
          </FieldGroup>

          <FieldGroup
            title="Transf. de Mesma Titularidade (Internas)"
            onClear={() => setDraft((value) => ({ ...value, internalTransfer: "" }))}
          >
            <select
              value={draft.internalTransfer}
              onChange={(event) =>
                setDraft((value) => ({
                  ...value,
                  internalTransfer: event.target.value as TransactionInternalTransferFilter | "",
                }))
              }
              className="h-10 w-full rounded-md border border-border bg-bg px-3 text-sm text-text outline-none"
            >
              <option value="">Selecione</option>
              <option value="only">Somente internas</option>
              <option value="exclude">Sem internas</option>
            </select>
          </FieldGroup>

          <FieldGroup
            title="Qualidade da classificação"
            onClear={() => setDraft((value) => ({ ...value, quality: "" }))}
          >
            <select
              value={draft.quality}
              onChange={(event) =>
                setDraft((value) => ({
                  ...value,
                  quality: event.target.value as TransactionQualityFilter | "",
                }))
              }
              className="h-10 w-full rounded-md border border-border bg-bg px-3 text-sm text-text outline-none"
            >
              <option value="">Todas classificações</option>
              <option value="missing_tag">Sem Tag acionável</option>
              <option value="missing_bucket">Sem Meta acionável</option>
            </select>
          </FieldGroup>

          <FieldGroup
            title="Metas de poupança"
            onClear={() => setDraft((value) => ({ ...value, savingsGoalIds: [] }))}
          >
            <FilterMultiSelect
              label="Meta poupança"
              values={draft.savingsGoalIds}
              options={savingsGoalOptions}
              onChange={(savingsGoalIds) =>
                setDraft((value) => ({ ...value, savingsGoalIds }))
              }
              placeholder="Buscar em Metas de poupança"
              searchPlaceholder="Buscar em Metas de poupança"
            />
          </FieldGroup>
        </div>

        <div className="grid grid-cols-2 gap-3 border-t border-border bg-surface px-5 py-4">
          <button
            type="button"
            onClick={() => {
              onClear();
              onClose();
            }}
            className="inline-flex h-10 items-center justify-center rounded-md border border-border px-4 text-sm font-semibold text-text transition hover:bg-surface2"
          >
            Limpar Tudo
          </button>
          <button
            type="button"
            onClick={apply}
            disabled={rangeInvalid}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-accent px-4 text-sm font-semibold text-accentFg transition hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Filter size={16} aria-hidden />
            Aplicar Filtros
          </button>
        </div>
      </aside>
    </div>
  );
}
