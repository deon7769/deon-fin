"use client";

import { useMemo } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { usePeriod } from "@/providers/PeriodProvider";
import {
  clampPageSize,
  hasTransactionFilters,
  idsFilterFromSearch,
  qualityFilterFromSearch,
  semTagFilterFromSearch,
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
      bucketIds: idsFilterFromSearch(searchParams.get("bucket_ids")),
      tagIds:
        semTagFilterFromSearch(searchParams.get("semTag")) ??
        idsFilterFromSearch(searchParams.get("tag_ids")),
      savingsGoalIds: idsFilterFromSearch(searchParams.get("savings_goal_id")),
      quality: qualityFilterFromSearch(searchParams.get("quality")),
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

  const clearFilters = () => {
    const params = new URLSearchParams(searchParams.toString());
    for (const key of [
      "q",
      "type",
      "hidden",
      "page",
      "page_size",
      "semTag",
      "bucket_ids",
      "tag_ids",
      "savings_goal_id",
      "quality",
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
    setPage: (page: number) => replaceParams({ page }, false),
    setPageSize: (pageSize: number) => replaceParams({ page_size: pageSize }),
    clearFilters,
  };
}
