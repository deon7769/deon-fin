import type { ReactNode } from "react";

type EmptyStateProps = {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
};

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex min-h-56 flex-col items-center justify-center gap-3 text-center">
      {icon ? <div className="text-muted">{icon}</div> : null}
      <div className="space-y-1">
        <p className="text-sm font-semibold text-text">{title}</p>
        {description ? <p className="max-w-sm text-sm text-muted">{description}</p> : null}
      </div>
      {action ? <div className="pt-2">{action}</div> : null}
    </div>
  );
}
