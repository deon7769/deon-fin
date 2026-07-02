import { beforeEach, describe, expect, it, vi } from "vitest";

const useQueryMock = vi.fn();

vi.mock("@tanstack/react-query", () => ({
  useQuery: useQueryMock,
}));

describe("financial month start day query", () => {
  beforeEach(() => {
    vi.resetModules();
    useQueryMock.mockReset();
    useQueryMock.mockReturnValue({ data: undefined, isError: false, isFetched: false });
  });

  it("keeps the protected profile query disabled while auth is unauthenticated", async () => {
    const { shouldLoadFinancialMonthStartDay, useFinancialMonthStartDayState } = await import(
      "@/hooks/useFinancialMonthStartDay"
    );

    expect(
      shouldLoadFinancialMonthStartDay({
        authEnabled: true,
        authStatus: "unauthenticated",
      }),
    ).toBe(false);

    const result = useFinancialMonthStartDayState({ enabled: false });

    expect(result).toEqual({ startDay: 1, settled: true });
    expect(useQueryMock).toHaveBeenCalledWith(expect.objectContaining({ enabled: false }));
  });

  it("enables the protected profile query once the session is authenticated", async () => {
    const { shouldLoadFinancialMonthStartDay, useFinancialMonthStartDayState } = await import(
      "@/hooks/useFinancialMonthStartDay"
    );

    expect(
      shouldLoadFinancialMonthStartDay({
        authEnabled: true,
        authStatus: "authenticated",
      }),
    ).toBe(true);

    useFinancialMonthStartDayState({ enabled: true });

    expect(useQueryMock).toHaveBeenCalledWith(expect.objectContaining({ enabled: true }));
  });
});
