import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { Sidebar } from "@/components/layout/Sidebar";
import { PrivacyProvider } from "@/providers/PrivacyProvider";
import {
  SIDEBAR_STORAGE_KEY,
  initialSidebarCollapsed,
  sidebarLabelClass,
  sidebarWidthClass,
  toggleSidebarCollapsed,
} from "@/lib/sidebar";

vi.mock("next/navigation", () => ({
  usePathname: () => "/transacoes",
}));

describe("sidebar helpers", () => {
  it("uses a stable storage key for the collapsed state", () => {
    expect(SIDEBAR_STORAGE_KEY).toBe("deon-fin:sidebar-collapsed");
  });

  it("parses the persisted collapsed state conservatively", () => {
    expect(initialSidebarCollapsed(null)).toBe(false);
    expect(initialSidebarCollapsed("0")).toBe(false);
    expect(initialSidebarCollapsed("1")).toBe(true);
    expect(initialSidebarCollapsed("true")).toBe(true);
  });

  it("returns desktop width classes for expanded and collapsed states", () => {
    expect(sidebarWidthClass(false)).toContain("md:w-[240px]");
    expect(sidebarWidthClass(true)).toContain("md:w-16");
  });

  it("allows the collapsed rail to shrink inside the app flex shell", () => {
    expect(sidebarWidthClass(true)).toContain("min-w-0");
  });

  it("keeps collapsed labels available to screen readers", () => {
    expect(sidebarLabelClass(false)).toBe("");
    expect(sidebarLabelClass(true)).toContain("md:sr-only");
  });

  it("toggles the collapsed state", () => {
    expect(toggleSidebarCollapsed(false)).toBe(true);
    expect(toggleSidebarCollapsed(true)).toBe(false);
  });

  it("keeps the desktop sidebar pinned while page content scrolls", () => {
    const html = renderToStaticMarkup(createElement(PrivacyProvider, null, createElement(Sidebar)));

    expect(html).toContain("sticky top-0");
    expect(html).toContain("h-screen");
    expect(html).toContain("transition-[width]");
  });
});
