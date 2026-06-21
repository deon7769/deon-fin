const SYNC_LABELS: Record<string, string> = {
  UPDATED: "Sincronizado",
  OUTDATED: "Desatualizado",
  LOGIN_ERROR: "Erro de login",
  DISCONNECTED: "Desconectado",
  DERIVED: "Saldo estimado",
  UNKNOWN: "Indisponível",
};

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
