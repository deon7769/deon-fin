"use client";

import { LogOut, UserRound } from "lucide-react";
import { cn } from "@/lib/cn";
import { sidebarLabelClass } from "@/lib/sidebar";
import type { AuthFamily, AuthUser } from "@/lib/types";

type AuthStatusProps = {
  collapsed?: boolean;
  loggingOut?: boolean;
  user: AuthUser;
  family: AuthFamily;
  onLogout: () => void;
};

export function AuthStatus({
  collapsed = false,
  loggingOut = false,
  user,
  family,
  onLogout,
}: AuthStatusProps) {
  const label = user.display_name?.trim() || user.email;

  return (
    <div className="space-y-2 border-b border-border pb-3">
      <div
        title={label}
        className={cn(
          "flex min-h-10 items-center gap-3 rounded-md bg-bg px-3 py-2 text-sm text-text",
          collapsed && "justify-center px-0",
        )}
      >
        <UserRound size={18} className="shrink-0 text-muted" aria-hidden />
        <div className={cn("min-w-0", sidebarLabelClass(collapsed))}>
          <p className="truncate font-medium">{label}</p>
          <p className="truncate text-xs text-muted">{family.name}</p>
        </div>
      </div>

      <button
        type="button"
        onClick={onLogout}
        disabled={loggingOut}
        aria-label="Sair"
        title="Sair"
        className={cn(
          "flex h-10 w-full items-center gap-3 rounded-md px-3 text-sm font-medium text-muted transition hover:bg-surface2 hover:text-text disabled:cursor-not-allowed disabled:opacity-60",
          collapsed && "justify-center px-0",
        )}
      >
        <LogOut size={18} aria-hidden />
        <span className={sidebarLabelClass(collapsed)}>{loggingOut ? "Saindo..." : "Sair"}</span>
      </button>
    </div>
  );
}
