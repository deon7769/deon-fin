"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/cn";
import { menuItems, otherItems, type NavItem } from "./nav";
import { SidebarFooter } from "./SidebarFooter";

function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

function NavGroup({ title, items }: { title: string; items: NavItem[] }) {
  const pathname = usePathname();

  return (
    <div className="space-y-2">
      <p className="px-3 text-xs font-semibold uppercase text-muted">{title}</p>
      <nav className="space-y-1" aria-label={title}>
        {items.map((item) => {
          const active = isActive(pathname, item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex h-10 items-center gap-3 rounded-md px-3 text-sm font-medium transition",
                active
                  ? "bg-accent text-black"
                  : "text-muted hover:bg-surface2 hover:text-text",
              )}
            >
              <Icon size={18} aria-hidden />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}

export function Sidebar() {
  return (
    <aside className="flex h-screen w-[240px] shrink-0 flex-col border-r border-border bg-surface">
      <div className="border-b border-border px-5 py-5">
        <p className="text-lg font-semibold text-text">deon-fin</p>
      </div>

      <div className="flex-1 space-y-7 overflow-y-auto px-3 py-5">
        <NavGroup title="Menu" items={menuItems} />
        <NavGroup title="Outros" items={otherItems} />
      </div>

      <SidebarFooter />
    </aside>
  );
}
