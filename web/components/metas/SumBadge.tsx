import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/cn";
import { sumBadgeState } from "@/lib/metas";
import type { BucketPlanResponse } from "@/lib/types";

export function SumBadge({ plan }: { plan: BucketPlanResponse }) {
  const state = sumBadgeState(plan);
  const Icon = state.tone === "ok" ? CheckCircle2 : AlertTriangle;

  return (
    <div
      className={cn(
        "inline-flex min-h-9 items-center gap-2 rounded-md border px-3 text-sm font-medium",
        state.tone === "ok"
          ? "border-positive/30 bg-positive/10 text-positive"
          : "border-accent/30 bg-accent/10 text-accent",
      )}
      title={plan.warning?.message}
    >
      <Icon size={16} aria-hidden />
      <span>{state.label}</span>
    </div>
  );
}
