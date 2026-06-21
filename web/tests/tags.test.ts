import { describe, expect, it } from "vitest";

import { filterTags, isValidTagColor, normalizeTagColorInput, tagById } from "@/lib/tags";
import type { Tag } from "@/lib/types";

const tags: Tag[] = [
  { id: 1, name: "Saúde", color: "#3B82F6", tx_count: 2 },
  { id: 2, name: "Lazer", color: "#9F1239", tx_count: 0 },
  { id: 3, name: "Alimentação", color: "#F5B301", tx_count: 5 },
];

describe("tag helpers", () => {
  it("filters tags ignoring case and accents", () => {
    expect(filterTags(tags, "saude").map((tag) => tag.name)).toEqual(["Saúde"]);
    expect(filterTags(tags, "LAZER").map((tag) => tag.name)).toEqual(["Lazer"]);
    expect(filterTags(tags, "alimentacao").map((tag) => tag.name)).toEqual(["Alimentação"]);
  });

  it("finds a tag by id and treats null as no selection", () => {
    expect(tagById(tags, 2)?.name).toBe("Lazer");
    expect(tagById(tags, null)).toBeNull();
    expect(tagById(tags, 999)).toBeNull();
  });

  it("normalizes and validates hex colors", () => {
    expect(normalizeTagColorInput("  #F5B301  ")).toBe("#f5b301");
    expect(normalizeTagColorInput("")).toBeNull();
    expect(isValidTagColor("#fff")).toBe(true);
    expect(isValidTagColor("#F5B301")).toBe(true);
    expect(isValidTagColor("red")).toBe(false);
    expect(isValidTagColor("ff0000")).toBe(false);
  });
});
