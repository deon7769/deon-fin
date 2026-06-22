"use client";

import { useMutation } from "@tanstack/react-query";

import { api } from "@/lib/api";
import {
  endpointForCalculator,
  type CalculatorKey,
  type SimulationPayload,
  type SimulationResponse,
} from "@/lib/simulacoes";

export function useSimulationCalculator(key: CalculatorKey) {
  return useMutation({
    mutationFn: (input: SimulationPayload) =>
      api.post<SimulationResponse>(endpointForCalculator(key), input),
  });
}
