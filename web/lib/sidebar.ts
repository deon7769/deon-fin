export const SIDEBAR_STORAGE_KEY = "deon-fin:sidebar-collapsed";

export function initialSidebarCollapsed(value: string | null): boolean {
  return value === "1" || value === "true";
}

export function sidebarWidthClass(collapsed: boolean): string {
  return collapsed ? "min-w-0 md:w-16" : "min-w-0 md:w-[240px]";
}

export function sidebarLabelClass(collapsed: boolean): string {
  return collapsed ? "md:sr-only" : "";
}

export function toggleSidebarCollapsed(collapsed: boolean): boolean {
  return !collapsed;
}
