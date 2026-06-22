"use client";

import { useState } from "react";
import { ArrowDown, ArrowUp, Save } from "lucide-react";
import { MoneyText } from "@/components/ui/MoneyText";
import { RealizedBar } from "@/components/metas/RealizedBar";
import { plannedKindLabel, toBucketPlanPatch, type BucketPlanPatch } from "@/lib/metas";
import type { BucketPlanItem } from "@/lib/types";

type BucketPlanRowProps = {
  bucket: BucketPlanItem;
  first: boolean;
  last: boolean;
  saving?: boolean;
  moving?: boolean;
  onMove: (direction: -1 | 1) => void;
  onSave: (bucketId: number, input: BucketPlanPatch) => Promise<void>;
};

export function BucketPlanRow({
  bucket,
  first,
  last,
  saving = false,
  moving = false,
  onMove,
  onSave,
}: BucketPlanRowProps) {
  const [name, setName] = useState(bucket.name);
  const [color, setColor] = useState(bucket.color ?? "#F5B301");
  const [kind, setKind] = useState<"percent" | "amount">(bucket.planned_kind);
  const [value, setValue] = useState(String(bucket.planned_value));
  const [error, setError] = useState<string | null>(null);

  const handleSave = async () => {
    try {
      setError(null);
      await onSave(
        bucket.id,
        toBucketPlanPatch({
          name,
          color,
          planned_kind: kind,
          planned_value: value,
        }),
      );
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Erro ao salvar");
    }
  };

  return (
    <div className="grid gap-3 border-b border-border py-4 last:border-b-0 xl:grid-cols-[minmax(160px,1.1fr)_150px_130px_90px_minmax(170px,1fr)_120px] xl:items-center">
      <label className="min-w-0 space-y-1">
        <span className="text-xs font-medium text-muted">Meta</span>
        <input
          value={name}
          onChange={(event) => setName(event.target.value)}
          className="h-10 w-full rounded-md border border-border bg-bg px-3 text-sm font-medium text-text outline-none focus:border-accent"
        />
      </label>

      <label className="space-y-1">
        <span className="text-xs font-medium text-muted">Modo</span>
        <select
          value={kind}
          onChange={(event) => setKind(event.target.value as "percent" | "amount")}
          className="h-10 w-full rounded-md border border-border bg-bg px-3 text-sm text-text outline-none focus:border-accent"
        >
          <option value="percent">{plannedKindLabel("percent")}</option>
          <option value="amount">{plannedKindLabel("amount")}</option>
        </select>
      </label>

      <label className="space-y-1">
        <span className="text-xs font-medium text-muted">Planejado</span>
        <div className="flex h-10 overflow-hidden rounded-md border border-border bg-bg focus-within:border-accent">
          <input
            value={value}
            onChange={(event) => setValue(event.target.value)}
            inputMode="decimal"
            className="min-w-0 flex-1 bg-transparent px-3 text-sm text-text outline-none"
          />
          <span className="inline-flex w-10 items-center justify-center border-l border-border text-xs text-muted">
            {kind === "percent" ? "%" : "R$"}
          </span>
        </div>
      </label>

      <label className="space-y-1">
        <span className="text-xs font-medium text-muted">Cor</span>
        <input
          type="color"
          value={color}
          onChange={(event) => setColor(event.target.value)}
          aria-label={`Cor de ${bucket.name}`}
          className="h-10 w-full rounded-md border border-border bg-bg px-2 py-1"
        />
      </label>

      <RealizedBar color={color} planned={bucket.planned_amount} spent={bucket.spent_month} />

      <div className="flex items-center justify-between gap-2 xl:justify-end">
        <div className="text-sm font-semibold text-text xl:hidden">
          <MoneyText value={bucket.planned_amount} />
        </div>
        <div className="flex gap-1">
          <button
            type="button"
            onClick={() => onMove(-1)}
            disabled={first || moving}
            aria-label={`Mover ${bucket.name} para cima`}
            title="Mover para cima"
            className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-border text-muted transition hover:bg-surface2 hover:text-text disabled:cursor-not-allowed disabled:opacity-40"
          >
            <ArrowUp size={15} aria-hidden />
          </button>
          <button
            type="button"
            onClick={() => onMove(1)}
            disabled={last || moving}
            aria-label={`Mover ${bucket.name} para baixo`}
            title="Mover para baixo"
            className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-border text-muted transition hover:bg-surface2 hover:text-text disabled:cursor-not-allowed disabled:opacity-40"
          >
            <ArrowDown size={15} aria-hidden />
          </button>
          <button
            type="button"
            onClick={() => void handleSave()}
            disabled={saving}
            aria-label={`Salvar ${bucket.name}`}
            title="Salvar"
            className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-accent text-accentFg transition hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Save size={15} aria-hidden />
          </button>
        </div>
      </div>

      {error ? <p className="text-xs text-negative xl:col-span-6">{error}</p> : null}
    </div>
  );
}
