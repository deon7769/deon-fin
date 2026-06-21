import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

type SectionCardProps = {
  title?: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
};

export function SectionCard({ title, subtitle, actions, children, className }: SectionCardProps) {
  return (
    <section className={cn("rounded-card border border-border bg-surface", className)}>
      {(title || subtitle || actions) && (
        <div className="flex items-start justify-between gap-4 border-b border-border px-5 py-4">
          <div className="min-w-0">
            {title ? <h2 className="text-base font-semibold text-text">{title}</h2> : null}
            {subtitle ? <p className="mt-1 text-sm text-muted">{subtitle}</p> : null}
          </div>
          {actions ? <div className="shrink-0">{actions}</div> : null}
        </div>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}
