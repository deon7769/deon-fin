"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Tag } from "@/lib/types";

export function useTags() {
  return useQuery({
    queryKey: ["tags"],
    queryFn: () => api.get<{ items: Tag[] }>("/tags").then((response) => response.items),
    staleTime: 60 * 60_000,
  });
}
