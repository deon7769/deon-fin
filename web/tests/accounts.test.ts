import { describe, expect, it } from "vitest";

import {
  accountsRefetchInterval,
  bankAccountLine,
  formatSyncDateTime,
  pluggyItemIdForAccount,
  syncStatusLabel,
  usageLabel,
} from "@/lib/accounts";

describe("account helpers", () => {
  it("formats usage labels", () => {
    expect(usageLabel(18.74)).toBe("18,74%");
    expect(usageLabel(null)).toBe("--");
  });

  it("maps sync statuses to user-facing labels", () => {
    expect(syncStatusLabel("UPDATED")).toBe("Sincronizado");
    expect(syncStatusLabel("LOGIN_ERROR")).toBe("Erro de login");
    expect(syncStatusLabel("DISCONNECTED")).toBe("Desconectado");
    expect(syncStatusLabel("DERIVED")).toBe("Saldo estimado");
    expect(syncStatusLabel("SOMETHING_NEW")).toBe("SOMETHING_NEW");
  });

  it("formats SQLite UTC sync timestamps in Sao Paulo time", () => {
    const formatted = formatSyncDateTime("2026-07-02 18:05:34");

    expect(formatted).toContain("02/07/2026");
    expect(formatted).toContain("15:05");
  });

  it("keeps polling accounts while a sync is running", () => {
    expect(accountsRefetchInterval({ sync: { running: true } })).toBe(2000);
    expect(accountsRefetchInterval({ sync: { running: false } })).toBe(false);
    expect(accountsRefetchInterval(null)).toBe(false);
  });

  it("builds compact bank account lines", () => {
    expect(bankAccountLine("077/0001", "12345-6")).toBe("077/0001 - 12345-6");
    expect(bankAccountLine(null, "12345-6")).toBe("12345-6");
    expect(bankAccountLine(null, null)).toBe("--");
  });

  it("resolves the Pluggy item id for bank accounts and cards", () => {
    const banks = [
      {
        id: "pluggy:bank",
        pluggy_item_id: "item-bank",
      },
    ];
    const cards = [
      {
        id: "pluggy:card",
        pluggy_item_id: "item-card",
      },
    ];

    expect(pluggyItemIdForAccount(banks, cards, "pluggy:bank")).toBe("item-bank");
    expect(pluggyItemIdForAccount(banks, cards, "pluggy:card")).toBe("item-card");
    expect(pluggyItemIdForAccount(banks, cards, "manual:cash")).toBeNull();
  });
});
