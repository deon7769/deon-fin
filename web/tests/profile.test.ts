import { describe, expect, it } from "vitest";

import { formatCurrencyInput, initialsFor, parseCurrencyInput } from "@/lib/profile";

describe("profile helpers", () => {
  it("builds initials from profile names", () => {
    expect(initialsFor("Davi Alves")).toBe("DA");
    expect(initialsFor("Davi")).toBe("D");
    expect(initialsFor("  maria   da silva ")).toBe("MD");
    expect(initialsFor("")).toBe("?");
    expect(initialsFor(null)).toBe("?");
  });

  it("parses Brazilian currency input", () => {
    expect(parseCurrencyInput("R$ 10.490,41")).toBe(10490.41);
    expect(parseCurrencyInput("10490,41")).toBe(10490.41);
    expect(parseCurrencyInput("")).toBe(0);
  });

  it("formats numbers for editable currency input", () => {
    expect(formatCurrencyInput(10490.41)).toBe("10.490,41");
    expect(formatCurrencyInput(0)).toBe("0,00");
    expect(formatCurrencyInput(null)).toBe("0,00");
  });
});
