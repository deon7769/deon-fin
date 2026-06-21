"use client";

import type { Tag } from "@/lib/types";

type TagSelectProps = {
  value?: number | null;
  options: Tag[];
  onChange?: (tagId: number | null) => void;
  disabled?: boolean;
  placeholder?: string;
};

export function TagSelect({
  value = null,
  options,
  onChange,
  disabled = false,
  placeholder = "Tag...",
}: TagSelectProps) {
  return (
    <select
      aria-label="Tag"
      disabled={disabled}
      value={value ?? ""}
      onChange={(event) => onChange?.(event.target.value ? Number(event.target.value) : null)}
      className="h-9 rounded-md border border-border bg-surface2 px-3 text-sm text-text disabled:opacity-60"
    >
      <option value="">{placeholder}</option>
      {options.map((tag) => (
        <option key={tag.id} value={tag.id}>
          {tag.name}
        </option>
      ))}
    </select>
  );
}
