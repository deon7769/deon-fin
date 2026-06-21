"use client";

import type { Bucket } from "@/lib/types";

type BucketSelectProps = {
  value?: number | null;
  options: Bucket[];
  onChange?: (bucketId: number | null) => void;
  disabled?: boolean;
  placeholder?: string;
};

export function BucketSelect({
  value = null,
  options,
  onChange,
  disabled = false,
  placeholder = "Meta...",
}: BucketSelectProps) {
  return (
    <select
      aria-label="Meta"
      disabled={disabled}
      value={value ?? ""}
      onChange={(event) => onChange?.(event.target.value ? Number(event.target.value) : null)}
      className="h-9 rounded-md border border-border bg-surface2 px-3 text-sm text-text disabled:opacity-60"
    >
      <option value="">{placeholder}</option>
      {options.map((bucket) => (
        <option key={bucket.id} value={bucket.id}>
          {bucket.name}
        </option>
      ))}
    </select>
  );
}
