import { describe, expect, it } from "vitest";

import {
  clampPageSize,
  classificationSourceFilterFromSearch,
  hasTransactionFilters,
  idsFilterFromSearch,
  internalTransferFilterFromSearch,
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

  it("serializes and labels classification source filters", () => {
    const filters = {
      month: "2026-06",
      bucketSources: ["manual", "none"] as const,
      tagSources: ["auto"] as const,
    };

    expect(transactionQuery(filters)).toMatchObject({
      month: "2026-06",
      bucket_source: "manual,none",
      tag_source: "auto",
    });
    expect(hasTransactionFilters(filters)).toBe(true);
    expect(classificationSourceFilterFromSearch("manual,none,bad, auto")).toEqual([
      "manual",
      "none",
      "auto",
    ]);
    expect(classificationSourceFilterFromSearch(null)).toBeUndefined();
    expect(transactionFilterBadges(filters)).toEqual([
      "Origem Meta: Manual",
      "Origem Meta: Sem origem",
      "Origem Tag: Automática",
    ]);
  });

  it("serializes and labels advanced drawer filters from the prints", () => {
    const filters = {
      range: { from: "2026-06-12", to: "2026-06-12" },
      accountIds: ["acc-1", "card-1"],
      amountMin: 50,
      amountMax: 500,
      bucketIds: [null, 2],
      tagIds: [3],
      internalTransfer: "only" as const,
      hidden: "include" as const,
    };

    expect(transactionQuery(filters)).toMatchObject({
      from: "2026-06-12",
      to: "2026-06-12",
      account_ids: "acc-1,card-1",
      min: 50,
      max: 500,
      bucket_ids: "none,2",
      tag_ids: "3",
      internal_transfer: "only",
      hidden: "include",
    });
    expect(hasTransactionFilters(filters)).toBe(true);
    expect(internalTransferFilterFromSearch("only")).toBe("only");
    expect(internalTransferFilterFromSearch("bad")).toBeUndefined();
    expect(
      transactionFilterBadges(filters, {
        accounts: [
          { id: "acc-1", name: "Banco Inter" },
          { id: "card-1", name: "BTG Banking" },
        ],
        buckets: [{ id: 2, name: "Custos Fixos" }],
        tags: [{ id: 3, name: "Mercado" }],
      }),
    ).toEqual([
      "Meta: Sem meta",
      "Meta: Custos Fixos",
      "Tag: Mercado",
      "Conta: Banco Inter",
      "Conta: BTG Banking",
      "Valor: R$ 50 - R$ 500",
      "Ocultas: Incluídas",
      "Transferências internas: Somente internas",
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
