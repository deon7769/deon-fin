"use client";

import { useQuery } from "@tanstack/react-query";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { MaintenanceSavePayload } from "@/lib/maintenance";
import type {
  MaintenanceResponse,
  MaintenanceSystemTotalsPayload,
  MaintenanceSystemTotalsResponse,
} from "@/lib/types";

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

export function useMaintenanceSystemTotals() {
  return useQuery({
    queryKey: ["maintenance", "system-totals"],
    queryFn: ({ signal }) =>
      api.get<MaintenanceSystemTotalsResponse>("/maintenance/system-totals", undefined, signal),
    staleTime: 30_000,
  });
}

export function useSaveMaintenanceSystemTotals() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: MaintenanceSystemTotalsPayload) =>
      api.patch<MaintenanceSystemTotalsResponse>("/maintenance/system-totals", payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["maintenance", "system-totals"] });
      void queryClient.invalidateQueries({ queryKey: ["painel"] });
      void queryClient.invalidateQueries({ queryKey: ["budget"] });
      void queryClient.invalidateQueries({ queryKey: ["accounts"] });
    },
  });
}
