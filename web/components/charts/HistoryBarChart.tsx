"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipContentProps,
} from "recharts";
import { formatMonthShort } from "@/lib/format";
import type { PainelHistoryPoint } from "@/lib/types";
import { useMoneyFormatter } from "@/hooks/useMoneyFormatter";

type HistoryBarChartProps = {
  data: PainelHistoryPoint[];
};

function yAxisLabel(value: number): string {
  if (Math.abs(value) >= 1000) {
    return `${(value / 1000).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} mil`;
  }
  return value.toLocaleString("pt-BR");
}

function tooltipNumber(value: unknown): number {
  const raw = Array.isArray(value) ? value[0] : value;
  const parsed = Number(raw ?? 0);
  return Number.isFinite(parsed) ? parsed : 0;
}

function HistoryTooltip({ active, payload, label }: TooltipContentProps) {
  const money = useMoneyFormatter();
  if (!active || !payload?.length) {
    return null;
  }

  return (
    <div className="rounded-md border border-border bg-surface px-3 py-2 shadow-xl">
      <p className="mb-2 text-xs font-semibold uppercase text-muted">{formatMonthShort(String(label))}</p>
      <div className="space-y-1">
        {payload.map((entry) => (
          <div
            key={`${entry.name ?? "entry"}:${String(entry.dataKey ?? "")}`}
            className="flex min-w-36 items-center justify-between gap-4 text-xs"
          >
            <span className="inline-flex items-center gap-2 text-muted">
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: entry.color }} />
              {entry.name}
            </span>
            <span className="font-semibold tabular-nums text-text">{money(tooltipNumber(entry.value))}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function HistoryBarChart({ data }: HistoryBarChartProps) {
  return (
    <div className="space-y-3">
      <div className="h-[280px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 10, left: -8, bottom: 0 }} barGap={6}>
            <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="month"
              tickFormatter={formatMonthShort}
              axisLine={false}
              tickLine={false}
              tick={{ fill: "var(--color-muted)", fontSize: 12 }}
            />
            <YAxis
              width={58}
              tickFormatter={(value) => yAxisLabel(Number(value))}
              axisLine={false}
              tickLine={false}
              tick={{ fill: "var(--color-muted)", fontSize: 12 }}
            />
            <Tooltip
              cursor={{ fill: "rgba(255,255,255,0.04)" }}
              content={(props) => <HistoryTooltip {...props} />}
            />
            <Bar dataKey="income" name="Entrada" fill="var(--color-positive)" radius={[4, 4, 0, 0]} />
            <Bar dataKey="expense" name="Saída" fill="var(--color-negative)" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="flex items-center gap-4 text-xs text-muted">
        <span className="inline-flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-positive" />
          Entrada
        </span>
        <span className="inline-flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-negative" />
          Saída
        </span>
      </div>
    </div>
  );
}
