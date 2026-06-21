import { describe, expect, it } from "vitest";

import { currentReferenceMonth, monthOf, monthRange, shiftMonth, yearOf } from "@/lib/period";

describe("period helpers", () => {
  it("computes reference month with the same start-day rule as the backend", () => {
    expect(currentReferenceMonth(new Date(2026, 5, 20), 1)).toBe("2026-06");
    expect(currentReferenceMonth(new Date(2026, 5, 14), 15)).toBe("2026-05");
    expect(currentReferenceMonth(new Date(2026, 5, 15), 15)).toBe("2026-06");
    expect(currentReferenceMonth(new Date(2026, 6, 14), 15)).toBe("2026-06");
    expect(currentReferenceMonth(new Date(2026, 0, 10), 15)).toBe("2025-12");
    expect(currentReferenceMonth(new Date(2027, 0, 5), 15)).toBe("2026-12");
  });

  it("clamps start day to the backend-supported range", () => {
    expect(currentReferenceMonth(new Date(2026, 1, 27), 31)).toBe("2026-01");
    expect(currentReferenceMonth(new Date(2026, 1, 28), 31)).toBe("2026-02");
    expect(currentReferenceMonth(new Date(2026, 5, 1), 0)).toBe("2026-06");
  });

  it("derives civil date ranges for reference months", () => {
    expect(monthRange("2026-06", 1)).toEqual({
      from: "2026-06-01",
      to: "2026-06-30",
    });
    expect(monthRange("2026-06", 15)).toEqual({
      from: "2026-06-15",
      to: "2026-07-14",
    });
    expect(monthRange("2026-12", 15)).toEqual({
      from: "2026-12-15",
      to: "2027-01-14",
    });
  });

  it("shifts year-month values across year boundaries", () => {
    expect(shiftMonth("2026-01", -1)).toBe("2025-12");
    expect(shiftMonth("2026-12", 1)).toBe("2027-01");
    expect(shiftMonth("2026-06", 6)).toBe("2026-12");
  });

  it("extracts year and month values", () => {
    expect(yearOf("2026-06")).toBe(2026);
    expect(monthOf("2026-06")).toBe(6);
  });
});
