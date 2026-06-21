"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Budget } from "@/lib/types";
import { usePeriod } from "@/providers/PeriodProvider";

export function useBudget() {
  const { month } = usePeriod();

  return useQuery({
    queryKey: ["budget", month],
    queryFn: ({ signal }) => api.get<Budget>("/budget", { month }, signal),
    staleTime: 30_000,
  });
}
