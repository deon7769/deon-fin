import { api } from "@/lib/api";
import type { InvestmentRefreshQuotesResponse, InvestmentsResponse } from "@/lib/types";

export function getInvestments(includeInactive = false, signal?: AbortSignal) {
  return api.get<InvestmentsResponse>(
    "/investments",
    includeInactive ? { include_inactive: true } : undefined,
    signal,
  );
}

export function refreshInvestmentQuotes() {
  return api.post<InvestmentRefreshQuotesResponse>("/investments/refresh-quotes");
}
