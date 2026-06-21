"use client";

import { useEffect, useId, useRef, useState, type Dispatch, type SetStateAction } from "react";
import { CalendarDays, ChevronDown, ChevronLeft, ChevronRight, X } from "lucide-react";
import { cn } from "@/lib/cn";
import { formatDate, formatMonthYear } from "@/lib/format";
import { isISODate, monthOf, yearOf, type DateRange } from "@/lib/period";
import { usePeriod } from "@/providers/PeriodProvider";

const MONTHS_PT = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

function monthLabel(ym: string): string {
  const label = formatMonthYear(ym).replace(" de ", " ");
  return label.charAt(0).toUpperCase() + label.slice(1);
}

function yearMonth(year: number, month: number) {
  return `${year.toString().padStart(4, "0")}-${month.toString().padStart(2, "0")}`;
}

type CustomRangeProps = {
  initial: DateRange | null;
  setCustomOpen: Dispatch<SetStateAction<boolean>>;
  onApply: (range: DateRange | null) => void;
};

function CustomRange({ initial, setCustomOpen, onApply }: CustomRangeProps) {
  const [from, setFrom] = useState(initial?.from ?? "");
  const [to, setTo] = useState(initial?.to ?? "");
  const valid = isISODate(from) && isISODate(to) && from <= to;

  return (
    <div className="mt-3 space-y-3">
      <div className="flex items-center gap-2">
        <label className="flex-1 text-[11px] font-medium text-muted">
          De
          <input
            type="date"
            value={from}
            onChange={(event) => setFrom(event.target.value)}
            className="mt-1 h-9 w-full rounded-md border border-border bg-bg px-2 text-xs text-text"
          />
        </label>
        <label className="flex-1 text-[11px] font-medium text-muted">
          Até
          <input
            type="date"
            value={to}
            onChange={(event) => setTo(event.target.value)}
            className="mt-1 h-9 w-full rounded-md border border-border bg-bg px-2 text-xs text-text"
          />
        </label>
      </div>

      <div className="flex justify-end gap-2">
        <button
          type="button"
          onClick={() => {
            onApply(null);
            setCustomOpen(false);
          }}
          className="h-8 rounded-md px-2 text-xs font-medium text-muted transition hover:bg-surface2 hover:text-text"
        >
          Limpar
        </button>
        <button
          type="button"
          disabled={!valid}
          onClick={() => valid && onApply({ from, to })}
          className="h-8 rounded-md bg-accent px-3 text-xs font-semibold text-black transition disabled:cursor-not-allowed disabled:opacity-50"
        >
          Aplicar
        </button>
      </div>
    </div>
  );
}

export function MonthYearPicker() {
  const { mode, month, range, setMonth, setRange } = usePeriod();
  const [open, setOpen] = useState(false);
  const [year, setYear] = useState(() => yearOf(month));
  const [customOpen, setCustomOpen] = useState(mode === "range");
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const popoverId = useId();

  const togglePopover = () => {
    if (open) {
      setOpen(false);
      return;
    }

    setYear(yearOf(month));
    setCustomOpen(mode === "range");
    setOpen(true);
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

    document.addEventListener("mousedown", handleMouseDown);
    return () => document.removeEventListener("mousedown", handleMouseDown);
  }, [open]);

  useEffect(() => {
    if (!open) {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open]);

  const selectedMonth = year === yearOf(month) ? monthOf(month) : -1;
  const triggerText =
    mode === "range" && range ? `${formatDate(range.from)} - ${formatDate(range.to)}` : monthLabel(month);

  return (
    <div ref={rootRef} className="relative">
      <button
        ref={triggerRef}
        type="button"
        onClick={togglePopover}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls={popoverId}
        className="inline-flex h-10 min-w-[164px] items-center justify-between gap-2 rounded-md border border-border bg-surface px-3 text-sm font-medium text-text transition hover:bg-surface2"
      >
        <span className="inline-flex min-w-0 items-center gap-2">
          <CalendarDays size={17} aria-hidden />
          <span className="truncate">{triggerText}</span>
        </span>
        <ChevronDown size={15} aria-hidden className={cn("shrink-0 transition", open && "rotate-180")} />
      </button>

      {open && (
        <div
          id={popoverId}
          role="dialog"
          aria-label="Selecionar período"
          className="absolute right-0 z-50 mt-2 w-80 rounded-md border border-border bg-surface p-3 shadow-2xl"
        >
          <div className="mb-3 flex items-center justify-between">
            <button
              type="button"
              aria-label="Ano anterior"
              onClick={() => setYear((current) => current - 1)}
              className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted transition hover:bg-surface2 hover:text-text"
            >
              <ChevronLeft size={18} aria-hidden />
            </button>
            <span className="text-sm font-semibold text-text" aria-live="polite">
              {year}
            </span>
            <button
              type="button"
              aria-label="Próximo ano"
              onClick={() => setYear((current) => current + 1)}
              className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted transition hover:bg-surface2 hover:text-text"
            >
              <ChevronRight size={18} aria-hidden />
            </button>
          </div>

          <div className="grid grid-cols-4 gap-1" role="grid" aria-label={`Meses de ${year}`}>
            {MONTHS_PT.map((label, index) => {
              const monthNumber = index + 1;
              const selected = monthNumber === selectedMonth;

              return (
                <button
                  key={label}
                  type="button"
                  role="gridcell"
                  aria-selected={selected}
                  onClick={() => {
                    setMonth(yearMonth(year, monthNumber));
                    setOpen(false);
                  }}
                  className={cn(
                    "h-9 rounded-md text-xs font-medium capitalize transition",
                    selected
                      ? "bg-accent text-black"
                      : "text-muted hover:bg-surface2 hover:text-text",
                  )}
                >
                  {label}
                </button>
              );
            })}
          </div>

          <div className="mt-3 border-t border-border pt-3">
            <div className="flex items-center justify-between">
              <button
                type="button"
                onClick={() => setCustomOpen((current) => !current)}
                className="inline-flex h-8 items-center gap-1 rounded-md px-1 text-xs font-medium text-muted transition hover:text-text"
              >
                Período personalizado
                <ChevronRight
                  size={14}
                  aria-hidden
                  className={cn("transition", customOpen && "rotate-90")}
                />
              </button>

              {mode === "range" && (
                <button
                  type="button"
                  onClick={() => {
                    setRange(null);
                    setOpen(false);
                  }}
                  aria-label="Limpar período personalizado"
                  className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted transition hover:bg-surface2 hover:text-text"
                >
                  <X size={15} aria-hidden />
                </button>
              )}
            </div>

            {customOpen && (
              <CustomRange
                key={`${range?.from ?? ""}:${range?.to ?? ""}`}
                initial={range}
                setCustomOpen={setCustomOpen}
                onApply={(nextRange) => {
                  setRange(nextRange);
                  setOpen(false);
                }}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
