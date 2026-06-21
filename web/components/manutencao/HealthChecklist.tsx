import { AlertTriangle, CheckCircle2 } from "lucide-react";
import type { MaintenanceHealth } from "@/lib/maintenance";

type HealthChecklistProps = {
  health: MaintenanceHealth;
};

export function HealthChecklist({ health }: HealthChecklistProps) {
  return (
    <div className="grid gap-3 md:grid-cols-2">
      {health.items.map((item) => {
        const Icon = item.ok ? CheckCircle2 : AlertTriangle;
        return (
          <div
            key={item.key}
            className="flex items-start gap-3 rounded-md border border-border bg-surface2 px-3 py-3"
          >
            <Icon
              size={18}
              className={item.ok ? "mt-0.5 text-positive" : "mt-0.5 text-accent"}
              aria-hidden
            />
            <div className="min-w-0">
              <p className="text-sm font-medium text-text">{item.label}</p>
              <p className="mt-1 text-xs text-muted">{item.description}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
