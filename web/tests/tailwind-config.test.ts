import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import config from "@/tailwind.config";

function sourceFiles(dir: string): string[] {
  const path = join(process.cwd(), dir);
  if (!existsSync(path)) {
    return [];
  }
  return readdirSync(path).flatMap((entry) => {
    const fullPath = join(path, entry);
    if (statSync(fullPath).isDirectory()) {
      return sourceFiles(join(dir, entry));
    }
    return fullPath.endsWith(".tsx") || fullPath.endsWith(".ts") ? [fullPath] : [];
  });
}

describe("tailwind config", () => {
  it("scans lib files that provide shared class helpers", () => {
    expect(config.content).toContain("./lib/**/*.{ts,tsx}");
  });

  it("uses the blue primary accent token with an explicit foreground", () => {
    const colors = config.theme?.extend?.colors as Record<string, string>;
    const globals = readFileSync(join(process.cwd(), "app", "globals.css"), "utf8");

    expect(colors.accent).toBe("var(--color-accent)");
    expect(colors.accentFg).toBe("var(--color-accent-fg)");
    expect(globals).toContain("--color-accent: #2563eb");
    expect(globals).toContain("--color-accent-fg: #ffffff");
    expect(globals).not.toContain("#f5b301");
    expect(globals).not.toContain("#b57e00");
  });

  it("does not use legacy accent variable or black text on primary accent", () => {
    for (const filePath of [...sourceFiles("app"), ...sourceFiles("components")]) {
      const source = readFileSync(filePath, "utf8");
      expect(source, filePath).not.toContain("accent-[var(--accent)]");
      expect(source, filePath).not.toMatch(/bg-accent[^"`']*text-black|text-black[^"`']*bg-accent/);
    }
  });
});
