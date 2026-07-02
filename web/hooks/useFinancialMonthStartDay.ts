"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { AuthStatus } from "@/lib/auth";

type ProfileResponse = {
  financial_month_start_day?: number | null;
};

type UseFinancialMonthStartDayStateOptions = {
  enabled?: boolean;
};

export function shouldLoadFinancialMonthStartDay({
  authEnabled,
  authStatus,
}: {
  authEnabled: boolean;
  authStatus: AuthStatus;
}) {
  return !authEnabled || authStatus === "authenticated";
}

export function useFinancialMonthStartDay() {
  return useFinancialMonthStartDayState().startDay;
}

export function useFinancialMonthStartDayState(
  options: UseFinancialMonthStartDayStateOptions = {},
) {
  const enabled = options.enabled ?? true;
  const { data, isError, isFetched } = useQuery({
    queryKey: ["profile", "financial-month-start-day"],
    queryFn: ({ signal }) => api.get<ProfileResponse>("/profile", undefined, signal),
    enabled,
    retry: false,
    throwOnError: false,
    staleTime: 5 * 60_000,
  });

  const raw = Number(data?.financial_month_start_day ?? 1);
  return {
    startDay: Math.max(1, Math.min(28, Math.trunc(Number.isFinite(raw) ? raw : 1))),
    settled: !enabled || isFetched || isError,
  };
}
