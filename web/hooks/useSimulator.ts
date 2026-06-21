"use client";

import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  AmortizationRequest,
  AmortizationResponse,
  ScenarioSimulationRequest,
  ScenarioSimulationResponse,
} from "@/lib/types";

export function useScenarioSimulation() {
  return useMutation({
    mutationFn: (input: ScenarioSimulationRequest) =>
      api.post<ScenarioSimulationResponse>("/simular", input),
  });
}

export function useAmortizationSimulation() {
  return useMutation({
    mutationFn: (input: AmortizationRequest) =>
      api.post<AmortizationResponse>("/amortizacao", input),
  });
}
