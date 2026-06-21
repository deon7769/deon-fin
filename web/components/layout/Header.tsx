"use client";

import { Eye, EyeOff } from "lucide-react";
import { MonthYearPicker } from "@/components/ui/MonthYearPicker";
import { usePrivacy } from "@/providers/PrivacyProvider";

type HeaderProps = {
  title: string;
  subtitle?: string;
};

export function Header({ title, subtitle }: HeaderProps) {
  const { hidden, toggle } = usePrivacy();
  const label = hidden ? "Mostrar valores" : "Ocultar valores";

  return (
    <header className="flex min-h-20 flex-col items-start justify-between gap-3 border-b border-border bg-bg py-4 pl-14 pr-4 sm:flex-row sm:items-center sm:px-6">
      <div className="min-w-0">
        <h1 className="break-words text-2xl font-semibold text-text">{title}</h1>
        {subtitle ? <p className="mt-1 text-sm text-muted">{subtitle}</p> : null}
      </div>

      <div className="flex w-full shrink-0 items-center gap-2 sm:w-auto">
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
