"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createInvestmentAsset,
  deleteInvestmentAsset,
  getInvestments,
  refreshInvestmentQuotes,
  searchInvestmentTickers,
  updateInvestmentAsset,
} from "@/lib/investments";
import type { InvestmentAssetInput } from "@/lib/types";

export function useInvestments(includeInactive = false) {
  return useQuery({
    queryKey: ["investments", includeInactive],
    queryFn: ({ signal }) => getInvestments(includeInactive, signal),
    staleTime: 30_000,
  });
}

export function useRefreshInvestmentQuotes() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: refreshInvestmentQuotes,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["investments"] });
    },
  });
}

export function useTickerSearch(query: string, assetClass: string) {
  return useQuery({
    queryKey: ["investments", "ticker-search", assetClass, query],
    queryFn: ({ signal }) => searchInvestmentTickers(query, assetClass, signal),
    enabled: query.trim().length >= 2,
    staleTime: 5 * 60_000,
  });
}

export function useCreateInvestmentAsset() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: InvestmentAssetInput) => createInvestmentAsset(input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["investments"] });
    },
  });
}

export function useUpdateInvestmentAsset() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (vars: { id: number; input: Partial<InvestmentAssetInput> }) =>
      updateInvestmentAsset(vars.id, vars.input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["investments"] });
    },
  });
}

export function useDeleteInvestmentAsset() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => deleteInvestmentAsset(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["investments"] });
    },
  });
}
