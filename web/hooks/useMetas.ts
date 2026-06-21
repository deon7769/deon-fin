"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { BucketPlanPatch } from "@/lib/metas";
import type { Bucket, BucketPlanResponse, SavingsGoal, SavingsGoalsResponse } from "@/lib/types";
import { usePeriod } from "@/providers/PeriodProvider";

export type SavingsGoalInput = {
  name: string;
  target_amount: number;
  term_months: number;
  saved_amount?: number;
  priority?: number;
};

function invalidateMetasSurfaces(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: ["bucketPlan"] });
  queryClient.invalidateQueries({ queryKey: ["buckets"] });
  queryClient.invalidateQueries({ queryKey: ["budget"] });
  queryClient.invalidateQueries({ queryKey: ["savings"] });
}

export function useBucketPlan() {
  const { month } = usePeriod();

  return useQuery({
    queryKey: ["bucketPlan", month],
    queryFn: ({ signal }) => api.get<BucketPlanResponse>("/buckets/plan", { month }, signal),
    staleTime: 30_000,
  });
}

export function useUpdateBucket() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (vars: { id: number; input: Partial<BucketPlanPatch> }) =>
      api.patch<Bucket>(`/buckets/${vars.id}`, vars.input),
    onSuccess: () => invalidateMetasSurfaces(queryClient),
  });
}

export function useReorderBuckets() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (order: number[]) => api.patch<{ updated: number }>("/buckets/sort", { order }),
    onSuccess: () => invalidateMetasSurfaces(queryClient),
  });
}

export function useSavingsGoals() {
  const { month } = usePeriod();

  return useQuery({
    queryKey: ["savings", month],
    queryFn: ({ signal }) => api.get<SavingsGoalsResponse>("/savings-goals", { month }, signal),
    staleTime: 30_000,
  });
}

export function useCreateGoal() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: SavingsGoalInput) => api.post<SavingsGoal>("/savings-goals", input),
    onSuccess: () => invalidateMetasSurfaces(queryClient),
  });
}

export function useUpdateGoal() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (vars: { id: number; input: Partial<SavingsGoalInput> }) =>
      api.patch<SavingsGoal>(`/savings-goals/${vars.id}`, vars.input),
    onSuccess: () => invalidateMetasSurfaces(queryClient),
  });
}

export function useDeleteGoal() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => api.del<{ deleted_id: number }>(`/savings-goals/${id}`),
    onSuccess: () => invalidateMetasSurfaces(queryClient),
  });
}
