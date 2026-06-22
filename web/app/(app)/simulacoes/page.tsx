"use client";

import { useMemo, useState } from "react";
import { BarChart3, Calculator, RotateCcw } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";

import { SimulationResultPanel } from "@/components/simulacoes/SimulationResultPanel";
import { Header } from "@/components/layout/Header";
import { EmptyState } from "@/components/ui/EmptyState";
import { SectionCard } from "@/components/ui/SectionCard";
import { useSimulationCalculator } from "@/hooks/useSimulacoes";
import { cn } from "@/lib/cn";
import {
  CALCULATORS,
  DEFAULT_INPUTS,
  type CalculatorKey,
  type SimulationPayload,
} from "@/lib/simulacoes";

function isCalculatorKey(value: string | null): value is CalculatorKey {
  return CALCULATORS.some((calculator) => calculator.key === value);
}

function parseInputValue(value: string, previous: unknown): unknown {
  if (typeof previous === "number") {
    const normalized = value.replace(",", ".");
    const parsed = Number(normalized);
    return Number.isFinite(parsed) ? parsed : previous;
  }
  if (typeof previous === "boolean") {
    return value === "true";
  }
  if (Array.isArray(previous)) {
    try {
      return JSON.parse(value);
    } catch {
      return previous;
    }
  }
  return value;
}

function SimulationForm({
  value,
  loading,
  onChange,
  onSubmit,
  onReset,
}: {
  value: SimulationPayload;
  loading: boolean;
  onChange: (value: SimulationPayload) => void;
  onSubmit: () => void;
  onReset: () => void;
}) {
  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-2">
        {Object.entries(value).map(([key, fieldValue]) => {
          const fieldId = `sim-${key}`;
          if (typeof fieldValue === "boolean") {
            return (
              <label key={key} className="flex h-10 items-center gap-2 rounded-md border border-border px-3 text-sm text-text">
                <input
                  type="checkbox"
                  checked={fieldValue}
                  onChange={(event) => onChange({ ...value, [key]: event.target.checked })}
                  className="h-4 w-4 accent-[var(--accent)]"
                />
                {key.replaceAll("_", " ")}
              </label>
            );
          }
          if (Array.isArray(fieldValue)) {
            return (
              <label key={key} className="space-y-1 md:col-span-2" htmlFor={fieldId}>
                <span className="text-xs font-medium uppercase tracking-normal text-muted">{key.replaceAll("_", " ")}</span>
                <textarea
                  id={fieldId}
                  value={JSON.stringify(fieldValue)}
                  onChange={(event) => onChange({ ...value, [key]: parseInputValue(event.target.value, fieldValue) })}
                  className="min-h-20 w-full rounded-md border border-border bg-surface2 px-3 py-2 text-sm text-text outline-none transition focus:border-accent"
                />
              </label>
            );
          }
          return (
            <label key={key} className="space-y-1" htmlFor={fieldId}>
              <span className="text-xs font-medium uppercase tracking-normal text-muted">{key.replaceAll("_", " ")}</span>
              <input
                id={fieldId}
                type={typeof fieldValue === "number" ? "number" : "text"}
                step="any"
                value={String(fieldValue)}
                onChange={(event) => onChange({ ...value, [key]: parseInputValue(event.target.value, fieldValue) })}
                className="h-10 w-full rounded-md border border-border bg-surface2 px-3 text-sm text-text outline-none transition focus:border-accent"
              />
            </label>
          );
        })}
      </div>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={onSubmit}
          disabled={loading}
          className="inline-flex h-10 items-center gap-2 rounded-md bg-accent px-3 text-sm font-medium text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <Calculator size={16} aria-hidden />
          {loading ? "Calculando..." : "Calcular"}
        </button>
        <button
          type="button"
          onClick={onReset}
          className="inline-flex h-10 items-center gap-2 rounded-md border border-border px-3 text-sm font-medium text-text transition hover:bg-surface2"
        >
          <RotateCcw size={16} aria-hidden />
          Limpar
        </button>
      </div>
    </div>
  );
}

export default function SimulacoesPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const requestedCalculator = searchParams.get("calc");
  const initialCalculator: CalculatorKey = isCalculatorKey(requestedCalculator)
    ? requestedCalculator
    : "juros-compostos";
  const [active, setActive] = useState<CalculatorKey>(initialCalculator);
  const [inputs, setInputs] = useState<Record<CalculatorKey, SimulationPayload>>(DEFAULT_INPUTS);
  const simulation = useSimulationCalculator(active);
  const activeDefinition = useMemo(
    () => CALCULATORS.find((item) => item.key === active) ?? CALCULATORS[0],
    [active],
  );

  const updateInput = (value: SimulationPayload) => {
    setInputs((current) => ({ ...current, [active]: value }));
  };

  const reset = () => {
    updateInput(DEFAULT_INPUTS[active]);
    simulation.reset();
  };

  return (
    <>
      <Header
        title="Simulações"
        subtitle="Calculadoras financeiras para comparar cenários, taxas, renda, amortização e imóvel."
      />

      <div className="space-y-5 p-4 sm:p-6">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {CALCULATORS.map((calculator) => {
            const selected = calculator.key === active;
            return (
              <button
                key={calculator.key}
                type="button"
                onClick={() => {
                  setActive(calculator.key);
                  simulation.reset();
                  router.replace(`/simulacoes?calc=${calculator.key}`, { scroll: false });
                }}
                className={cn(
                  "rounded-card border p-4 text-left transition",
                  selected
                    ? "border-accent bg-accent/10 text-text"
                    : "border-border bg-surface text-muted hover:bg-surface2 hover:text-text",
                )}
              >
                <div className="flex items-start gap-3">
                  <BarChart3 size={18} aria-hidden className={selected ? "text-accent" : "text-muted"} />
                  <div className="min-w-0">
                    <div className="font-medium">{calculator.label}</div>
                    <div className="mt-1 text-xs text-muted">{calculator.description}</div>
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        <div className="grid gap-5 xl:grid-cols-[minmax(320px,420px)_minmax(0,1fr)]">
          <SectionCard title={activeDefinition.label} subtitle={activeDefinition.description}>
            <SimulationForm
              value={inputs[active]}
              loading={simulation.isPending}
              onChange={updateInput}
              onSubmit={() => simulation.mutate(inputs[active])}
              onReset={reset}
            />
          </SectionCard>

          <SectionCard title="Resultado" subtitle="Cards principais e série quando a calculadora retorna histórico.">
            <div className="space-y-4">
              {simulation.isError ? (
                <p className="rounded-md border border-negative/25 bg-negative/10 px-3 py-2 text-sm text-negative">
                  {simulation.error instanceof Error ? simulation.error.message : "Não foi possível calcular."}
                </p>
              ) : null}
              {simulation.data ? (
                <SimulationResultPanel result={simulation.data} />
              ) : (
                <EmptyState
                  icon={<Calculator size={28} aria-hidden />}
                  title="Nenhuma simulação calculada"
                />
              )}
            </div>
          </SectionCard>
        </div>
      </div>
    </>
  );
}
