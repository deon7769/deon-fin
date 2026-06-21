"use client";

import { syncStatusLabel, syncStatusTone } from "@/lib/accounts";
import { cn } from "@/lib/cn";

type SyncStatusChipProps = {
  status: string;
  at?: string | null;
};

const toneClasses = {
  positive: "text-positive",
  negative: "text-negative",
  accent: "text-accent",
  muted: "text-muted",
};

function formatDateTime(value?: string | null): string | null {
  if (!value) {
    return null;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function SyncStatusChip({ status, at }: SyncStatusChipProps) {
  const tone = syncStatusTone(status);
  const timestamp = formatDateTime(at);

  return (
    <div className="min-w-0">
      <span className={cn("inline-flex items-center gap-2 text-sm font-medium", toneClasses[tone])}>
        <span className="h-2 w-2 rounded-full bg-current" aria-hidden />
        {syncStatusLabel(status)}
      </span>
      {timestamp ? <p className="mt-1 text-xs text-muted">{timestamp}</p> : null}
    </div>
  );
}
