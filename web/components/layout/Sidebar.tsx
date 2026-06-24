"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, PanelLeftClose, PanelLeftOpen, X } from "lucide-react";
import { cn } from "@/lib/cn";
import {
  SIDEBAR_STORAGE_KEY,
  initialSidebarCollapsed,
  sidebarLabelClass,
  sidebarWidthClass,
  toggleSidebarCollapsed,
} from "@/lib/sidebar";
import { menuItems, otherItems, type NavItem } from "./nav";
import { SidebarFooter } from "./SidebarFooter";

function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

function readStoredSidebarCollapsed() {
  if (typeof window === "undefined") {
    return false;
  }

  try {
    return initialSidebarCollapsed(window.localStorage.getItem(SIDEBAR_STORAGE_KEY));
  } catch {
    return false;
  }
}

function NavGroup({
  title,
  items,
  collapsed,
  onNavigate,
}: {
  title: string;
  items: NavItem[];
  collapsed: boolean;
  onNavigate?: () => void;
}) {
  const pathname = usePathname();

  return (
    <div className="space-y-2">
      <p className={cn("px-3 text-xs font-semibold uppercase text-muted", collapsed && "md:sr-only")}>
        {title}
      </p>
      <nav className="space-y-1" aria-label={title}>
        {items.map((item) => {
          const active = isActive(pathname, item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              prefetch={false}
              aria-current={active ? "page" : undefined}
              title={item.label}
              onClick={onNavigate}
              className={cn(
                "flex h-10 items-center gap-3 rounded-md px-3 text-sm font-medium transition",
                collapsed && "md:justify-center md:px-0",
                active
                  ? "bg-accent text-accentFg"
                  : "text-muted hover:bg-surface2 hover:text-text",
              )}
            >
              <Icon size={18} className="shrink-0" aria-hidden />
              <span className={cn("truncate", sidebarLabelClass(collapsed))}>{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}

function SidebarContent({
  collapsed,
  mobile = false,
  onClose,
  onNavigate,
  onToggleCollapsed,
}: {
  collapsed: boolean;
  mobile?: boolean;
  onClose?: () => void;
  onNavigate?: () => void;
  onToggleCollapsed?: () => void;
}) {
  const desktopCollapsed = collapsed && !mobile;
  const collapseLabel = collapsed ? "Expandir menu" : "Recolher menu";

  return (
    <>
      <div className={cn("border-b border-border py-4", desktopCollapsed ? "px-2" : "px-4")}>
        <div
          className={cn(
            "flex items-center gap-3",
            desktopCollapsed ? "flex-col justify-center" : "justify-between",
          )}
        >
          <Link
            href="/"
            prefetch={false}
            aria-label="Painel"
            title="Painel"
            onClick={onNavigate}
            className={cn(
              "inline-flex min-w-0 items-center rounded-md text-text transition hover:text-accent",
              desktopCollapsed
                ? "h-9 w-9 justify-center bg-accent text-sm font-bold text-accentFg hover:text-accentFg"
                : "text-lg font-semibold",
            )}
          >
            {desktopCollapsed ? (
              <>
                <span aria-hidden>df</span>
                <span className="sr-only">deon-fin</span>
              </>
            ) : (
              <span className="truncate">deon-fin</span>
            )}
          </Link>

          {mobile ? (
            <button
              type="button"
              onClick={onClose}
              aria-label="Fechar menu"
              title="Fechar menu"
              className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-border bg-surface text-muted transition hover:bg-surface2 hover:text-text"
            >
              <X size={18} aria-hidden />
            </button>
          ) : (
            <button
              type="button"
              onClick={onToggleCollapsed}
              aria-label={collapseLabel}
              aria-pressed={collapsed}
              title={collapseLabel}
              className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-border bg-surface text-muted transition hover:bg-surface2 hover:text-text"
            >
              {collapsed ? <PanelLeftOpen size={18} aria-hidden /> : <PanelLeftClose size={18} aria-hidden />}
            </button>
          )}
        </div>
      </div>

      <div className={cn("flex-1 space-y-7 overflow-y-auto py-5", desktopCollapsed ? "px-2" : "px-3")}>
        <NavGroup title="Menu" items={menuItems} collapsed={desktopCollapsed} onNavigate={onNavigate} />
        <NavGroup title="Outros" items={otherItems} collapsed={desktopCollapsed} onNavigate={onNavigate} />
      </div>

      <SidebarFooter collapsed={desktopCollapsed} />
    </>
  );
}

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(readStoredSidebarCollapsed);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    if (!mobileOpen) {
      return undefined;
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setMobileOpen(false);
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [mobileOpen]);

  function handleToggleCollapsed() {
    setCollapsed((current) => {
      const next = toggleSidebarCollapsed(current);
      try {
        window.localStorage.setItem(SIDEBAR_STORAGE_KEY, next ? "1" : "0");
      } catch {
        // The in-memory state should still update if storage is unavailable.
      }
      return next;
    });
  }

  function closeMobile() {
    setMobileOpen(false);
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setMobileOpen(true)}
        aria-label="Abrir menu"
        title="Abrir menu"
        className="fixed left-3 top-4 z-40 inline-flex h-10 w-10 items-center justify-center rounded-md border border-border bg-surface text-muted shadow-lg transition hover:bg-surface2 hover:text-text md:hidden"
      >
        <Menu size={18} aria-hidden />
      </button>

      <div
        aria-hidden="true"
        className={cn(
          "hidden h-screen shrink-0 transition-[width] duration-200 md:block",
          sidebarWidthClass(collapsed),
        )}
      />

      <aside
        className={cn(
          "fixed left-0 top-0 z-30 hidden h-screen flex-col border-r border-border bg-surface transition-[width] duration-200 md:flex",
          sidebarWidthClass(collapsed),
        )}
      >
        <SidebarContent collapsed={collapsed} onToggleCollapsed={handleToggleCollapsed} />
      </aside>

      {mobileOpen ? (
        <div
          className="fixed inset-0 z-50 md:hidden"
          role="dialog"
          aria-modal="true"
          aria-label="Menu de navegação"
        >
          <button
            type="button"
            aria-label="Fechar menu"
            className="absolute inset-0 h-full w-full bg-black/55"
            onClick={closeMobile}
          />
          <aside className="relative flex h-full w-[280px] max-w-[86vw] flex-col border-r border-border bg-surface shadow-2xl">
            <SidebarContent collapsed={false} mobile onClose={closeMobile} onNavigate={closeMobile} />
          </aside>
        </div>
      ) : null}
    </>
  );
}
