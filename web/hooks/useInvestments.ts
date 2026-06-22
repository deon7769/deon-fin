"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getInvestments, refreshInvestmentQuotes } from "@/lib/investments";

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
