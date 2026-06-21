"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export type SetTagResponse = {
  updated: number;
  tag_id: number | null;
};

export function useSetTag() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (vars: { txId: string; tagId: number | null }) =>
      api.patch<SetTagResponse>(`/transactions/${vars.txId}`, {
        tag_id: vars.tagId,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["invoice"] });
      queryClient.invalidateQueries({ queryKey: ["painel"] });
    },
  });
}
