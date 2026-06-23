"use client";

import type { SavingsGoal } from "@/lib/types";

type SavingsGoalSelectProps = {
  value?: number | null;
  options: SavingsGoal[];
  onChange: (goalId: number | null) => void;
  disabled?: boolean;
  loading?: boolean;
  emptyLabel?: string;
};

export function SavingsGoalSelect({
  value = null,
  options,
  onChange,
  disabled = false,
  loading = false,
  emptyLabel = "Sem meta de poupança",
}: SavingsGoalSelectProps) {
  return (
    <select
      value={value ?? ""}
      disabled={disabled || loading}
      onChange={(event) => {
        const nextValue = event.target.value;
        onChange(nextValue ? Number(nextValue) : null);
      }}
      aria-label="Meta de poupança"
      className="h-9 w-full min-w-[176px] rounded-md border border-border bg-surface2 px-2 text-sm text-text outline-none transition hover:bg-surface disabled:cursor-not-allowed disabled:opacity-60"
    >
      <option value="">{loading ? "Carregando..." : emptyLabel}</option>
      {options.map((goal) => (
        <option key={goal.id} value={goal.id}>
          {goal.name}
        </option>
      ))}
    </select>
  );
}
