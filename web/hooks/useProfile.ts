"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Profile } from "@/lib/types";

export type ProfileInput = {
  name: string;
  email: string;
  monthly_income: number;
  financial_month_start_day: number;
  goals_text: string;
};

export type UpdateProfileResponse = {
  saved: boolean;
  reference_month_recompute: "scheduled" | "not_needed";
  profile: Profile;
};

export function useProfile() {
  return useQuery({
    queryKey: ["profile"],
    queryFn: ({ signal }) => api.get<Profile>("/profile", undefined, signal),
    staleTime: 5 * 60_000,
  });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: ProfileInput) => api.put<UpdateProfileResponse>("/profile", input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["profile"] });
      queryClient.invalidateQueries({ queryKey: ["profile", "financial-month-start-day"] });
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["budget"] });
      queryClient.invalidateQueries({ queryKey: ["painel"] });
    },
  });
}
