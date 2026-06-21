const BRL = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
});
const PCT = new Intl.NumberFormat("pt-BR", {
  style: "percent",
  maximumFractionDigits: 1,
});
const DATE = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
});
const MONTH_YEAR = new Intl.DateTimeFormat("pt-BR", {
  month: "long",
  year: "numeric",
});

export function formatBRL(value: number): string {
  return BRL.format(Number.isFinite(value) ? value : 0).replace(/\u00a0/g, " ");
}

export function formatDate(input: Date | string): string {
  const date = typeof input === "string" ? new Date(`${input}T00:00:00`) : input;
  return DATE.format(date);
}

export function formatPercent(value: number, asFraction = true): string {
  return PCT.format(asFraction ? value : value / 100);
}

export function formatMonthYear(ym: string): string {
  const [year, month] = ym.split("-").map(Number);
  return MONTH_YEAR.format(new Date(year, (month || 1) - 1, 1));
}
