"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/cn";

const TABS = [
  { href: "/investimentos", label: "Ativos" },
  { href: "/investimentos/metas", label: "Metas da carteira" },
];

export function InvestmentTabs() {
  const pathname = usePathname();

  return (
    <nav className="flex flex-wrap gap-2 border-b border-border pb-3" aria-label="Investimentos">
      {TABS.map((tab) => {
        const active = pathname === tab.href;
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={cn(
              "inline-flex h-9 items-center rounded-md border px-3 text-sm font-medium transition",
              active
                ? "border-blue-400 bg-blue-500/15 text-blue-100"
                : "border-border text-muted hover:bg-surface2 hover:text-text",
            )}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
