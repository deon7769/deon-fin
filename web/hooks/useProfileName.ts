"use client";

import { useProfile } from "@/hooks/useProfile";

export function useProfileName() {
  const query = useProfile();
  return {
    ...query,
    name: query.data?.name?.trim() ?? "",
  };
}
