"use client";

import { formatSyncDateTime, syncStatusLabel, syncStatusTone } from "@/lib/accounts";
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

export function SyncStatusChip({ status, at }: SyncStatusChipProps) {
  const tone = syncStatusTone(status);
  const timestamp = formatSyncDateTime(at);

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
