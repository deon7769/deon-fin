import { formatBRL } from "./format";
import type { Transaction, TransactionHiddenFilter, TransactionType } from "./types";

export type TransactionDateRange = {
  from: string;
  to: string;
};

export type TransactionQualityFilter = "missing_tag" | "missing_bucket";
export type TransactionInternalTransferFilter = "only" | "exclude";
export type TransactionClassificationSourceFilter = "manual" | "rule" | "auto" | "none";

export type TransactionFilters = {
  month?: string | null;
  range?: TransactionDateRange | null;
  q?: string | null;
  type?: TransactionType | null;
  hidden?: TransactionHiddenFilter;
  amountMin?: number | null;
  amountMax?: number | null;
  accountId?: string | null;
  accountIds?: string[];
  bucketIds?: Array<number | null>;
  tagIds?: Array<number | null>;
  bucketSources?: readonly TransactionClassificationSourceFilter[];
  tagSources?: readonly TransactionClassificationSourceFilter[];
  savingsGoalIds?: Array<number | null>;
  quality?: TransactionQualityFilter | null;
  internalTransfer?: TransactionInternalTransferFilter | null;
  page?: number;
  pageSize?: number;
};

export type TransactionAdvancedFilterPatch = {
  range?: TransactionDateRange | null;
  month?: string | null;
  type?: TransactionType | null;
  hidden?: TransactionHiddenFilter;
  amountMin?: number | null;
  amountMax?: number | null;
  accountIds?: string[];
  bucketIds?: Array<number | null>;
  tagIds?: Array<number | null>;
  bucketSources?: readonly TransactionClassificationSourceFilter[];
  tagSources?: readonly TransactionClassificationSourceFilter[];
  savingsGoalIds?: Array<number | null>;
  quality?: TransactionQualityFilter | null;
  internalTransfer?: TransactionInternalTransferFilter | null;
};

export type TransactionQuery = Record<string, string | number | boolean>;

type FilterLookupItem = {
  id: number;
  name: string;
};

type AccountFilterLookupItem = {
  id: string;
  name: string;
};

type TransactionFilterBadgeContext = {
  buckets?: FilterLookupItem[];
  tags?: FilterLookupItem[];
  savingsGoals?: FilterLookupItem[];
  accounts?: AccountFilterLookupItem[];
};

const CLASSIFICATION_SOURCE_LABELS: Record<TransactionClassificationSourceFilter, string> = {
  manual: "Manual",
  rule: "Regra",
  auto: "Automática",
  none: "Sem origem",
};

function idsParam(values?: Array<number | null>): string | undefined {
  if (!values?.length) {
    return undefined;
  }

  const tokens = values.map((value) => (value === null ? "none" : String(value)));
  return tokens.length ? tokens.join(",") : undefined;
}

function stringListParam(values?: readonly string[]): string | undefined {
  const normalized = (values ?? []).map((value) => value.trim()).filter(Boolean);
  return normalized.length ? normalized.join(",") : undefined;
}

function compactBRL(value: number): string {
  return formatBRL(value).replace(/,00$/, "");
}

function positiveInt(value: number | undefined, fallback: number): number {
  if (!Number.isFinite(value ?? NaN)) {
    return fallback;
  }
  return Math.max(1, Math.floor(value as number));
}

export function clampPageSize(value: number | undefined): number {
  if (!Number.isFinite(value ?? NaN)) {
    return 25;
  }
  if ((value as number) <= 0) {
    return 10;
  }
  return Math.min(100, Math.floor(value as number));
}

export function semTagFilterFromSearch(value: string | null): Array<number | null> | undefined {
  return value === "1" || value === "true" ? [null] : undefined;
}

export function qualityFilterFromSearch(value: string | null): TransactionQualityFilter | undefined {
  return value === "missing_tag" || value === "missing_bucket" ? value : undefined;
}

export function internalTransferFilterFromSearch(
  value: string | null,
): TransactionInternalTransferFilter | undefined {
  return value === "only" || value === "exclude" ? value : undefined;
}

export function stringListFilterFromSearch(value: string | null): string[] | undefined {
  if (!value?.trim()) {
    return undefined;
  }
  const parsed = value
    .split(",")
    .map((token) => token.trim())
    .filter(Boolean);
  return parsed.length ? parsed : undefined;
}

export function classificationSourceFilterFromSearch(
  value: string | null,
): TransactionClassificationSourceFilter[] | undefined {
  if (!value?.trim()) {
    return undefined;
  }

  const parsed = value
    .split(",")
    .map((token) => token.trim())
    .filter((token): token is TransactionClassificationSourceFilter =>
      token === "manual" || token === "rule" || token === "auto" || token === "none",
    );
  return parsed.length ? parsed : undefined;
}

export function idsFilterFromSearch(value: string | null): Array<number | null> | undefined {
  if (!value?.trim()) {
    return undefined;
  }

  const parsed: Array<number | null> = [];
  for (const rawToken of value.split(",")) {
    const token = rawToken.trim();
    if (!token) {
      continue;
    }
    if (token === "none") {
      parsed.push(null);
      continue;
    }
    const numeric = Number(token);
    if (Number.isInteger(numeric) && numeric > 0) {
      parsed.push(numeric);
    }
  }

  return parsed.length ? parsed : undefined;
}

export function transactionQuery(filters: TransactionFilters): TransactionQuery {
  const query: TransactionQuery = {};
  if (filters.range?.from && filters.range?.to) {
    query.from = filters.range.from;
    query.to = filters.range.to;
  } else if (filters.month) {
    query.month = filters.month;
  }

  const q = filters.q?.trim();
  if (q) {
    query.q = q;
  }
  if (filters.type) {
    query.type = filters.type;
  }
  if (filters.amountMin !== undefined && filters.amountMin !== null) {
    query.min = filters.amountMin;
  }
  if (filters.amountMax !== undefined && filters.amountMax !== null) {
    query.max = filters.amountMax;
  }
  const accountIds = stringListParam(filters.accountIds);
  if (accountIds) {
    query.account_ids = accountIds;
  } else if (filters.accountId) {
    query.account_id = filters.accountId;
  }

  const bucketIds = idsParam(filters.bucketIds);
  if (bucketIds) {
    query.bucket_ids = bucketIds;
  }
  const tagIds = idsParam(filters.tagIds);
  if (tagIds) {
    query.tag_ids = tagIds;
  }
  const bucketSources = stringListParam(filters.bucketSources);
  if (bucketSources) {
    query.bucket_source = bucketSources;
  }
  const tagSources = stringListParam(filters.tagSources);
  if (tagSources) {
    query.tag_source = tagSources;
  }
  const savingsGoalIds = idsParam(filters.savingsGoalIds);
  if (savingsGoalIds) {
    query.savings_goal_id = savingsGoalIds;
  }
  if (filters.quality) {
    query.quality = filters.quality;
  }
  if (filters.internalTransfer) {
    query.internal_transfer = filters.internalTransfer;
  }

  if (filters.hidden) {
    query.hidden = filters.hidden;
  }
  query.page = positiveInt(filters.page, 1);
  query.page_size = clampPageSize(filters.pageSize);
  return query;
}

export function hasTransactionFilters(filters: TransactionFilters): boolean {
  return Boolean(
    filters.q?.trim() ||
      filters.type ||
      (filters.hidden && filters.hidden !== "exclude") ||
      filters.amountMin !== undefined ||
      filters.amountMax !== undefined ||
      filters.accountId ||
      filters.accountIds?.length ||
      filters.bucketIds?.length ||
      filters.tagIds?.length ||
      filters.bucketSources?.length ||
      filters.tagSources?.length ||
      filters.savingsGoalIds?.length ||
      filters.quality ||
      filters.internalTransfer,
  );
}

function lookupFilterName(
  value: number | null,
  items: FilterLookupItem[] | undefined,
  emptyLabel: string,
  fallbackPrefix: string,
): string {
  if (value === null) {
    return emptyLabel;
  }
  return items?.find((item) => item.id === value)?.name ?? `${fallbackPrefix} #${value}`;
}

export function transactionFilterBadges(
  filters: TransactionFilters,
  context: TransactionFilterBadgeContext = {},
): string[] {
  const badges: string[] = [];

  for (const bucketId of filters.bucketIds ?? []) {
    badges.push(
      `Meta: ${lookupFilterName(bucketId, context.buckets, "Sem meta", "Meta")}`,
    );
  }
  for (const tagId of filters.tagIds ?? []) {
    badges.push(`Tag: ${lookupFilterName(tagId, context.tags, "Sem tag", "Tag")}`);
  }
  for (const source of filters.bucketSources ?? []) {
    badges.push(`Origem Meta: ${CLASSIFICATION_SOURCE_LABELS[source]}`);
  }
  for (const source of filters.tagSources ?? []) {
    badges.push(`Origem Tag: ${CLASSIFICATION_SOURCE_LABELS[source]}`);
  }
  for (const savingsGoalId of filters.savingsGoalIds ?? []) {
    badges.push(
      `Meta poupança: ${lookupFilterName(
        savingsGoalId,
        context.savingsGoals,
        "Sem meta",
        "Meta poupança",
      )}`,
    );
  }
  for (const accountId of filters.accountIds ?? []) {
    badges.push(
      `Conta: ${
        context.accounts?.find((item) => item.id === accountId)?.name ?? `Conta ${accountId}`
      }`,
    );
  }
  if (filters.quality === "missing_tag") {
    badges.push("Qualidade: Sem Tag acionável");
  } else if (filters.quality === "missing_bucket") {
    badges.push("Qualidade: Sem Meta acionável");
  }

  const q = filters.q?.trim();
  if (q) {
    badges.push(`Busca: ${q}`);
  }
  if (filters.type) {
    badges.push(`Tipo: ${filters.type === "income" ? "Receitas" : "Despesas"}`);
  }
  if (filters.amountMin !== undefined || filters.amountMax !== undefined) {
    const min = filters.amountMin !== undefined ? compactBRL(filters.amountMin ?? 0) : null;
    const max = filters.amountMax !== undefined ? compactBRL(filters.amountMax ?? 0) : null;
    badges.push(`Valor: ${min ?? "mín."} - ${max ?? "máx."}`);
  }
  if (filters.hidden && filters.hidden !== "exclude") {
    badges.push(
      filters.hidden === "only" ? "Ocultas: Somente ocultas" : "Ocultas: Incluídas",
    );
  }
  if (filters.internalTransfer === "only") {
    badges.push("Transferências internas: Somente internas");
  } else if (filters.internalTransfer === "exclude") {
    badges.push("Transferências internas: Sem internas");
  }

  return badges;
}

export function transactionDisplayValue(
  transaction: Pick<Transaction, "amount" | "signed_value" | "display_value">,
): number {
  return transaction.display_value ?? transaction.signed_value;
}

export function transactionCategoryLabel(
  transaction: Pick<Transaction, "category" | "category_label">,
): string {
  return transaction.category_label?.trim() || transaction.category?.trim() || "Sem categoria";
}

export function transactionClassificationFeedback(
  kind: "tag" | "bucket",
  result: { updated?: number; similar_affected?: number },
): string {
  const label = kind === "tag" ? "Tag" : "Meta";
  const similar = Math.max(0, Number(result.similar_affected ?? 0));
  if (similar > 0) {
    const total = Math.max(1, Number(result.updated ?? 1)) + similar;
    return `${label} atualizada em ${total} lançamento(s), incluindo ${similar} similar(es).`;
  }
  return `${label} atualizada.`;
}

export function parseTransactionAmountInput(value: string): number | null {
  const raw = value.trim();
  if (!raw || /[^0-9.,]/.test(raw)) {
    return null;
  }

  let normalized: string | null = null;
  if (raw.includes(",") && raw.includes(".")) {
    if (/^\d{1,3}(\.\d{3})+,\d{1,2}$/.test(raw)) {
      normalized = raw.replace(/\./g, "").replace(",", ".");
    }
  } else if (raw.includes(",")) {
    if (/^\d+(,\d{1,2})?$/.test(raw)) {
      normalized = raw.replace(",", ".");
    }
  } else if (raw.includes(".")) {
    if (/^\d+\.\d{1,2}$/.test(raw)) {
      normalized = raw;
    } else if (/^\d{1,3}(\.\d{3})+$/.test(raw)) {
      normalized = raw.replace(/\./g, "");
    }
  } else if (/^\d+$/.test(raw)) {
    normalized = raw;
  }

  if (normalized === null) {
    return null;
  }
  const parsed = Number(normalized);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return null;
  }
  return Math.round(parsed * 100) / 100;
}
