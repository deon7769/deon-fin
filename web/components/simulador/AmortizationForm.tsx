"use client";

import { Home, Play } from "lucide-react";
import type { AmortizationRequest } from "@/lib/types";

type AmortizationFormProps = {
  value: AmortizationRequest;
  validationMessage?: string | null;
  loading?: boolean;
  canLoadProperty?: boolean;
  loadingProperty?: boolean;
  onChange: (value: AmortizationRequest) => void;
  onLoadProperty: () => void;
  onSubmit: () => void;
};

type NumberFieldProps = {
  label: string;
  value: number;
  min?: number;
  step?: number;
  onChange: (value: number) => void;
};

function parseNumber(value: string): number {
  if (value.trim() === "") {
    return 0;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function NumberField({ label, value, min = 0, step = 0.01, onChange }: NumberFieldProps) {
  return (
    <label className="space-y-1.5 text-sm">
      <span className="font-medium text-text">{label}</span>
      <input
        type="number"
        min={min}
        step={step}
        value={value}
        onChange={(event) => onChange(parseNumber(event.currentTarget.value))}
        className="h-10 w-full rounded-md border border-border bg-surface px-3 text-sm text-text outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/20"
      />
    </label>
  );
}

export function AmortizationForm({
  value,
  validationMessage,
  loading,
  canLoadProperty,
  loadingProperty,
  onChange,
  onLoadProperty,
  onSubmit,
}: AmortizationFormProps) {
  const setField = (field: keyof AmortizationRequest) => (next: number) => {
    onChange({ ...value, [field]: next });
  };

  return (
    <form
      className="space-y-5"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <button
        type="button"
        onClick={onLoadProperty}
        disabled={!canLoadProperty || loadingProperty}
        className="inline-flex h-9 items-center gap-2 rounded-md border border-border px-3 text-sm font-medium text-text transition hover:bg-surface2 disabled:cursor-not-allowed disabled:opacity-55"
      >
        <Home size={16} aria-hidden />
        {loadingProperty ? "Carregando..." : "Carregar do imóvel"}
      </button>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <NumberField label="Saldo devedor (R$)" value={value.saldo} onChange={setField("saldo")} />
        <NumberField label="Juros (% a.a.)" value={value.juros_aa} onChange={setField("juros_aa")} />
        <NumberField label="Parcela atual (R$)" value={value.parcela} onChange={setField("parcela")} />
        <NumberField
          label="Aporte extra/mês (R$)"
          value={value.aporte_extra}
          onChange={setField("aporte_extra")}
        />
      </div>

      {validationMessage ? (
        <p className="rounded-md border border-negative/25 bg-negative/10 px-3 py-2 text-sm text-negative">
          {validationMessage}
        </p>
      ) : null}

      <button
        type="submit"
        disabled={loading}
        className="inline-flex h-10 items-center gap-2 rounded-md bg-accent px-4 text-sm font-semibold text-white transition hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-60"
      >
        <Play size={16} aria-hidden />
        {loading ? "Calculando..." : "Simular amortização"}
      </button>
    </form>
  );
}
