"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  PainelByTag,
  PainelHistoryPoint,
  PainelHistoryWindow,
  PainelSummary,
  PainelTagType,
} from "@/lib/types";
import { usePeriod } from "@/providers/PeriodProvider";

export function usePainelSummary() {
  const { month } = usePeriod();

  return useQuery({
    queryKey: ["painel", "summary", month],
    queryFn: ({ signal }) => api.get<PainelSummary>("/painel/summary", { month }, signal),
    staleTime: 30_000,
  });
}

export function usePainelHistory(window: PainelHistoryWindow) {
  return useQuery({
    queryKey: ["painel", "history", window],
    queryFn: ({ signal }) => api.get<PainelHistoryPoint[]>("/painel/history", { window }, signal),
    staleTime: 60_000,
  });
}

export function usePainelByTag(type: PainelTagType) {
  const { month } = usePeriod();

  return useQuery({
    queryKey: ["painel", "by-tag", month, type],
    queryFn: ({ signal }) => api.get<PainelByTag>("/painel/by-tag", { month, type }, signal),
    staleTime: 30_000,
  });
}
