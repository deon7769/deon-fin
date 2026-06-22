"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { chartRows, type SimulationResponse } from "@/lib/simulacoes";

function axisLabel(value: number): string {
  if (Math.abs(value) >= 1000) {
    return `${(value / 1000).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} mil`;
  }
  return value.toLocaleString("pt-BR");
}

export function SimulationLineChart({ result }: { result: SimulationResponse }) {
  const data = chartRows(result);
  if (!data.length) {
    return null;
  }

  return (
    <div className="h-[260px] min-h-[260px] min-w-[220px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 12, left: -4, bottom: 0 }}>
          <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="mes"
            axisLine={false}
            tickLine={false}
            tick={{ fill: "var(--color-muted)", fontSize: 12 }}
          />
          <YAxis
            width={62}
            tickFormatter={(value) => axisLabel(Number(value))}
            axisLine={false}
            tickLine={false}
            tick={{ fill: "var(--color-muted)", fontSize: 12 }}
          />
          <Tooltip cursor={{ stroke: "var(--color-border)" }} />
          <Line type="monotone" dataKey="metrica1" name="Métrica 1" stroke="var(--color-accent)" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="metrica2" name="Métrica 2" stroke="var(--color-positive)" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
