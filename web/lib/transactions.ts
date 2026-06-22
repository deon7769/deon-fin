import type { Transaction, TransactionHiddenFilter, TransactionType } from "./types";

export type TransactionDateRange = {
  from: string;
  to: string;
};

export type TransactionFilters = {
  month?: string | null;
  range?: TransactionDateRange | null;
  q?: string | null;
  type?: TransactionType | null;
  hidden?: TransactionHiddenFilter;
  amountMin?: number | null;
  amountMax?: number | null;
  accountId?: string | null;
  bucketIds?: Array<number | null>;
  tagIds?: Array<number | null>;
  page?: number;
  pageSize?: number;
};

export type TransactionQuery = Record<string, string | number | boolean>;

function idsParam(values?: Array<number | null>): string | undefined {
  if (!values?.length) {
    return undefined;
  }

  const tokens = values.map((value) => (value === null ? "none" : String(value)));
  return tokens.length ? tokens.join(",") : undefined;
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
  if (filters.accountId) {
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
      filters.bucketIds?.length ||
      filters.tagIds?.length,
  );
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
