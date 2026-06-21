"use client";

import { cn } from "@/lib/cn";
import type { PainelTagType } from "@/lib/types";

const OPTIONS: Array<{ value: PainelTagType; label: string }> = [
  { value: "expense", label: "Despesas" },
  { value: "income", label: "Receitas" },
];

type TypeToggleProps = {
  value: PainelTagType;
  onChange: (value: PainelTagType) => void;
};

export function TypeToggle({ value, onChange }: TypeToggleProps) {
  return (
    <div className="inline-grid grid-cols-2 rounded-md border border-border bg-bg p-0.5" role="group" aria-label="Tipo de transação">
      {OPTIONS.map((option) => {
        const active = value === option.value;
        return (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
            aria-pressed={active}
            className={cn(
              "h-8 min-w-20 rounded-md px-3 text-xs font-semibold transition",
              active ? "bg-accent text-black" : "text-muted hover:bg-surface2 hover:text-text",
            )}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
