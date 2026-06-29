"use client";

import { Eye, EyeOff, Moon, Sun } from "lucide-react";
import { AuthStatus } from "@/components/auth/AuthStatus";
import { useThemeToggle } from "@/hooks/useThemeToggle";
import { cn } from "@/lib/cn";
import { sidebarLabelClass } from "@/lib/sidebar";
import { useOptionalAuth } from "@/providers/AuthProvider";
import { usePrivacy } from "@/providers/PrivacyProvider";

const buttonClass =
  "flex h-10 w-full items-center gap-3 rounded-md px-3 text-sm font-medium text-muted transition hover:bg-surface2 hover:text-text";

export function SidebarFooter({ collapsed = false }: { collapsed?: boolean }) {
  const auth = useOptionalAuth();
  const { hidden, toggle: togglePrivacy } = usePrivacy();
  const { isDark, mounted, toggle: toggleTheme } = useThemeToggle();
  const privacyLabel = hidden ? "Mostrar valores" : "Ocultar valores";

  return (
    <div className="space-y-2 border-t border-border p-3">
      {auth?.enabled && auth.user && auth.family ? (
        <AuthStatus
          collapsed={collapsed}
          loggingOut={auth.status === "loading"}
          user={auth.user}
          family={auth.family}
          onLogout={() => {
            void auth.logout();
          }}
        />
      ) : null}

      <button
        type="button"
        onClick={toggleTheme}
        aria-label="Alternar tema"
        aria-pressed={mounted ? !isDark : undefined}
        title="Alternar tema"
        className={cn(buttonClass, collapsed && "justify-center px-0")}
      >
        {mounted && !isDark ? <Sun size={18} aria-hidden /> : <Moon size={18} aria-hidden />}
        <span className={sidebarLabelClass(collapsed)}>Tema</span>
      </button>

      <button
        type="button"
        onClick={togglePrivacy}
        aria-label={privacyLabel}
        aria-pressed={hidden}
        title={privacyLabel}
        className={cn(buttonClass, collapsed && "justify-center px-0", hidden && "text-text")}
      >
        {hidden ? <EyeOff size={18} aria-hidden /> : <Eye size={18} aria-hidden />}
        <span className={sidebarLabelClass(collapsed)}>Ocultar</span>
      </button>
    </div>
  );
}
