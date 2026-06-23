"use client";

import { useEffect, useMemo, useState } from "react";
import { RotateCcw, Save } from "lucide-react";
import { MoneyText } from "@/components/ui/MoneyText";
import { SectionCard } from "@/components/ui/SectionCard";
import { cn } from "@/lib/cn";
import {
  bucketAllocationStatus,
  sumBucketAllocationDraft,
  type BucketPlanPatch,
} from "@/lib/metas";
import type { BucketPlanItem } from "@/lib/types";

type BucketAllocationUpdate = {
  id: number;
  input: BucketPlanPatch;
};

type BucketAllocationPanelProps = {
  buckets: BucketPlanItem[];
  income: number;
  saving?: boolean;
  error?: string | null;
  onSave: (updates: BucketAllocationUpdate[]) => void | Promise<void>;
};

function formatPct(value: number): string {
  return Number(value.toFixed(2)).toString();
}

function bucketColor(bucket: BucketPlanItem): string {
  return bucket.color ?? "#F5B301";
}

function initialDraft(buckets: BucketPlanItem[], income: number): Record<number, number> {
  return Object.fromEntries(
    buckets.map((bucket) => {
      const pct =
        bucket.planned_kind === "percent"
          ? bucket.planned_value
          : income > 0
            ? (bucket.planned_amount / income) * 100
            : 0;
      return [bucket.id, Math.round(pct * 100) / 100];
    }),
  );
}

function donutBackground(buckets: BucketPlanItem[], draft: Record<number, number>): string {
  let cursor = 0;
  const segments: string[] = [];

  for (const bucket of buckets) {
    const value = Math.max(0, Number(draft[bucket.id] ?? 0));
    if (value <= 0 || cursor >= 100) {
      continue;
    }
    const next = Math.min(100, cursor + value);
    segments.push(`${bucketColor(bucket)} ${cursor}% ${next}%`);
    cursor = next;
  }

  if (cursor < 100) {
    segments.push(`#27272a ${cursor}% 100%`);
  }

  return `conic-gradient(${segments.join(", ")})`;
}

export function BucketAllocationPanel({
  buckets,
  income,
  saving = false,
  error = null,
  onSave,
}: BucketAllocationPanelProps) {
  const [draft, setDraft] = useState<Record<number, number>>(() => initialDraft(buckets, income));
  const draftKey = useMemo(
    () =>
      `${income}:${buckets
        .map((bucket) => `${bucket.id}:${bucket.planned_kind}:${bucket.planned_value}:${bucket.planned_amount}`)
        .join("|")}`,
    [buckets, income],
  );

  const total = useMemo(() => sumBucketAllocationDraft(draft), [draft]);
  const status = bucketAllocationStatus(total);
  const background = donutBackground(buckets, draft);

  useEffect(() => {
    setDraft(initialDraft(buckets, income));
  }, [draftKey, buckets, income]);

  const setTarget = (bucketId: number, value: number) => {
    const parsed = Number.isFinite(value) ? value : 0;
    const clamped = Math.max(0, Math.min(100, parsed));
    setDraft((current) => ({ ...current, [bucketId]: clamped }));
  };

  const reset = () => {
    setDraft(initialDraft(buckets, income));
  };

  const save = () => {
    const updates = buckets.map((bucket) => ({
      id: bucket.id,
      input: {
        name: bucket.name,
        color: bucketColor(bucket),
        planned_kind: "percent" as const,
        planned_value: Math.round(Number(draft[bucket.id] ?? 0) * 100) / 100,
      },
    }));
    return onSave(updates);
  };

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(300px,0.9fr)_1.7fr]">
      <SectionCard title="Visualização de uso">
        <div className="flex justify-center py-4">
          <div
            className="flex h-56 w-56 items-center justify-center rounded-full p-9"
            style={{ background }}
            aria-label={`Total: ${formatPct(total)}%`}
          >
            <div className="flex h-full w-full flex-col items-center justify-center rounded-full bg-surface text-center">
              <span className="text-3xl font-semibold text-text">Total: {formatPct(total)}%</span>
              <span
                className={cn(
                  "mt-1 text-xs font-medium",
                  status.state === "valid" && "text-positive",
                  status.state === "under" && "text-amber-200",
                  status.state === "over" && "text-negative",
                )}
              >
                {status.message}
              </span>
            </div>
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          {buckets.map((bucket) => {
            const value = Number(draft[bucket.id] ?? 0);
            return (
              <div key={bucket.id} className="flex min-w-0 items-center gap-2 text-sm">
                <span
                  aria-hidden
                  className="h-3 w-3 shrink-0 rounded-full"
                  style={{ backgroundColor: bucketColor(bucket) }}
                />
                <span className="truncate font-medium text-text">{bucket.name}</span>
                <span className="shrink-0 text-muted">({formatPct(value)}%)</span>
              </div>
            );
          })}
        </div>
      </SectionCard>

      <SectionCard
        title="Controle de Metas"
        subtitle="Ajuste as barras para distribuir 100% da renda planejada."
      >
        <div className="space-y-5">
          {buckets.map((bucket) => {
            const value = Number(draft[bucket.id] ?? 0);
            const planned = income > 0 ? (income * value) / 100 : bucket.planned_amount;
            return (
              <label key={bucket.id} className="grid gap-2 md:grid-cols-[190px_1fr_86px] md:items-center">
                <span className="min-w-0 text-sm font-semibold text-text">{bucket.name}</span>
                <input
                  type="range"
                  min={0}
                  max={100}
                  step={1}
                  value={value}
                  onChange={(event) => setTarget(bucket.id, Number(event.target.value))}
                  className="h-2 w-full accent-[var(--color-accent)]"
                  style={{ accentColor: bucketColor(bucket) }}
                  aria-label={`Percentual de ${bucket.name}`}
                />
                <span className="grid grid-cols-[1fr_auto] items-center overflow-hidden rounded-md border border-border bg-bg">
                  <input
                    type="number"
                    min={0}
                    max={100}
                    step={1}
                    value={value}
                    onChange={(event) => setTarget(bucket.id, Number(event.target.value))}
                    className="h-9 min-w-0 bg-transparent px-2 text-right text-sm font-semibold text-text outline-none"
                    aria-label={`Valor percentual de ${bucket.name}`}
                  />
                  <span className="pr-2 text-xs text-muted">%</span>
                </span>
                <span className="text-xs text-muted md:col-start-2">
                  <MoneyText value={planned} /> planejado
                </span>
              </label>
            );
          })}
        </div>

        <div className="mt-5 border-t border-border pt-4">
          <div className="flex items-center justify-between gap-3 text-sm">
            <span className="text-muted">Alocado</span>
            <span
              className={cn(
                "font-semibold",
                status.state === "valid" && "text-positive",
                status.state === "under" && "text-amber-200",
                status.state === "over" && "text-negative",
              )}
            >
              {formatPct(total)}% / 100%
            </span>
          </div>
          <p
            className={cn(
              "mt-2 text-xs",
              status.state === "valid" && "text-positive",
              status.state === "under" && "text-amber-200",
              status.state === "over" && "text-negative",
            )}
          >
            {status.message}
          </p>
        </div>

        {error ? <p className="mt-4 text-sm text-negative">{error}</p> : null}

        <div className="mt-5 flex flex-col gap-2 sm:flex-row sm:justify-end">
          <button
            type="button"
            onClick={reset}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-border px-3 text-sm font-medium text-muted transition hover:bg-surface2 hover:text-text"
          >
            <RotateCcw size={16} aria-hidden />
            Resetar valores
          </button>
          <button
            type="button"
            onClick={() => void save()}
            disabled={!status.canSave || saving}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-accent px-4 text-sm font-semibold text-accentFg transition hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Save size={16} aria-hidden />
            {saving ? "Salvando..." : "Salvar metas"}
          </button>
        </div>
      </SectionCard>
    </div>
  );
}
