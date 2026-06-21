import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

type KpiCardProps = {
  title: string;
  value: ReactNode;
  subtitle?: string;
  icon?: ReactNode;
  tone?: "default" | "positive" | "negative" | "accent";
};

const toneClasses = {
  default: "text-text",
  positive: "text-positive",
  negative: "text-negative",
  accent: "text-accent",
};

export function KpiCard({ title, value, subtitle, icon, tone = "default" }: KpiCardProps) {
  return (
    <section className="rounded-card border border-border bg-surface p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm text-muted">{title}</p>
          <div className={cn("mt-2 text-2xl font-semibold", toneClasses[tone])}>{value}</div>
        </div>
        {icon ? <div className="rounded-md bg-surface2 p-2 text-muted">{icon}</div> : null}
      </div>
      {subtitle ? <p className="mt-3 text-xs text-muted">{subtitle}</p> : null}
    </section>
  );
}
