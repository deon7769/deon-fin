"use client";

import { useCallback } from "react";
import { formatBRL } from "@/lib/format";
import { usePrivacy } from "@/providers/PrivacyProvider";

export function useMoneyFormatter() {
  const { hidden } = usePrivacy();

  return useCallback(
    (value: number) => (hidden ? "••••" : formatBRL(value)),
    [hidden],
  );
}
