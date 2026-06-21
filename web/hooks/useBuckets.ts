"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Bucket } from "@/lib/types";

export function useBuckets() {
  return useQuery({
    queryKey: ["buckets"],
    queryFn: () => api.get<{ items: Bucket[] }>("/buckets").then((response) => response.items),
    staleTime: 60 * 60_000,
  });
}
