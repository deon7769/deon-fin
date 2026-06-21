import { describe, expect, it } from "vitest";

import { bucketById, filterBuckets } from "@/lib/buckets";
import type { Bucket } from "@/lib/types";

const buckets: Bucket[] = [
  { id: 1, key: "liberdade_financeira", name: "Liberdade Financeira", color: "#22C55E" },
  { id: 2, key: "custos_fixos", name: "Custos Fixos", color: "#3B82F6" },
  { id: 6, key: "conhecimento", name: "Conhecimento", color: "#9F1239" },
];

describe("bucket helpers", () => {
  it("filters buckets ignoring case and accents", () => {
    expect(filterBuckets(buckets, "fixos").map((bucket) => bucket.key)).toEqual([
      "custos_fixos",
    ]);
    expect(filterBuckets(buckets, "liberdade").map((bucket) => bucket.key)).toEqual([
      "liberdade_financeira",
    ]);
    expect(filterBuckets(buckets, "CONHECIMENTO").map((bucket) => bucket.key)).toEqual([
      "conhecimento",
    ]);
  });

  it("finds a bucket by id and treats null as no selection", () => {
    expect(bucketById(buckets, 2)?.key).toBe("custos_fixos");
    expect(bucketById(buckets, null)).toBeNull();
    expect(bucketById(buckets, 999)).toBeNull();
  });
});
