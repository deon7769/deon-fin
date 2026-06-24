"use client";

import { useMemo } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { usePeriod } from "@/providers/PeriodProvider";
import {
  clampPageSize,
  classificationSourceFilterFromSearch,
  hasTransactionFilters,
  idsFilterFromSearch,
  internalTransferFilterFromSearch,
  qualityFilterFromSearch,
  semTagFilterFromSearch,
  stringListFilterFromSearch,
  type TransactionAdvancedFilterPatch,
  type TransactionFilters,
} from "@/lib/transactions";
import type { TransactionHiddenFilter, TransactionType } from "@/lib/types";

function parsePage(value: string | null): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? Math.floor(parsed) : 1;
}

function parseType(value: string | null): TransactionType | null {
  return value === "income" || value === "expense" ? value : null;
}

function parseHidden(value: string | null): TransactionHiddenFilter {
  return value === "include" || value === "only" ? value : "exclude";
}

function parseAmount(value: string | null): number | null {
  if (value === null || value.trim() === "") {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function idsParam(values?: Array<number | null>): string | null {
  if (!values?.length) {
    return null;
  }
  return values.map((value) => (value === null ? "none" : String(value))).join(",");
}

function stringListParam(values?: readonly string[]): string | null {
  const normalized = (values ?? []).map((value) => value.trim()).filter(Boolean);
  return normalized.length ? normalized.join(",") : null;
}

export function useTransactionFilters() {
  const period = usePeriod();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const filters = useMemo<TransactionFilters>(
    () => ({
      month: period.mode === "month" ? period.month : null,
      range: period.mode === "range" ? period.range : null,
      q: searchParams.get("q") ?? "",
      type: parseType(searchParams.get("type")),
      hidden: parseHidden(searchParams.get("hidden")),
      amountMin: parseAmount(searchParams.get("min")),
      amountMax: parseAmount(searchParams.get("max")),
      accountIds:
        stringListFilterFromSearch(searchParams.get("account_ids")) ??
        stringListFilterFromSearch(searchParams.get("account_id")),
      bucketIds: idsFilterFromSearch(searchParams.get("bucket_ids")),
      tagIds:
        semTagFilterFromSearch(searchParams.get("semTag")) ??
        idsFilterFromSearch(searchParams.get("tag_ids")),
      bucketSources: classificationSourceFilterFromSearch(searchParams.get("bucket_source")),
      tagSources: classificationSourceFilterFromSearch(searchParams.get("tag_source")),
      savingsGoalIds: idsFilterFromSearch(searchParams.get("savings_goal_id")),
      quality: qualityFilterFromSearch(searchParams.get("quality")),
      internalTransfer: internalTransferFilterFromSearch(searchParams.get("internal_transfer")),
      page: parsePage(searchParams.get("page")),
      pageSize: clampPageSize(Number(searchParams.get("page_size") ?? 25)),
    }),
    [period.mode, period.month, period.range, searchParams],
  );

  const replaceParams = (patch: Record<string, string | number | null>, resetPage = true) => {
    const params = new URLSearchParams(searchParams.toString());
    for (const [key, value] of Object.entries(patch)) {
      if (value === null || value === "") {
        params.delete(key);
      } else {
        params.set(key, String(value));
      }
    }
    if (resetPage) {
      params.delete("page");
    }
    const query = params.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  };

  const applyAdvancedFilters = (patch: TransactionAdvancedFilterPatch) => {
    const params = new URLSearchParams(searchParams.toString());
    const setParam = (key: string, value: string | number | null | undefined) => {
      if (value === null || value === undefined || value === "") {
        params.delete(key);
      } else {
        params.set(key, String(value));
      }
    };

    if ("range" in patch || "month" in patch) {
      if (patch.range?.from && patch.range.to) {
        params.set("from", patch.range.from);
        params.set("to", patch.range.to);
        params.delete("month");
      } else {
        params.delete("from");
        params.delete("to");
        setParam("month", patch.month);
      }
    }

    setParam("type", patch.type);
    setParam("hidden", patch.hidden && patch.hidden !== "exclude" ? patch.hidden : null);
    setParam("min", patch.amountMin);
    setParam("max", patch.amountMax);
    setParam("account_ids", stringListParam(patch.accountIds));
    params.delete("account_id");
    setParam("bucket_ids", idsParam(patch.bucketIds));
    setParam("tag_ids", idsParam(patch.tagIds));
    setParam("bucket_source", stringListParam(patch.bucketSources));
    setParam("tag_source", stringListParam(patch.tagSources));
    setParam("savings_goal_id", idsParam(patch.savingsGoalIds));
    setParam("quality", patch.quality);
    setParam("internal_transfer", patch.internalTransfer);
    params.delete("semTag");
    params.delete("page");

    const query = params.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  };

  const clearFilters = () => {
    const params = new URLSearchParams(searchParams.toString());
    for (const key of [
      "q",
      "type",
      "hidden",
      "from",
      "to",
      "min",
      "max",
      "account_id",
      "account_ids",
      "page",
      "page_size",
      "semTag",
      "bucket_ids",
      "tag_ids",
      "bucket_source",
      "tag_source",
      "savings_goal_id",
      "quality",
      "internal_transfer",
    ]) {
      params.delete(key);
    }
    const query = params.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  };

  return {
    filters,
    hasFilters: hasTransactionFilters(filters),
    setSearch: (q: string) => replaceParams({ q }),
    setType: (type: TransactionType | null) => replaceParams({ type }),
    setHidden: (hidden: TransactionHiddenFilter) =>
      replaceParams({ hidden: hidden === "exclude" ? null : hidden }),
    setSavingsGoal: (savingsGoalId: number | null | undefined) =>
      replaceParams({
        savings_goal_id:
          savingsGoalId === undefined ? null : savingsGoalId === null ? "none" : savingsGoalId,
      }),
    setQuality: (quality: NonNullable<TransactionFilters["quality"]> | null) =>
      replaceParams({ quality }),
    applyAdvancedFilters,
    setPage: (page: number) => replaceParams({ page }, false),
    setPageSize: (pageSize: number) => replaceParams({ page_size: pageSize }),
    clearFilters,
  };
}
