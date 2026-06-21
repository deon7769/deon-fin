import { MoneyText } from "@/components/ui/MoneyText";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { formatBudgetPercent } from "@/lib/format";

type RealizedBarProps = {
  color: string | null;
  planned: number;
  spent: number;
};

export function RealizedBar({ color, planned, spent }: RealizedBarProps) {
  const pct = planned > 0 ? Math.round((spent / planned) * 10000) / 100 : 0;

  return (
    <div className="min-w-[160px] space-y-2">
      <div className="flex items-center justify-between gap-2 text-xs">
        <span className="text-muted">Realizado</span>
        <span className={spent > planned && planned > 0 ? "text-negative" : "text-muted"}>
          {formatBudgetPercent(pct)}
        </span>
      </div>
      <ProgressBar
        value={pct}
        color={spent > planned && planned > 0 ? "var(--color-negative)" : (color ?? undefined)}
      />
      <p className="text-xs text-muted">
        <MoneyText value={spent} /> de <MoneyText value={planned} />
      </p>
    </div>
  );
}
