import { describe, expect, it } from "vitest";

import { greetingForHour } from "@/lib/greeting";

describe("greeting helpers", () => {
  it("greets by local hour and profile name", () => {
    expect(greetingForHour(8, "Davi")).toBe("Bom dia, Davi!");
    expect(greetingForHour(14, "Davi")).toBe("Boa tarde, Davi!");
    expect(greetingForHour(21, "Davi")).toBe("Boa noite, Davi!");
  });

  it("falls back when the profile name is empty", () => {
    expect(greetingForHour(9, "")).toBe("Bom dia!");
    expect(greetingForHour(21, "   ")).toBe("Boa noite!");
  });
});
