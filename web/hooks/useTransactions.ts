"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { transactionQuery, type TransactionFilters } from "@/lib/transactions";
import type { TransactionPage } from "@/lib/types";

export function useTransactions(filters: TransactionFilters) {
  const query = transactionQuery(filters);

  return useQuery({
    queryKey: ["transactions", query],
    queryFn: ({ signal }) => api.get<TransactionPage>("/transactions", query, signal),
    placeholderData: (previous) => previous,
  });
}
