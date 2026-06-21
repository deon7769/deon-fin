"use client";

import { Eye, EyeOff } from "lucide-react";
import { MonthYearPicker } from "@/components/ui/MonthYearPicker";
import { usePrivacy } from "@/providers/PrivacyProvider";

export function Header({ title }: { title: string }) {
  const { hidden, toggle } = usePrivacy();
  const label = hidden ? "Mostrar valores" : "Ocultar valores";

  return (
    <header className="flex min-h-20 items-center justify-between border-b border-border bg-bg px-6">
      <div>
        <h1 className="text-2xl font-semibold text-text">{title}</h1>
      </div>

      <div className="flex items-center gap-2">
        <MonthYearPicker />
        <button
          type="button"
          onClick={toggle}
          aria-label={label}
          aria-pressed={hidden}
          title={label}
          className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-border bg-surface text-muted transition hover:bg-surface2 hover:text-text"
        >
          {hidden ? <EyeOff size={17} aria-hidden /> : <Eye size={17} aria-hidden />}
        </button>
      </div>
    </header>
  );
}
