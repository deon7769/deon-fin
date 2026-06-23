import { describe, expect, it } from "vitest";

import {
  clampPageSize,
  hasTransactionFilters,
  idsFilterFromSearch,
  parseTransactionAmountInput,
  semTagFilterFromSearch,
  transactionCategoryLabel,
  transactionDisplayValue,
  transactionFilterBadges,
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

  it("describes hidden bucket filters so redirected meta filters are visible", () => {
    expect(
      transactionFilterBadges(
        { bucketIds: [2], type: "expense", hidden: "exclude" },
        { buckets: [{ id: 2, name: "Moradia" }] },
      ),
    ).toEqual(["Meta: Moradia", "Tipo: Despesas"]);

    expect(transactionFilterBadges({ bucketIds: [null] }, { buckets: [] })).toEqual([
      "Meta: Sem meta",
    ]);
  });

  it("serializes and labels savings goal filters", () => {
    const filters = { month: "2026-06", savingsGoalIds: [7, null] };

    expect(transactionQuery(filters)).toMatchObject({
      month: "2026-06",
      savings_goal_id: "7,none",
    });
    expect(hasTransactionFilters(filters)).toBe(true);
    expect(
      transactionFilterBadges(filters, {
        savingsGoals: [{ id: 7, name: "Viagem" }],
      }),
    ).toEqual(["Meta poupança: Viagem", "Meta poupança: Sem meta"]);
  });

  it("serializes and labels actionable quality filters", () => {
    const filters = { month: "2026-06", quality: "missing_tag" as const };

    expect(transactionQuery(filters)).toMatchObject({
      month: "2026-06",
      quality: "missing_tag",
    });
    expect(hasTransactionFilters(filters)).toBe(true);
    expect(transactionFilterBadges(filters)).toEqual(["Qualidade: Sem Tag acionável"]);
    expect(transactionFilterBadges({ quality: "missing_bucket" })).toEqual([
      "Qualidade: Sem Meta acionável",
    ]);
  });

  it("prefers transaction display_value over aggregate signed_value", () => {
    expect(transactionDisplayValue({ amount: -300, signed_value: 0, display_value: -300 })).toBe(-300);
    expect(transactionDisplayValue({ amount: -300, signed_value: 0 })).toBe(0);
  });

  it("prefers translated category labels when available", () => {
    expect(transactionCategoryLabel({ category: "Eating out", category_label: "Restaurantes" })).toBe(
      "Restaurantes",
    );
    expect(transactionCategoryLabel({ category: "Shopping", category_label: " " })).toBe("Shopping");
    expect(transactionCategoryLabel({ category: null, category_label: null })).toBe("Sem categoria");
  });

  it("parses transaction amount input without accepting JavaScript numeric quirks", () => {
    expect(parseTransactionAmountInput("1.234,56")).toBe(1234.56);
    expect(parseTransactionAmountInput("1234,56")).toBe(1234.56);
    expect(parseTransactionAmountInput("1234.56")).toBe(1234.56);
    expect(parseTransactionAmountInput("0x10")).toBeNull();
    expect(parseTransactionAmountInput("1e3")).toBeNull();
    expect(parseTransactionAmountInput("abc123")).toBeNull();
    expect(parseTransactionAmountInput("1.2.3")).toBeNull();
    expect(parseTransactionAmountInput("-10")).toBeNull();
    expect(parseTransactionAmountInput("0")).toBeNull();
  });
});
