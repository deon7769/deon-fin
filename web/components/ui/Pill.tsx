import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

type PillProps = {
  children: ReactNode;
  color?: string | null;
  className?: string;
};

export function Pill({ children, color, className }: PillProps) {
  return (
    <span
      className={cn(
        "inline-flex min-h-7 items-center gap-2 rounded-pill border border-border bg-surface2 px-3 text-xs font-medium text-text",
        className,
      )}
    >
      {color ? (
        <span
          className="h-2 w-2 shrink-0 rounded-full"
          style={{ backgroundColor: color }}
          aria-hidden
        />
      ) : null}
      {children}
    </span>
  );
}
