"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

type ProfileResponse = {
  financial_month_start_day?: number | null;
};

export function useFinancialMonthStartDay() {
  return useFinancialMonthStartDayState().startDay;
}

export function useFinancialMonthStartDayState() {
  const { data, isError, isFetched } = useQuery({
    queryKey: ["profile", "financial-month-start-day"],
    queryFn: ({ signal }) => api.get<ProfileResponse>("/profile", undefined, signal),
    retry: false,
    throwOnError: false,
    staleTime: 5 * 60_000,
  });

  const raw = Number(data?.financial_month_start_day ?? 1);
  return {
    startDay: Math.max(1, Math.min(28, Math.trunc(Number.isFinite(raw) ? raw : 1))),
    settled: isFetched || isError,
  };
}
