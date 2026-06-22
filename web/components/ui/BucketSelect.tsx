"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Check, ChevronDown, Search } from "lucide-react";
import { bucketById, filterBuckets } from "@/lib/buckets";
import { cn } from "@/lib/cn";
import type { Bucket } from "@/lib/types";

type BucketSelectProps = {
  value?: number | null;
  options: Bucket[];
  onChange?: (bucketId: number | null) => void;
  onChangeWithPropagation?: (bucketId: number | null, applyToSimilar: boolean) => void;
  disabled?: boolean;
  placeholder?: string;
  searchPlaceholder?: string;
  loading?: boolean;
};

type PendingSelection = {
  bucketId: number | null;
};

function BucketDot({ color }: { color?: string | null }) {
  return (
    <span
      aria-hidden
      className="h-2.5 w-2.5 shrink-0 rounded-full border border-border"
      style={{ backgroundColor: color ?? "transparent" }}
    />
  );
}

export function BucketSelect({
  value = null,
  options,
  onChange,
  onChangeWithPropagation,
  disabled = false,
  placeholder = "Meta...",
  searchPlaceholder = "Buscar meta...",
  loading = false,
}: BucketSelectProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [pending, setPending] = useState<PendingSelection | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const selected = bucketById(options, value);
  const filtered = useMemo(() => filterBuckets(options, query), [options, query]);
  const buttonLabel = loading ? "Carregando..." : selected?.name ?? placeholder;

  const close = () => {
    setOpen(false);
    setPending(null);
    setQuery("");
  };

  const commit = (bucketId: number | null, applyToSimilar: boolean) => {
    if (onChangeWithPropagation) {
      onChangeWithPropagation(bucketId, applyToSimilar);
    } else {
      onChange?.(bucketId);
    }
    close();
  };

  const selectBucket = (bucketId: number | null) => {
    if (bucketId === null || !onChangeWithPropagation) {
      commit(bucketId, false);
      return;
    }
    setPending({ bucketId });
  };

  useEffect(() => {
    if (!open) {
      return;
    }

    const handleMouseDown = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        close();
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        close();
      }
    };

    document.addEventListener("mousedown", handleMouseDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleMouseDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  return (
    <div ref={rootRef} className="relative inline-block text-left">
      <button
        type="button"
        disabled={disabled || loading}
        onClick={() => setOpen((current) => !current)}
        aria-haspopup="listbox"
        aria-expanded={open}
        className="inline-flex h-9 min-w-[156px] items-center justify-between gap-2 rounded-md border border-border bg-surface2 px-3 text-sm text-text transition hover:bg-surface disabled:cursor-not-allowed disabled:opacity-60"
      >
        <span className="inline-flex min-w-0 items-center gap-2">
          {selected && <BucketDot color={selected.color} />}
          <span className="truncate">{buttonLabel}</span>
        </span>
        <ChevronDown size={15} aria-hidden className={cn("shrink-0 transition", open && "rotate-180")} />
      </button>

      {open && (
        <div className="absolute right-0 z-50 mt-2 w-72 rounded-md border border-border bg-surface p-2 shadow-2xl">
          {pending ? (
            <div className="space-y-2 p-1">
              <p className="text-xs font-medium text-text">
                {bucketById(options, pending.bucketId)?.name ?? "Sem meta"}
              </p>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => commit(pending.bucketId, false)}
                  className="h-8 flex-1 rounded-md border border-border px-2 text-xs font-medium text-muted transition hover:bg-surface2 hover:text-text"
                >
                  Só esta
                </button>
                <button
                  type="button"
                  onClick={() => commit(pending.bucketId, true)}
                  className="h-8 flex-1 rounded-md bg-accent px-2 text-xs font-semibold text-accentFg transition hover:brightness-95"
                >
                  Aplicar similares
                </button>
              </div>
            </div>
          ) : (
            <>
              <label className="mb-2 flex h-9 items-center gap-2 rounded-md border border-border bg-bg px-2 text-muted">
                <Search size={15} aria-hidden />
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder={searchPlaceholder}
                  className="min-w-0 flex-1 bg-transparent text-sm text-text outline-none placeholder:text-muted"
                />
              </label>

              <div role="listbox" aria-label="Meta" className="max-h-64 overflow-y-auto">
                <button
                  type="button"
                  role="option"
                  aria-selected={value === null}
                  onClick={() => selectBucket(null)}
                  className="flex h-9 w-full items-center justify-between rounded-md px-2 text-sm text-muted transition hover:bg-surface2 hover:text-text"
                >
                  <span>Sem meta</span>
                  {value === null && <Check size={16} aria-hidden />}
                </button>

                {filtered.map((bucket) => {
                  const selectedBucket = bucket.id === value;
                  return (
                    <button
                      key={bucket.id}
                      type="button"
                      role="option"
                      aria-selected={selectedBucket}
                      onClick={() => selectBucket(bucket.id)}
                      className="flex h-9 w-full items-center justify-between gap-3 rounded-md px-2 text-sm text-text transition hover:bg-surface2"
                    >
                      <span className="inline-flex min-w-0 items-center gap-2">
                        <BucketDot color={bucket.color} />
                        <span className="truncate">{bucket.name}</span>
                      </span>
                      {selectedBucket && <Check size={16} aria-hidden className="shrink-0" />}
                    </button>
                  );
                })}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
