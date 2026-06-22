"use client";

import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  calcularInvestmentAporte,
  confirmarInvestmentAporte,
  createInvestmentQuestion,
  createInvestmentAsset,
  deleteInvestmentQuestion,
  deleteInvestmentAsset,
  getInvestmentAssetAnswers,
  getInvestmentCountry,
  getInvestmentMap,
  getInvestmentQuestions,
  getInvestmentProfiles,
  getInvestmentTargets,
  getInvestments,
  refreshInvestmentQuotes,
  restoreInvestmentQuestions,
  saveInvestmentTargets,
  saveInvestmentAssetAnswers,
  searchInvestmentTickers,
  updateInvestmentQuestion,
  updateInvestmentAsset,
} from "@/lib/investments";
import type {
  InvestmentAssetAnswersInput,
  InvestmentAssetInput,
  InvestmentAporteConfirmInput,
  InvestmentAporteCalculateInput,
  InvestmentMapCountry,
  InvestmentQuestionInput,
  InvestmentTargetsMap,
} from "@/lib/types";

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

export function useInvestmentTargets() {
  return useQuery({
    queryKey: ["investments", "targets"],
    queryFn: ({ signal }) => getInvestmentTargets(signal),
    staleTime: 30_000,
  });
}

export function useInvestmentProfiles() {
  return useQuery({
    queryKey: ["investments", "profiles"],
    queryFn: ({ signal }) => getInvestmentProfiles(signal),
    staleTime: 5 * 60_000,
  });
}

export function useInvestmentMap() {
  return useQuery({
    queryKey: ["investments", "map"],
    queryFn: ({ signal }) => getInvestmentMap(signal),
    staleTime: 5 * 60_000,
  });
}

export function useInvestmentCountry(code: string | null) {
  return useQuery({
    queryKey: ["investments", "map", code],
    queryFn: ({ signal }) => getInvestmentCountry(code as string, signal),
    enabled: Boolean(code),
    staleTime: 5 * 60_000,
  });
}

export function useInvestmentCountryDetails(countries: InvestmentMapCountry[]) {
  return useQueries({
    queries: countries.map((country) => ({
      queryKey: ["investments", "map", country.code],
      queryFn: ({ signal }: { signal: AbortSignal }) => getInvestmentCountry(country.code, signal),
      staleTime: 5 * 60_000,
    })),
  });
}

export function useSaveInvestmentTargets() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: { targets: InvestmentTargetsMap; perfil?: string }) =>
      saveInvestmentTargets(input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["investments", "targets"] });
      queryClient.invalidateQueries({ queryKey: ["investments"] });
    },
  });
}

export function useCalcularInvestmentAporte() {
  return useMutation({
    mutationFn: (input: InvestmentAporteCalculateInput) => calcularInvestmentAporte(input),
  });
}

export function useConfirmarInvestmentAporte() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: InvestmentAporteConfirmInput) => confirmarInvestmentAporte(input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["investments"] });
      queryClient.invalidateQueries({ queryKey: ["investments", "targets"] });
    },
  });
}

export function useInvestmentQuestions(diagramType: string) {
  return useQuery({
    queryKey: ["investments", "questions", diagramType],
    queryFn: ({ signal }) => getInvestmentQuestions(diagramType, signal),
    staleTime: 30_000,
  });
}

export function useCreateInvestmentQuestion() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: InvestmentQuestionInput) => createInvestmentQuestion(input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["investments", "questions"] });
      queryClient.invalidateQueries({ queryKey: ["investments"] });
    },
  });
}

export function useUpdateInvestmentQuestion() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (vars: { id: number; input: Partial<InvestmentQuestionInput> }) =>
      updateInvestmentQuestion(vars.id, vars.input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["investments", "questions"] });
      queryClient.invalidateQueries({ queryKey: ["investments"] });
    },
  });
}

export function useDeleteInvestmentQuestion() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => deleteInvestmentQuestion(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["investments", "questions"] });
      queryClient.invalidateQueries({ queryKey: ["investments"] });
    },
  });
}

export function useRestoreInvestmentQuestions() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (diagramType: string) => restoreInvestmentQuestions(diagramType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["investments", "questions"] });
      queryClient.invalidateQueries({ queryKey: ["investments"] });
    },
  });
}

export function useInvestmentAssetAnswers(assetId: number | null, enabled = true) {
  return useQuery({
    queryKey: ["investments", "assets", assetId, "answers"],
    queryFn: ({ signal }) => getInvestmentAssetAnswers(assetId as number, signal),
    enabled: enabled && assetId !== null,
    staleTime: 30_000,
  });
}

export function useSaveInvestmentAssetAnswers() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (vars: { id: number; input: InvestmentAssetAnswersInput }) =>
      saveInvestmentAssetAnswers(vars.id, vars.input),
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({ queryKey: ["investments", "assets", vars.id, "answers"] });
      queryClient.invalidateQueries({ queryKey: ["investments"] });
    },
  });
}
