"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { MaintenanceResponse } from "@/lib/types";

export function useMaintenance() {
  return useQuery({
    queryKey: ["maintenance"],
    queryFn: ({ signal }) => api.get<MaintenanceResponse>("/maintenance", undefined, signal),
    staleTime: 30_000,
  });
}
