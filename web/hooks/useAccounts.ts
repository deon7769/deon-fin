"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  AccountCredentialsResponse,
  AccountDeleteResponse,
  AccountSyncResponse,
  AccountsResponse,
} from "@/lib/types";
import { usePeriod } from "@/providers/PeriodProvider";

function accountPath(accountId: string, suffix = "") {
  return `/accounts/${encodeURIComponent(accountId)}${suffix}`;
}

function invalidateAccountSurfaces(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: ["accounts"] });
  queryClient.invalidateQueries({ queryKey: ["painel"] });
  queryClient.invalidateQueries({ queryKey: ["cards"] });
  queryClient.invalidateQueries({ queryKey: ["invoice"] });
}

export function useAccounts() {
  const { month } = usePeriod();

  return useQuery({
    queryKey: ["accounts", month],
    queryFn: ({ signal }) => api.get<AccountsResponse>("/accounts", { month }, signal),
    staleTime: 30_000,
  });
}

export function useSyncAccount() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (vars: { accountId: string; days?: number }) =>
      api.post<AccountSyncResponse>(accountPath(vars.accountId, "/sync"), {
        days: vars.days ?? 365,
      }),
    onSuccess: () => invalidateAccountSurfaces(queryClient),
  });
}

export function useAccountCredentials() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (accountId: string) =>
      api.post<AccountCredentialsResponse>(accountPath(accountId, "/credentials")),
    onSuccess: () => invalidateAccountSurfaces(queryClient),
  });
}

export function useDeleteAccount() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (accountId: string) => api.del<AccountDeleteResponse>(accountPath(accountId)),
    onSuccess: () => invalidateAccountSurfaces(queryClient),
  });
}

export function useReorderAccounts() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (order: string[]) => api.patch<{ updated: number }>("/accounts/sort", { order }),
    onSuccess: () => invalidateAccountSurfaces(queryClient),
  });
}
