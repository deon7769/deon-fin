"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useFinancialMonthStartDayState } from "@/hooks/useFinancialMonthStartDay";
import {
  currentReferenceMonth,
  isISODate,
  isYearMonth,
  type DateRange,
} from "@/lib/period";

export type PeriodMode = "month" | "range";

type PeriodContextValue = {
  mode: PeriodMode;
  month: string;
  range: DateRange | null;
  setMonth: (ym: string) => void;
  setRange: (range: DateRange | null) => void;
};

const PeriodContext = createContext<PeriodContextValue | null>(null);
const STORAGE_MONTH = "deon-fin:period-month";
const STORAGE_MONTH_EVENT = "deon-fin:period-month-change";
let memoryStoredMonth: string | null = null;

function initialRange(searchParams: URLSearchParams): DateRange | null {
  const from = searchParams.get("from");
  const to = searchParams.get("to");
  return isISODate(from) && isISODate(to) && from <= to ? { from, to } : null;
}

function readStoredMonthSnapshot() {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    const stored = localStorage.getItem(STORAGE_MONTH);
    if (isYearMonth(stored)) {
      return stored;
    }
  } catch {
    // Keep the in-memory fallback below.
  }

  return memoryStoredMonth;
}

function subscribeStoredMonth(listener: () => void) {
  if (typeof window === "undefined") {
    return () => undefined;
  }

  const handleStorage = (event: StorageEvent) => {
    if (event.key === STORAGE_MONTH) {
      listener();
    }
  };
  const handleLocalChange = () => listener();

  window.addEventListener("storage", handleStorage);
  window.addEventListener(STORAGE_MONTH_EVENT, handleLocalChange);

  return () => {
    window.removeEventListener("storage", handleStorage);
    window.removeEventListener(STORAGE_MONTH_EVENT, handleLocalChange);
  };
}

function storeMonth(ym: string) {
  memoryStoredMonth = ym;
  try {
    localStorage.setItem(STORAGE_MONTH, ym);
  } catch {
    // URL + in-memory state still work.
  }
  window.dispatchEvent(new Event(STORAGE_MONTH_EVENT));
}

export function PeriodProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { startDay, settled: startDaySettled } = useFinancialMonthStartDayState();
  const storedMonth = useSyncExternalStore(subscribeStoredMonth, readStoredMonthSnapshot, () => null);
  const [manualMonth, setManualMonth] = useState<string | null>(null);

  const range = useMemo(() => initialRange(searchParams), [searchParams]);
  const rawUrlMonth = searchParams.get("month");
  const urlMonth = isYearMonth(rawUrlMonth) ? rawUrlMonth : null;
  const defaultMonth = useMemo(
    () => currentReferenceMonth(new Date(), startDaySettled ? startDay : 1),
    [startDay, startDaySettled],
  );
  const month = urlMonth ?? manualMonth ?? storedMonth ?? defaultMonth;
  const mode: PeriodMode = range ? "range" : "month";

  const writeUrl = useCallback(
    (next: { month?: string; range?: DateRange | null }) => {
      const params = new URLSearchParams(searchParams.toString());
      if (next.range) {
        params.delete("month");
        params.set("from", next.range.from);
        params.set("to", next.range.to);
      } else {
        params.delete("from");
        params.delete("to");
        if (next.month) {
          params.set("month", next.month);
        }
      }

      const query = params.toString();
      router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
    },
    [pathname, router, searchParams],
  );

  useEffect(() => {
    if (range || urlMonth) {
      return;
    }

    if (!manualMonth && !storedMonth && !startDaySettled) {
      return;
    }

    writeUrl({ month, range: null });
  }, [manualMonth, month, range, startDaySettled, storedMonth, urlMonth, writeUrl]);

  const setMonth = useCallback(
    (ym: string) => {
      if (!isYearMonth(ym)) {
        return;
      }
      setManualMonth(ym);
      storeMonth(ym);
      writeUrl({ month: ym, range: null });
    },
    [writeUrl],
  );

  const setRange = useCallback(
    (nextRange: DateRange | null) => {
      if (
        nextRange &&
        isISODate(nextRange.from) &&
        isISODate(nextRange.to) &&
        nextRange.from <= nextRange.to
      ) {
        writeUrl({ range: nextRange });
        return;
      }

      writeUrl({ month, range: null });
    },
    [month, writeUrl],
  );

  const value = useMemo<PeriodContextValue>(
    () => ({ mode, month, range, setMonth, setRange }),
    [mode, month, range, setMonth, setRange],
  );

  return <PeriodContext.Provider value={value}>{children}</PeriodContext.Provider>;
}

export function usePeriod() {
  const value = useContext(PeriodContext);
  if (!value) {
    throw new Error("usePeriod must be used inside PeriodProvider");
  }
  return value;
}
