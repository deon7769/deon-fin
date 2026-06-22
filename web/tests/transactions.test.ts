import { describe, expect, it } from "vitest";

import {
  clampPageSize,
  hasTransactionFilters,
  idsFilterFromSearch,
  semTagFilterFromSearch,
  transactionDisplayValue,
  transactionQuery,
} from "@/lib/transactions";

describe("transaction helpers", () => {
  it("serializes filters without empty values", () => {
    expect(
      transactionQuery({
        month: "2026-06",
        q: " ifood ",
        hidden: "exclude",
        bucketIds: [1, null],
        tagIds: [],
        page: 2,
        pageSize: 10,
      }),
    ).toEqual({
      month: "2026-06",
      q: "ifood",
      hidden: "exclude",
      bucket_ids: "1,none",
      page: 2,
      page_size: 10,
    });
  });

  it("prefers date range over month and clamps page size", () => {
    expect(
      transactionQuery({
        month: "2026-06",
        range: { from: "2026-05-10", to: "2026-06-10" },
        type: "expense",
        amountMin: 50,
        amountMax: 200,
        hidden: "only",
        page: 0,
        pageSize: 999,
      }),
    ).toEqual({
      from: "2026-05-10",
      to: "2026-06-10",
      type: "expense",
      min: 50,
      max: 200,
      hidden: "only",
      page: 1,
      page_size: 100,
    });
    expect(clampPageSize(25)).toBe(25);
    expect(clampPageSize(0)).toBe(10);
  });

  it("maps semTag=1 to the null tag filter", () => {
    expect(semTagFilterFromSearch("1")).toEqual([null]);
    expect(semTagFilterFromSearch("true")).toEqual([null]);
    expect(semTagFilterFromSearch(null)).toBeUndefined();

    const filters = { month: "2026-06", tagIds: semTagFilterFromSearch("1") };
    expect(transactionQuery(filters)).toMatchObject({
      month: "2026-06",
      tag_ids: "none",
    });
    expect(hasTransactionFilters(filters)).toBe(true);
  });

  it("parses bucket and tag ids from URL search params", () => {
    expect(idsFilterFromSearch("1,none, 2")).toEqual([1, null, 2]);
    expect(idsFilterFromSearch("x,0")).toBeUndefined();
    expect(idsFilterFromSearch(null)).toBeUndefined();
  });

  it("prefers transaction display_value over aggregate signed_value", () => {
    expect(transactionDisplayValue({ amount: -300, signed_value: 0, display_value: -300 })).toBe(-300);
    expect(transactionDisplayValue({ amount: -300, signed_value: 0 })).toBe(0);
  });
});
