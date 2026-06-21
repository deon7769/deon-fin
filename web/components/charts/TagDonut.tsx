"use client";

import {
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  type TooltipContentProps,
} from "recharts";
import type { PainelTagSlice } from "@/lib/types";
import { useMoneyFormatter } from "@/hooks/useMoneyFormatter";

type TagDonutProps = {
  items: PainelTagSlice[];
  total: number;
};

function TagTooltip({ active, payload }: TooltipContentProps) {
  const money = useMoneyFormatter();
  if (!active || !payload?.length) {
    return null;
  }

  const slice = payload[0]?.payload as PainelTagSlice | undefined;
  if (!slice) {
    return null;
  }

  return (
    <div className="rounded-md border border-border bg-surface px-3 py-2 shadow-xl">
      <p className="text-xs font-semibold text-text">{slice.tag_name}</p>
      <p className="mt-1 text-xs tabular-nums text-muted">{money(slice.total)}</p>
    </div>
  );
}

export function TagDonut({ items, total }: TagDonutProps) {
  const money = useMoneyFormatter();

  return (
    <div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(0,260px)_minmax(0,1fr)] lg:items-center">
      <div className="relative h-[260px] min-h-[260px] min-w-[220px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={items}
              dataKey="total"
              nameKey="tag_name"
              innerRadius={68}
              outerRadius={102}
              paddingAngle={2}
              stroke="var(--color-surface)"
              strokeWidth={2}
            >
              {items.map((slice) => (
                <Cell
                  key={`${slice.tag_id ?? "none"}:${slice.tag_name}`}
                  fill={slice.color ?? "var(--color-muted)"}
                />
              ))}
            </Pie>
            <Tooltip content={(props) => <TagTooltip {...props} />} />
          </PieChart>
        </ResponsiveContainer>

        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">
          <span className="text-xs font-medium uppercase text-muted">Total</span>
          <span className="mt-1 text-lg font-semibold tabular-nums text-text">{money(total)}</span>
        </div>
      </div>

      <div className="space-y-2">
        {items.map((slice) => (
          <div
            key={`${slice.tag_id ?? "none"}:${slice.tag_name}:legend`}
            className="flex items-center justify-between gap-3 rounded-md bg-bg px-3 py-2"
          >
            <span className="inline-flex min-w-0 items-center gap-2 text-sm text-text">
              <span
                className="h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ backgroundColor: slice.color ?? "var(--color-muted)" }}
              />
              <span className="truncate">{slice.tag_name}</span>
            </span>
            <span className="shrink-0 text-sm font-semibold tabular-nums text-text">{money(slice.total)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
