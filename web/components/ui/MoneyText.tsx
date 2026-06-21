"use client";

import { cn } from "@/lib/cn";
import { formatBRL } from "@/lib/format";
import { usePrivacy } from "@/providers/PrivacyProvider";

type MoneyTextProps = {
  value: number;
  hidden?: boolean;
  colorBySign?: boolean | "auto" | "none";
  className?: string;
};

const MASK = "••••";

export function MoneyText({ value, hidden, colorBySign = false, className }: MoneyTextProps) {
  const { hidden: globalHidden } = usePrivacy();
  const masked = hidden ?? globalHidden;
  const shouldColor = colorBySign === true || colorBySign === "auto";

  return (
    <span
      className={cn(
        "tabular-nums",
        shouldColor && value > 0 && "text-positive",
        shouldColor && value < 0 && "text-negative",
        className,
      )}
      aria-label={masked ? "valor oculto" : undefined}
    >
      {masked ? MASK : formatBRL(value)}
    </span>
  );
}
