"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export type SetBucketResponse = {
  updated: number;
  bucket_id: number | null;
  bucket_source: string;
  match_key: string;
  rule_upserted: boolean;
  rule_deleted?: boolean;
  similar_affected: number;
  similar_ids: string[];
};

export function useSetBucket() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (vars: { txId: string; bucketId: number | null; applyToSimilar?: boolean }) =>
      api.post<SetBucketResponse>(`/transactions/${vars.txId}/bucket`, {
        bucket_id: vars.bucketId,
        apply_to_similar: vars.applyToSimilar ?? false,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["budget"] });
      queryClient.invalidateQueries({ queryKey: ["invoice"] });
      queryClient.invalidateQueries({ queryKey: ["painel"] });
      queryClient.invalidateQueries({ queryKey: ["maintenance"] });
      queryClient.invalidateQueries({ queryKey: ["maintenance", "classification-audit"] });
      queryClient.invalidateQueries({ queryKey: ["maintenance", "classification-rules"] });
      queryClient.invalidateQueries({ queryKey: ["maintenance", "classification-suggestions"] });
    },
  });
}
