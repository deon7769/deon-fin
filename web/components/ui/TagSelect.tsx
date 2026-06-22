"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Check, ChevronDown, Plus, Search, X } from "lucide-react";
import { filterTags, tagById } from "@/lib/tags";
import { cn } from "@/lib/cn";
import type { Tag } from "@/lib/types";
import { Pill } from "./Pill";

type TagSelectProps = {
  value?: number | null;
  options: Tag[];
  onChange?: (tagId: number | null) => void;
  onChangeWithPropagation?: (tagId: number | null, applyToSimilar: boolean) => void;
  onCreate?: (name: string) => Promise<Tag> | Tag;
  disabled?: boolean;
  placeholder?: string;
  searchPlaceholder?: string;
  loading?: boolean;
};

type PendingSelection = {
  tagId: number | null;
};

function normalizeLabel(value: string): string {
  return value
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase()
    .trim();
}

export function TagSelect({
  value = null,
  options,
  onChange,
  onChangeWithPropagation,
  onCreate,
  disabled = false,
  placeholder = "Selecione uma tag",
  searchPlaceholder = "Buscar tag...",
  loading = false,
}: TagSelectProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [creating, setCreating] = useState(false);
  const [pending, setPending] = useState<PendingSelection | null>(null);
  const [error, setError] = useState<string | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const selected = tagById(options, value);
  const filtered = useMemo(() => filterTags(options, query), [options, query]);
  const trimmedQuery = query.trim();
  const existingMatch = options.find(
    (tag) => normalizeLabel(tag.name) === normalizeLabel(trimmedQuery),
  );
  const canCreate = Boolean(onCreate && trimmedQuery && !existingMatch && !creating);
  const buttonLabel = loading ? "Carregando..." : selected?.name ?? placeholder;

  const close = () => {
    setOpen(false);
    setQuery("");
    setError(null);
    setCreating(false);
    setPending(null);
  };

  const commit = (tagId: number | null, applyToSimilar: boolean) => {
    if (onChangeWithPropagation) {
      onChangeWithPropagation(tagId, applyToSimilar);
    } else {
      onChange?.(tagId);
    }
    close();
  };

  const selectTag = (tagId: number | null) => {
    if (tagId === null || !onChangeWithPropagation) {
      commit(tagId, false);
      return;
    }
    setPending({ tagId });
  };

  const createTag = async () => {
    if (!onCreate || !trimmedQuery || existingMatch) {
      if (existingMatch) {
        selectTag(existingMatch.id);
      }
      return;
    }

    setCreating(true);
    setError(null);
    try {
      const tag = await onCreate(trimmedQuery);
      if (onChangeWithPropagation) {
        onChangeWithPropagation(tag.id, false);
      } else {
        onChange?.(tag.id);
      }
      close();
    } catch {
      setError("Não foi possível criar a tag.");
      setCreating(false);
    }
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
        aria-label="Tag"
        className="inline-flex h-9 min-w-[164px] items-center justify-between gap-2 rounded-md border border-border bg-surface2 px-3 text-sm text-text transition hover:bg-surface disabled:cursor-not-allowed disabled:opacity-60"
      >
        <span className="inline-flex min-w-0 items-center gap-2">
          {selected ? (
            <Pill color={selected.color} className="min-w-0 max-w-[8.5rem]">
              <span className="truncate">{selected.name}</span>
            </Pill>
          ) : null}
          {!selected ? <span className="truncate text-muted">{buttonLabel}</span> : null}
        </span>
        <ChevronDown size={15} aria-hidden className={cn("shrink-0 transition", open && "rotate-180")} />
      </button>

      {open && (
        <div className="absolute right-0 z-50 mt-2 w-72 rounded-md border border-border bg-surface p-2 shadow-2xl">
          {pending ? (
            <div className="space-y-2 p-1">
              <p className="text-xs font-medium text-text">
                {tagById(options, pending.tagId)?.name ?? "Sem tag"}
              </p>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => commit(pending.tagId, false)}
                  className="h-8 flex-1 rounded-md border border-border px-2 text-xs font-medium text-muted transition hover:bg-surface2 hover:text-text"
                >
                  Só esta
                </button>
                <button
                  type="button"
                  onClick={() => commit(pending.tagId, true)}
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
                  onChange={(event) => {
                    setQuery(event.target.value);
                    setError(null);
                  }}
                  placeholder={searchPlaceholder}
                  aria-label="Buscar tag"
                  className="min-w-0 flex-1 bg-transparent text-sm text-text outline-none placeholder:text-muted"
                />
              </label>

              {onCreate ? (
                <button
                  type="button"
                  disabled={!canCreate}
                  onClick={createTag}
                  className="mb-2 flex h-9 w-full items-center gap-2 rounded-md px-2 text-sm font-medium text-accent transition hover:bg-surface2 disabled:cursor-not-allowed disabled:text-muted"
                >
                  <Plus size={15} aria-hidden />
                  <span className="truncate">{creating ? "Criando..." : `Criar "${trimmedQuery || "tag"}"`}</span>
                </button>
              ) : null}

              {error ? <p className="mb-2 px-2 text-xs text-negative">{error}</p> : null}

              <div role="listbox" aria-label="Tag" className="max-h-64 overflow-y-auto">
                <button
                  type="button"
                  role="option"
                  aria-selected={value === null}
                  onClick={() => selectTag(null)}
                  className="flex h-9 w-full items-center justify-between rounded-md px-2 text-sm text-muted transition hover:bg-surface2 hover:text-text"
                >
                  <span className="inline-flex items-center gap-2">
                    <X size={15} aria-hidden />
                    <span>Sem tag</span>
                  </span>
                  {value === null && <Check size={16} aria-hidden />}
                </button>

                {filtered.map((tag) => {
                  const selectedTag = tag.id === value;
                  return (
                    <button
                      key={tag.id}
                      type="button"
                      role="option"
                      aria-selected={selectedTag}
                      onClick={() => selectTag(tag.id)}
                      className="flex h-10 w-full items-center justify-between gap-3 rounded-md px-2 text-sm text-text transition hover:bg-surface2"
                    >
                      <Pill color={tag.color} className="min-w-0 max-w-[13rem]">
                        <span className="truncate">{tag.name}</span>
                      </Pill>
                      {selectedTag && <Check size={16} aria-hidden className="shrink-0" />}
                    </button>
                  );
                })}

                {!filtered.length ? (
                  <div className="px-2 py-4 text-center text-sm text-muted">Nenhuma tag encontrada</div>
                ) : null}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
