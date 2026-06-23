import type { BucketPlanResponse, BucketPlanWarning, SavingsGoal } from "./types";

export type BucketPlanInput = {
  name: string;
  color: string;
  planned_kind: "percent" | "amount";
  planned_value: string | number;
};

export type BucketPlanPatch = {
  name: string;
  color: string;
  planned_kind: "percent" | "amount";
  planned_value: number;
};

export type SumBadgeState = {
  tone: "ok" | "warning";
  label: string;
};

export type BucketAllocationStatus = {
  state: "valid" | "under" | "over";
  message: string;
  canSave: boolean;
};

export function plannedKindLabel(kind: "percent" | "amount"): string {
  return kind === "percent" ? "Percentual" : "Valor fixo";
}

function formatPercentNumber(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(2).replace(/0+$/, "").replace(/\.$/, "");
}

export function sumBadgeState(input: Pick<BucketPlanResponse, "sum_percent"> & {
  warning: BucketPlanWarning | null;
}): SumBadgeState {
  return {
    tone: input.warning ? "warning" : "ok",
    label: `${formatPercentNumber(input.sum_percent)}% planejado`,
  };
}

export function sumBucketAllocationDraft(draft: Record<string | number, number>): number {
  const total = Object.values(draft).reduce((sum, value) => {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? sum + parsed : sum;
  }, 0);
  return Math.round(total * 100) / 100;
}

export function bucketAllocationStatus(total: number): BucketAllocationStatus {
  const rounded = Math.round(Number(total) * 100) / 100;
  if (Math.abs(rounded - 100) < 0.001) {
    return { state: "valid", message: "100% alocado", canSave: true };
  }
  if (rounded < 100) {
    return {
      state: "under",
      message: `Faltam ${formatPercentNumber(100 - rounded)}% para 100%`,
      canSave: false,
    };
  }
  return {
    state: "over",
    message: `Excedeu ${formatPercentNumber(rounded - 100)}% do total`,
    canSave: false,
  };
}

export function goalViabilityLabel(goal: Pick<SavingsGoal, "fits_surplus" | "monthly_required">): string {
  if (goal.monthly_required <= 0) {
    return "Concluída";
  }
  return goal.fits_surplus ? "Cabe na sobra" : "Ajustar prazo";
}

function parseMoneyInput(value: string | number): number {
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : 0;
  }
  const trimmed = value.trim();
  const normalized = trimmed.includes(",")
    ? trimmed.replace(/\./g, "").replace(",", ".")
    : trimmed;
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : 0;
}

export function toBucketPlanPatch(input: BucketPlanInput): BucketPlanPatch {
  return {
    name: input.name.trim().replace(/\s+/g, " "),
    color: input.color.trim(),
    planned_kind: input.planned_kind,
    planned_value: Math.round(parseMoneyInput(input.planned_value) * 100) / 100,
  };
}
