import { describe, expect, it } from "vitest";
import config from "@/tailwind.config";

describe("tailwind config", () => {
  it("scans lib files that provide shared class helpers", () => {
    expect(config.content).toContain("./lib/**/*.{ts,tsx}");
  });
});
