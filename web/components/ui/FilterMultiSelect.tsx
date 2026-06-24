"use client";

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Check, ChevronDown, Search, X } from "lucide-react";
import { cn } from "@/lib/cn";

export type FilterMultiSelectValue = string | number | null;

export type FilterMultiSelectOption<T extends FilterMultiSelectValue> = {
  value: T;
  label: string;
  color?: string | null;
  searchText?: string;
};

type FilterMultiSelectProps<T extends FilterMultiSelectValue> = {
  label: string;
  values: T[];
  options: Array<FilterMultiSelectOption<T>>;
  onChange: (values: T[]) => void;
  placeholder?: string;
  searchPlaceholder?: string;
  emptyLabel?: string;
  renderOption?: (option: FilterMultiSelectOption<T>) => ReactNode;
};

function normalize(value: string): string {
  return value
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase()
    .trim();
}

function sameValue(left: FilterMultiSelectValue, right: FilterMultiSelectValue): boolean {
  return left === right;
}

function optionKey(value: FilterMultiSelectValue): string {
  return value === null ? "none" : String(value);
}

function Swatch({ color }: { color?: string | null }) {
  if (!color) {
    return null;
  }

  return (
    <span
      aria-hidden
      className="h-2.5 w-2.5 shrink-0 rounded-full border border-border"
      style={{ backgroundColor: color }}
    />
  );
}

export function FilterMultiSelect<T extends FilterMultiSelectValue>({
  label,
  values,
  options,
  onChange,
  placeholder,
  searchPlaceholder,
  emptyLabel = "Nenhuma opção encontrada",
  renderOption,
}: FilterMultiSelectProps<T>) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const rootRef = useRef<HTMLDivElement>(null);
  const selectedOptions = useMemo(
    () =>
      values
        .map((value) => options.find((option) => sameValue(option.value, value)))
        .filter((option): option is FilterMultiSelectOption<T> => Boolean(option)),
    [options, values],
  );
  const filteredOptions = useMemo(() => {
    const normalized = normalize(query);
    if (!normalized) {
      return options;
    }

    return options.filter((option) =>
      normalize(`${option.label} ${option.searchText ?? ""}`).includes(normalized),
    );
  }, [options, query]);

  const toggle = (next: T) => {
    const exists = values.some((value) => sameValue(value, next));
    onChange(exists ? values.filter((value) => !sameValue(value, next)) : [...values, next]);
  };

  const remove = (next: T) => {
    onChange(values.filter((value) => !sameValue(value, next)));
  };

  useEffect(() => {
    if (!open) {
      return;
    }

    const handleMouseDown = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
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
    <div ref={rootRef} className="relative space-y-2">
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={searchPlaceholder ?? `Buscar em ${label}`}
        className="inline-flex h-10 w-full items-center justify-between gap-2 rounded-md border border-border bg-bg px-3 text-sm text-text transition hover:bg-surface2"
      >
        <span className="truncate text-muted">
          {selectedOptions.length
            ? `${selectedOptions.length} selecionado${selectedOptions.length > 1 ? "s" : ""}`
            : placeholder ?? `Buscar em ${label}`}
        </span>
        <ChevronDown size={15} aria-hidden className={cn("shrink-0 transition", open && "rotate-180")} />
      </button>

      {selectedOptions.length ? (
        <div className="flex flex-wrap gap-2" aria-label={`${label} selecionados`}>
          {selectedOptions.map((option) => (
            <button
              key={optionKey(option.value)}
              type="button"
              onClick={() => remove(option.value)}
              aria-label={`Remover filtro ${label} ${option.label}`}
              className="inline-flex min-h-8 max-w-full items-center gap-2 rounded-md border border-accent/40 bg-accent/10 px-2 py-1 text-xs font-medium text-text transition hover:bg-accent/20"
            >
              <Swatch color={option.color} />
              <span className="truncate">
                {label}: {option.label}
              </span>
              <X size={13} aria-hidden className="shrink-0 text-muted" />
            </button>
          ))}
        </div>
      ) : null}

      {open ? (
        <div className="absolute left-0 right-0 z-50 mt-2 rounded-md border border-border bg-surface p-2 shadow-2xl">
          <label className="mb-2 flex h-9 items-center gap-2 rounded-md border border-border bg-bg px-2 text-muted">
            <Search size={15} aria-hidden />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={searchPlaceholder ?? `Buscar em ${label}`}
              aria-label={searchPlaceholder ?? `Buscar em ${label}`}
              className="min-w-0 flex-1 bg-transparent text-sm text-text outline-none placeholder:text-muted"
            />
          </label>
          <div role="listbox" aria-label={label} className="max-h-64 overflow-y-auto">
            {filteredOptions.map((option) => {
              const selected = values.some((value) => sameValue(value, option.value));
              return (
                <button
                  key={optionKey(option.value)}
                  type="button"
                  role="option"
                  aria-selected={selected}
                  onClick={() => toggle(option.value)}
                  className="flex min-h-9 w-full items-center justify-between gap-3 rounded-md px-2 py-1 text-sm text-text transition hover:bg-surface2"
                >
                  <span className="inline-flex min-w-0 items-center gap-2">
                    <Swatch color={option.color} />
                    <span className="truncate">
                      {renderOption ? renderOption(option) : option.label}
                    </span>
                  </span>
                  {selected ? <Check size={16} aria-hidden className="shrink-0" /> : null}
                </button>
              );
            })}
            {!filteredOptions.length ? (
              <div className="px-2 py-4 text-center text-sm text-muted">{emptyLabel}</div>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}
