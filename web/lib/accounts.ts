const SYNC_LABELS: Record<string, string> = {
  UPDATED: "Sincronizado",
  OUTDATED: "Desatualizado",
  LOGIN_ERROR: "Erro de login",
  DISCONNECTED: "Desconectado",
  DERIVED: "Saldo estimado",
  UNKNOWN: "Indisponível",
};

type AccountsSyncLike = {
  sync?: {
    running?: boolean;
  };
};

function normalizeSyncTimestamp(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) {
    return trimmed;
  }
  if (/[zZ]|[+-]\d{2}:?\d{2}$/.test(trimmed)) {
    return trimmed;
  }
  return `${trimmed.replace(" ", "T")}Z`;
}

export function formatSyncDateTime(value?: string | null): string | null {
  if (!value) {
    return null;
  }
  const date = new Date(normalizeSyncTimestamp(value));
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "America/Sao_Paulo",
  }).format(date);
}

export function accountsRefetchInterval(data: AccountsSyncLike | null | undefined): number | false {
  return data?.sync?.running ? 2000 : false;
}

export function usageLabel(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "--";
  }
  return `${value.toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}%`;
}

export function syncStatusLabel(status: string | null | undefined): string {
  if (!status) {
    return SYNC_LABELS.UNKNOWN;
  }
  return SYNC_LABELS[status] ?? status;
}

export function syncStatusTone(status: string | null | undefined): "positive" | "negative" | "accent" | "muted" {
  if (status === "UPDATED") {
    return "positive";
  }
  if (status === "LOGIN_ERROR") {
    return "negative";
  }
  if (status === "OUTDATED") {
    return "accent";
  }
  return "muted";
}

export function bankAccountLine(agency?: string | null, number?: string | null): string {
  const parts = [agency, number].filter(Boolean);
  return parts.length ? parts.join(" - ") : "--";
}

type AccountPluggyRef = {
  id: string;
  pluggy_item_id?: string | null;
};

export function pluggyItemIdForAccount(
  banks: readonly AccountPluggyRef[],
  cards: readonly AccountPluggyRef[],
  accountId: string,
): string | null {
  const account = [...banks, ...cards].find((item) => item.id === accountId);
  return account?.pluggy_item_id || null;
}
