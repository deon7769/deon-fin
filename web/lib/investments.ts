import { api } from "@/lib/api";
import type { InvestmentsResponse } from "@/lib/types";

export function getInvestments(includeInactive = false, signal?: AbortSignal) {
  return api.get<InvestmentsResponse>(
    "/investments",
    includeInactive ? { include_inactive: true } : undefined,
    signal,
  );
}
