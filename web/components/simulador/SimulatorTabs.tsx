"use client";

import { BadgePercent, Calculator } from "lucide-react";
import { cn } from "@/lib/cn";

export type SimulatorMode = "cenario" | "amortizacao";

type SimulatorTabsProps = {
  value: SimulatorMode;
  onChange: (value: SimulatorMode) => void;
};

const tabs: Array<{ value: SimulatorMode; label: string; icon: typeof Calculator }> = [
  { value: "cenario", label: "Cenários", icon: Calculator },
  { value: "amortizacao", label: "Amortização", icon: BadgePercent },
];

export function SimulatorTabs({ value, onChange }: SimulatorTabsProps) {
  return (
    <div className="inline-grid w-full grid-cols-2 rounded-md border border-border bg-surface p-1 sm:w-auto">
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const selected = tab.value === value;
        return (
          <button
            key={tab.value}
            type="button"
            aria-pressed={selected}
            onClick={() => onChange(tab.value)}
            className={cn(
              "inline-flex h-9 items-center justify-center gap-2 rounded px-3 text-sm font-medium transition",
              selected ? "bg-accent text-white shadow-sm" : "text-muted hover:bg-surface2 hover:text-text",
            )}
          >
            <Icon size={16} aria-hidden />
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
