import { describe, expect, it } from "vitest";

import { formatBRL, formatDate, formatMonthYear, formatPercent } from "@/lib/format";

describe("format helpers", () => {
  it("formats money as Brazilian reais", () => {
    expect(formatBRL(1234.5)).toBe("R$ 1.234,50");
    expect(formatBRL(-80)).toBe("-R$ 80,00");
    expect(formatBRL(Number.NaN)).toBe("R$ 0,00");
  });

  it("formats ISO dates in pt-BR without timezone drift", () => {
    expect(formatDate("2026-06-20")).toBe("20/06/2026");
  });

  it("formats percentages from fractions or percentage points", () => {
    expect(formatPercent(0.5)).toBe("50%");
    expect(formatPercent(12.5, false)).toBe("12,5%");
  });

  it("formats reference months in long pt-BR form", () => {
    expect(formatMonthYear("2026-06")).toBe("junho de 2026");
    expect(formatMonthYear("2026-12")).toBe("dezembro de 2026");
  });
});
