"use client";

import { useSyncExternalStore } from "react";
import { useTheme } from "next-themes";

function subscribeMounted() {
  return () => undefined;
}

export function useThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const mounted = useSyncExternalStore(subscribeMounted, () => true, () => false);

  const theme = (mounted ? resolvedTheme : "dark") === "light" ? "light" : "dark";

  return {
    theme,
    isDark: theme === "dark",
    mounted,
    setTheme,
    toggle: () => setTheme(theme === "dark" ? "light" : "dark"),
  };
}
