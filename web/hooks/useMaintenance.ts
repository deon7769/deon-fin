"use client";

import { useQuery } from "@tanstack/react-query";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { MaintenanceSavePayload } from "@/lib/maintenance";
import type { MaintenanceResponse } from "@/lib/types";

export function useMaintenance() {
  return useQuery({
    queryKey: ["maintenance"],
    queryFn: ({ signal }) => api.get<MaintenanceResponse>("/maintenance", undefined, signal),
    staleTime: 30_000,
  });
}

export function useSaveMaintenance() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: MaintenanceSavePayload) =>
      api.post<{ saved: boolean }>("/maintenance", payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["maintenance"] });
    },
  });
}
