"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { CardItem, InvoiceResponse } from "@/lib/types";

export function useCards() {
  return useQuery({
    queryKey: ["cards"],
    queryFn: ({ signal }) => api.get<{ items: CardItem[] }>("/cards", undefined, signal),
    staleTime: 60_000,
  });
}

export function useInvoice(accountId: string | null, month: string) {
  return useQuery({
    queryKey: ["invoice", accountId, month],
    queryFn: ({ signal }) =>
      api.get<InvoiceResponse>("/invoices", { account_id: accountId, month }, signal),
    enabled: Boolean(accountId),
    staleTime: 30_000,
  });
}
