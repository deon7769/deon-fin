"use client";

import { Eye, EyeOff, Moon, Sun } from "lucide-react";
import { useThemeToggle } from "@/hooks/useThemeToggle";
import { cn } from "@/lib/cn";
import { usePrivacy } from "@/providers/PrivacyProvider";

const buttonClass =
  "flex h-10 w-full items-center gap-3 rounded-md px-3 text-sm font-medium text-muted transition hover:bg-surface2 hover:text-text";

export function SidebarFooter() {
  const { hidden, toggle: togglePrivacy } = usePrivacy();
  const { isDark, mounted, toggle: toggleTheme } = useThemeToggle();
  const privacyLabel = hidden ? "Mostrar valores" : "Ocultar valores";

  return (
    <div className="space-y-2 border-t border-border p-3">
      <button
        type="button"
        onClick={toggleTheme}
        aria-label="Alternar tema"
        aria-pressed={mounted ? !isDark : undefined}
        className={buttonClass}
      >
        {mounted && !isDark ? <Sun size={18} aria-hidden /> : <Moon size={18} aria-hidden />}
        <span>Tema</span>
      </button>

      <button
        type="button"
        onClick={togglePrivacy}
        aria-label={privacyLabel}
        aria-pressed={hidden}
        className={cn(buttonClass, hidden && "text-text")}
      >
        {hidden ? <EyeOff size={18} aria-hidden /> : <Eye size={18} aria-hidden />}
        <span>Ocultar</span>
      </button>
    </div>
  );
}
