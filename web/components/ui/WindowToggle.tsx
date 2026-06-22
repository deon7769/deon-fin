"use client";

import { cn } from "@/lib/cn";
import type { PainelHistoryWindow } from "@/lib/types";

const OPTIONS: Array<{ value: PainelHistoryWindow; label: string }> = [
  { value: "3m", label: "3M" },
  { value: "6m", label: "6M" },
  { value: "1a", label: "1A" },
];

type WindowToggleProps = {
  value: PainelHistoryWindow;
  onChange: (value: PainelHistoryWindow) => void;
};

export function WindowToggle({ value, onChange }: WindowToggleProps) {
  return (
    <div className="inline-grid grid-cols-3 rounded-md border border-border bg-bg p-0.5" role="group" aria-label="Janela do histórico">
      {OPTIONS.map((option) => {
        const active = value === option.value;
        return (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
            aria-pressed={active}
            className={cn(
              "h-8 min-w-10 rounded-md px-2 text-xs font-semibold transition",
              active ? "bg-accent text-accentFg" : "text-muted hover:bg-surface2 hover:text-text",
            )}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
