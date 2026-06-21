export type DateRange = {
  from: string;
  to: string;
};

function clampStartDay(value: number): number {
  return Math.max(1, Math.min(28, Math.trunc(value || 1)));
}

function isoDate(date: Date): string {
  const year = date.getFullYear().toString().padStart(4, "0");
  const month = (date.getMonth() + 1).toString().padStart(2, "0");
  const day = date.getDate().toString().padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function yearMonth(year: number, month: number): string {
  return `${year.toString().padStart(4, "0")}-${month.toString().padStart(2, "0")}`;
}

export function currentReferenceMonth(date: Date, startDay = 1): string {
  const day = clampStartDay(startDay);
  let year = date.getFullYear();
  let month = date.getMonth() + 1;

  if (date.getDate() < day) {
    month -= 1;
    if (month === 0) {
      month = 12;
      year -= 1;
    }
  }

  return yearMonth(year, month);
}

export function shiftMonth(ym: string, delta: number): string {
  const [year, month] = ym.split("-").map(Number);
  const shifted = new Date(year, month - 1 + delta, 1);
  return yearMonth(shifted.getFullYear(), shifted.getMonth() + 1);
}

export function monthRange(ym: string, startDay = 1): DateRange {
  const [year, month] = ym.split("-").map(Number);
  const day = clampStartDay(startDay);
  const from = new Date(year, month - 1, day);
  const to = new Date(year, month, day - 1);

  return {
    from: isoDate(from),
    to: isoDate(to),
  };
}

export function yearOf(ym: string): number {
  return Number(ym.slice(0, 4));
}

export function monthOf(ym: string): number {
  return Number(ym.slice(5, 7));
}

export function isYearMonth(value: string | null | undefined): value is string {
  return !!value && /^\d{4}-(0[1-9]|1[0-2])$/.test(value);
}

export function isISODate(value: string | null | undefined): value is string {
  return !!value && /^\d{4}-\d{2}-\d{2}$/.test(value);
}
