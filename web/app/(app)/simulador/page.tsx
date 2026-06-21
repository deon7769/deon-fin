"use client";

import { useState } from "react";
import { Calculator, PercentCircle } from "lucide-react";
import { AmortizationForm } from "@/components/simulador/AmortizationForm";
import { AmortizationResult } from "@/components/simulador/AmortizationResult";
import { ScenarioForm } from "@/components/simulador/ScenarioForm";
import { ScenarioResult } from "@/components/simulador/ScenarioResult";
import { SimulatorTabs, type SimulatorMode } from "@/components/simulador/SimulatorTabs";
import { Header } from "@/components/layout/Header";
import { EmptyState } from "@/components/ui/EmptyState";
import { SectionCard } from "@/components/ui/SectionCard";
import { useMaintenance } from "@/hooks/useMaintenance";
import { useAmortizationSimulation, useScenarioSimulation } from "@/hooks/useSimulator";
import {
  DEFAULT_AMORTIZATION_INPUT,
  DEFAULT_SCENARIO_INPUT,
  SCENARIO_PRESETS,
  propertyToAmortizationInput,
  validateAmortizationInput,
  validateScenarioInput,
  type ScenarioPresetKey,
} from "@/lib/simulator";

function ErrorNotice({ error }: { error: unknown }) {
  return (
    <p className="rounded-md border border-negative/25 bg-negative/10 px-3 py-2 text-sm text-negative">
      {error instanceof Error ? error.message : "Não foi possível executar a simulação."}
    </p>
  );
}

export default function SimuladorPage() {
  const [mode, setMode] = useState<SimulatorMode>("cenario");
  const [scenarioInput, setScenarioInput] = useState(DEFAULT_SCENARIO_INPUT);
  const [amortizationInput, setAmortizationInput] = useState(DEFAULT_AMORTIZATION_INPUT);
  const [scenarioValidation, setScenarioValidation] = useState<string | null>(null);
  const [amortizationValidation, setAmortizationValidation] = useState<string | null>(null);
  const scenario = useScenarioSimulation();
  const amortization = useAmortizationSimulation();
  const maintenance = useMaintenance();

  const applyPreset = (preset: ScenarioPresetKey) => {
    setScenarioValidation(null);
    setScenarioInput(SCENARIO_PRESETS[preset]);
  };

  const runScenario = () => {
    const validation = validateScenarioInput(scenarioInput);
    if (!validation.valid) {
      setScenarioValidation(validation.message);
      return;
    }
    setScenarioValidation(null);
    scenario.mutate(scenarioInput);
  };

  const loadProperty = () => {
    const input = propertyToAmortizationInput(maintenance.data);
    if (input) {
      setAmortizationValidation(null);
      setAmortizationInput(input);
    }
  };

  const runAmortization = () => {
    const validation = validateAmortizationInput(amortizationInput);
    if (!validation.valid) {
      setAmortizationValidation(validation.message);
      return;
    }
    setAmortizationValidation(null);
    amortization.mutate(amortizationInput);
  };

  const propertyInput = propertyToAmortizationInput(maintenance.data);

  return (
    <>
      <Header
        title="Simulador"
        subtitle="Compare compra financiada, consórcio, juntar à vista e amortização extra."
      />

      <div className="space-y-5 p-4 sm:p-6">
        <SimulatorTabs value={mode} onChange={setMode} />

        {mode === "cenario" ? (
          <>
            <SectionCard
              title="Cenários de compra"
              subtitle="Preencha o valor do bem e compare as estratégias sem recarregar a página."
            >
              <ScenarioForm
                value={scenarioInput}
                validationMessage={scenarioValidation}
                loading={scenario.isPending}
                onChange={setScenarioInput}
                onPreset={applyPreset}
                onSubmit={runScenario}
              />
            </SectionCard>

            <SectionCard title="Resultado" subtitle="Financiamento, consórcio e juntar à vista.">
              <div className="space-y-4">
                {scenario.isError ? <ErrorNotice error={scenario.error} /> : null}
                {scenario.data ? (
                  <ScenarioResult result={scenario.data} />
                ) : (
                  <EmptyState
                    icon={<Calculator size={28} aria-hidden />}
                    title="Nenhum cenário calculado"
                    description="Execute a simulação para comparar as alternativas."
                  />
                )}
              </div>
            </SectionCard>
          </>
        ) : (
          <>
            <SectionCard
              title="Amortização de financiamento"
              subtitle="Veja quanto prazo e juros caem ao pagar um aporte extra por mês."
            >
              <AmortizationForm
                value={amortizationInput}
                validationMessage={amortizationValidation}
                loading={amortization.isPending}
                canLoadProperty={Boolean(propertyInput)}
                loadingProperty={maintenance.isLoading}
                onChange={setAmortizationInput}
                onLoadProperty={loadProperty}
                onSubmit={runAmortization}
              />
            </SectionCard>

            <SectionCard title="Resultado" subtitle="Comparação entre parcela atual e parcela acelerada.">
              <div className="space-y-4">
                {amortization.isError ? <ErrorNotice error={amortization.error} /> : null}
                {amortization.data ? (
                  <AmortizationResult result={amortization.data} />
                ) : (
                  <EmptyState
                    icon={<PercentCircle size={28} aria-hidden />}
                    title="Nenhuma amortização calculada"
                    description="Execute a simulação para ver a economia de prazo e juros."
                  />
                )}
              </div>
            </SectionCard>
          </>
        )}
      </div>
    </>
  );
}
