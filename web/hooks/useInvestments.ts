"use client";

import { useQuery } from "@tanstack/react-query";
import { getInvestments } from "@/lib/investments";

export function useInvestments(includeInactive = false) {
  return useQuery({
    queryKey: ["investments", includeInactive],
    queryFn: ({ signal }) => getInvestments(includeInactive, signal),
    staleTime: 30_000,
  });
}
