import { describe, expect, it } from "vitest";

import { hasUntaggedSlice } from "@/lib/painel";
import type { PainelTagSlice } from "@/lib/types";

describe("painel helpers", () => {
  it("detects when the tag donut has uncategorized transactions", () => {
    const tagged: PainelTagSlice = {
      tag_id: 1,
      tag_name: "Alimentação",
      color: "#f5b301",
      total: 100,
    };
    const untagged: PainelTagSlice = {
      tag_id: null,
      tag_name: "Sem Tags",
      color: null,
      total: 50,
    };

    expect(hasUntaggedSlice([tagged])).toBe(false);
    expect(hasUntaggedSlice([tagged, untagged])).toBe(true);
    expect(hasUntaggedSlice([])).toBe(false);
  });
});
