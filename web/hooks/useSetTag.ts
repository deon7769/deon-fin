"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export type SetTagResponse = {
  updated: number;
  tag_id: number | null;
  tag_source: string;
  match_key: string;
  rule_upserted: boolean;
  rule_deleted?: boolean;
  similar_affected: number;
  similar_ids: string[];
};

export function useSetTag() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (vars: { txId: string; tagId: number | null; applyToSimilar?: boolean }) =>
      api.post<SetTagResponse>(`/transactions/${vars.txId}/tag`, {
        tag_id: vars.tagId,
        apply_to_similar: vars.applyToSimilar ?? false,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["invoice"] });
      queryClient.invalidateQueries({ queryKey: ["painel"] });
    },
  });
}
