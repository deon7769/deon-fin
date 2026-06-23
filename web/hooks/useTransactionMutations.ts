"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Transaction, TransactionType } from "@/lib/types";

export type TransactionPatchInput = {
  hidden?: boolean;
  note?: string | null;
  reference_month?: string | null;
  bucket_id?: number | null;
  tag_id?: number | null;
  savings_goal_id?: number | null;
};

export type CreateTransactionInput = {
  account_id: string;
  posted_at: string;
  amount: number;
  type: TransactionType;
  description: string;
  bucket_id?: number | null;
  tag_id?: number | null;
  note?: string | null;
  reference_month?: string | null;
};

export type CreateTransactionResponse = {
  duplicate: boolean;
  transaction: Transaction;
};

export type BulkUpdateTransactionsResponse = {
  updated: number;
  not_found: string[];
};

export function useUpdateTransaction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (vars: { id: string; input: TransactionPatchInput }) =>
      api.patch<Transaction>(`/transactions/${vars.id}`, vars.input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["tags"] });
      queryClient.invalidateQueries({ queryKey: ["painel"] });
      queryClient.invalidateQueries({ queryKey: ["budget"] });
      queryClient.invalidateQueries({ queryKey: ["savings"] });
      queryClient.invalidateQueries({ queryKey: ["savingsGoalTransactions"] });
      queryClient.invalidateQueries({ queryKey: ["savingsGoalCandidates"] });
    },
  });
}

export function useCreateTransaction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: CreateTransactionInput) =>
      api.post<CreateTransactionResponse>("/transactions", input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["tags"] });
      queryClient.invalidateQueries({ queryKey: ["painel"] });
      queryClient.invalidateQueries({ queryKey: ["budget"] });
      queryClient.invalidateQueries({ queryKey: ["savings"] });
      queryClient.invalidateQueries({ queryKey: ["savingsGoalTransactions"] });
      queryClient.invalidateQueries({ queryKey: ["savingsGoalCandidates"] });
    },
  });
}

export function useDeleteTransaction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.del<{ deleted_id: string }>(`/transactions/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["tags"] });
      queryClient.invalidateQueries({ queryKey: ["painel"] });
      queryClient.invalidateQueries({ queryKey: ["budget"] });
      queryClient.invalidateQueries({ queryKey: ["savings"] });
      queryClient.invalidateQueries({ queryKey: ["savingsGoalTransactions"] });
      queryClient.invalidateQueries({ queryKey: ["savingsGoalCandidates"] });
    },
  });
}

export function useBulkUpdateTransactions() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (vars: { ids: string[]; patch: TransactionPatchInput }) =>
      api.patch<BulkUpdateTransactionsResponse>("/transactions/bulk", {
        ids: vars.ids,
        patch: vars.patch,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["tags"] });
      queryClient.invalidateQueries({ queryKey: ["painel"] });
      queryClient.invalidateQueries({ queryKey: ["budget"] });
      queryClient.invalidateQueries({ queryKey: ["savings"] });
      queryClient.invalidateQueries({ queryKey: ["savingsGoalTransactions"] });
      queryClient.invalidateQueries({ queryKey: ["savingsGoalCandidates"] });
    },
  });
}
