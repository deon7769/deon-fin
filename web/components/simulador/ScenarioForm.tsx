"use client";

import { Building2, Car, Play } from "lucide-react";
import { SCENARIO_PRESETS, type ScenarioPresetKey } from "@/lib/simulator";
import type { ScenarioSimulationRequest } from "@/lib/types";

type ScenarioFormProps = {
  value: ScenarioSimulationRequest;
  validationMessage?: string | null;
  loading?: boolean;
  onChange: (value: ScenarioSimulationRequest) => void;
  onPreset: (preset: ScenarioPresetKey) => void;
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

export function ScenarioForm({
  value,
  validationMessage,
  loading,
  onChange,
  onPreset,
  onSubmit,
}: ScenarioFormProps) {
  const setField = (field: keyof ScenarioSimulationRequest) => (next: number) => {
    onChange({ ...value, [field]: field === "prazo_meses" ? Math.round(next) : next });
  };

  return (
    <form
      className="space-y-5"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => onPreset("carro")}
          className="inline-flex h-9 items-center gap-2 rounded-md border border-border px-3 text-sm font-medium text-text transition hover:bg-surface2"
          title={`Preço padrão ${SCENARIO_PRESETS.carro.preco}`}
        >
          <Car size={16} aria-hidden />
          Carro
        </button>
        <button
          type="button"
          onClick={() => onPreset("imovel")}
          className="inline-flex h-9 items-center gap-2 rounded-md border border-border px-3 text-sm font-medium text-text transition hover:bg-surface2"
          title={`Preço padrão ${SCENARIO_PRESETS.imovel.preco}`}
        >
          <Building2 size={16} aria-hidden />
          Imóvel
        </button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <NumberField label="Preço (R$)" value={value.preco} onChange={setField("preco")} />
        <NumberField label="Entrada (R$)" value={value.entrada} onChange={setField("entrada")} />
        <NumberField
          label="Prazo (meses)"
          value={value.prazo_meses}
          min={1}
          step={1}
          onChange={setField("prazo_meses")}
        />
        <NumberField label="Juros (% a.a.)" value={value.juros_aa} onChange={setField("juros_aa")} />
        <NumberField
          label="Sobra mensal (R$)"
          value={value.sobra_mensal}
          onChange={setField("sobra_mensal")}
        />
        <NumberField
          label="Rendimento (% a.a.)"
          value={value.rendimento_aa}
          onChange={setField("rendimento_aa")}
        />
        <NumberField
          label="Taxa adm. consórcio (%)"
          value={value.taxa_adm_consorcio}
          onChange={setField("taxa_adm_consorcio")}
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
        {loading ? "Calculando..." : "Simular cenário"}
      </button>
    </form>
  );
}
