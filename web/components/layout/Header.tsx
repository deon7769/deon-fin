import { Eye, CalendarDays } from "lucide-react";

export function Header({ title }: { title: string }) {
  return (
    <header className="flex min-h-20 items-center justify-between border-b border-border bg-bg px-6">
      <div>
        <h1 className="text-2xl font-semibold text-text">{title}</h1>
      </div>

      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled
          title="F0.3"
          className="inline-flex h-10 items-center gap-2 rounded-md border border-border bg-surface px-3 text-sm text-muted opacity-70"
        >
          <CalendarDays size={17} aria-hidden />
          <span>Mês/Ano</span>
        </button>
        <button
          type="button"
          disabled
          title="F0.3"
          className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-border bg-surface text-muted opacity-70"
          aria-label="Ocultar valores"
        >
          <Eye size={17} aria-hidden />
        </button>
      </div>
    </header>
  );
}
