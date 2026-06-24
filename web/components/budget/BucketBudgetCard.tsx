"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { MoneyText } from "@/components/ui/MoneyText";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { cn } from "@/lib/cn";
import { formatBudgetPercent } from "@/lib/format";
import type { BudgetCategory } from "@/lib/types";

type BucketBudgetCardProps = {
  category: BudgetCategory;
  month: string;
};

export function BucketBudgetCard({ category, month }: BucketBudgetCardProps) {
  const progress = category.used_pct ?? (category.exceeded ? 100 : 0);
  const status = category.exceeded
    ? "Excedido"
    : category.tx_count === 0
      ? "Sem gastos"
      : formatBudgetPercent(category.used_pct);
  const href = `/transacoes?month=${month}&bucket_ids=${category.id}&type=expense`;

  return (
    <article className="rounded-card border border-border bg-bg p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex min-w-0 items-center gap-2">
            <span
              aria-hidden
              className="h-2.5 w-2.5 shrink-0 rounded-full border border-border"
              style={{ backgroundColor: category.color ?? "transparent" }}
            />
            <h3 className="truncate text-sm font-semibold text-text">{category.name}</h3>
          </div>
          <p
            className={cn(
              "mt-1 text-xs font-medium",
              category.exceeded ? "text-negative" : "text-muted",
            )}
          >
            {status}
          </p>
        </div>
        <Link
          href={href}
          aria-label={`Ver transações de ${category.name}`}
          title={`Ver transações de ${category.name}`}
          className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-muted transition hover:bg-surface2 hover:text-text"
        >
          <ArrowRight size={15} aria-hidden />
        </Link>
      </div>

      <div className="mt-4 space-y-3">
        <ProgressBar
          value={progress}
          color={category.exceeded ? "var(--color-negative)" : (category.color ?? undefined)}
        />
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <p className="text-xs text-muted">Gasto</p>
            <p className="mt-1 font-semibold text-text">
              <MoneyText value={category.spent} />
            </p>
          </div>
          <div>
            <p className="text-xs text-muted">Previsto</p>
            <p className="mt-1 font-semibold text-text">
              <MoneyText value={category.planned} />
            </p>
          </div>
        </div>
        <p
          className={cn(
            "text-xs",
            category.remaining < 0 ? "text-negative" : "text-muted",
          )}
        >
          <MoneyText value={category.remaining} colorBySign="auto" /> restante
        </p>
      </div>
    </article>
  );
}
