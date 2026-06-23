"use client";

import { useQuery } from "@tanstack/react-query";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { MaintenanceSavePayload } from "@/lib/maintenance";
import type {
  MaintenanceClassificationAuditResponse,
  MaintenanceClassificationBulkApplyResponse,
  MaintenanceClassificationBulkPreviewResponse,
  MaintenanceClassificationBulkRequest,
  MaintenanceClassificationRulePatch,
  MaintenanceClassificationReprocessResponse,
  MaintenanceClassificationRulesResponse,
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

function invalidateClassificationData(queryClient: ReturnType<typeof useQueryClient>) {
  void queryClient.invalidateQueries({ queryKey: ["maintenance"] });
  void queryClient.invalidateQueries({ queryKey: ["maintenance", "classification-audit"] });
  void queryClient.invalidateQueries({ queryKey: ["maintenance", "classification-rules"] });
  void queryClient.invalidateQueries({ queryKey: ["transactions"] });
  void queryClient.invalidateQueries({ queryKey: ["tags"] });
  void queryClient.invalidateQueries({ queryKey: ["painel"] });
  void queryClient.invalidateQueries({ queryKey: ["budget"] });
}

export function useReprocessMaintenanceClassification() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () =>
      api.post<MaintenanceClassificationReprocessResponse>("/maintenance/classification/reprocess"),
    onSuccess: () => {
      invalidateClassificationData(queryClient);
    },
  });
}

export function usePreviewMaintenanceClassificationBulk() {
  return useMutation({
    mutationFn: (payload: MaintenanceClassificationBulkRequest) =>
      api.post<MaintenanceClassificationBulkPreviewResponse>(
        "/maintenance/classification/bulk-preview",
        payload,
      ),
  });
}

export function useApplyMaintenanceClassificationBulk() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: MaintenanceClassificationBulkRequest) =>
      api.post<MaintenanceClassificationBulkApplyResponse>(
        "/maintenance/classification/bulk-apply",
        payload,
      ),
    onSuccess: () => {
      invalidateClassificationData(queryClient);
    },
  });
}

export function useMaintenanceClassificationRules() {
  return useQuery({
    queryKey: ["maintenance", "classification-rules"],
    queryFn: ({ signal }) =>
      api.get<MaintenanceClassificationRulesResponse>(
        "/maintenance/classification/rules",
        undefined,
        signal,
      ),
    staleTime: 30_000,
  });
}

export function useMaintenanceClassificationAudit() {
  return useQuery({
    queryKey: ["maintenance", "classification-audit"],
    queryFn: ({ signal }) =>
      api.get<MaintenanceClassificationAuditResponse>(
        "/maintenance/classification/audit",
        undefined,
        signal,
      ),
    staleTime: 30_000,
  });
}

export function useSaveMaintenanceClassificationRule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: MaintenanceClassificationRulePatch) =>
      api.patch<MaintenanceClassificationRulesResponse>(
        "/maintenance/classification/rules",
        payload,
      ),
    onSuccess: () => {
      invalidateClassificationData(queryClient);
    },
  });
}
