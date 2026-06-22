"use client";

import { FormEvent, useMemo, useState } from "react";
import { CalendarDays, Save } from "lucide-react";
import { formatCurrencyInput, initialsFor, parseCurrencyInput } from "@/lib/profile";
import type { Profile } from "@/lib/types";
import type { ProfileInput } from "@/hooks/useProfile";

type ProfileFormProps = {
  profile: Profile;
  saving?: boolean;
  error?: string | null;
  savedMessage?: string | null;
  onSubmit: (input: ProfileInput) => Promise<void> | void;
};

function fieldClass(error?: boolean) {
  return [
    "h-10 w-full rounded-md border bg-bg px-3 text-sm text-text outline-none placeholder:text-muted focus:border-accent",
    error ? "border-negative" : "border-border",
  ].join(" ");
}

export function ProfileForm({
  profile,
  saving = false,
  error = null,
  savedMessage = null,
  onSubmit,
}: ProfileFormProps) {
  const [name, setName] = useState(profile.name ?? "");
  const [email, setEmail] = useState(profile.email ?? "");
  const [income, setIncome] = useState(formatCurrencyInput(profile.monthly_income));
  const [startDay, setStartDay] = useState(String(profile.financial_month_start_day ?? 1));
  const [goals, setGoals] = useState(profile.goals_text ?? "");
  const [localError, setLocalError] = useState<string | null>(null);
  const initials = useMemo(() => initialsFor(name), [name]);
  const parsedIncome = parseCurrencyInput(income);
  const numericStartDay = Number.parseInt(startDay, 10);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalizedName = name.trim().replace(/\s+/g, " ");
    const normalizedEmail = email.trim();

    if (normalizedEmail && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(normalizedEmail)) {
      setLocalError("Informe um e-mail válido.");
      return;
    }
    if (!Number.isFinite(parsedIncome) || parsedIncome < 0) {
      setLocalError("Informe uma renda mensal válida.");
      return;
    }
    if (!Number.isInteger(numericStartDay) || numericStartDay < 1 || numericStartDay > 28) {
      setLocalError("Escolha um dia entre 1 e 28.");
      return;
    }

    setLocalError(null);
    await onSubmit({
      name: normalizedName,
      email: normalizedEmail,
      monthly_income: parsedIncome,
      financial_month_start_day: numericStartDay,
      goals_text: goals.trim(),
    });
  };

  return (
    <form onSubmit={submit} className="grid gap-5 lg:grid-cols-[160px_minmax(0,1fr)]">
      <div className="flex flex-col items-center gap-3 rounded-md border border-border bg-bg p-5">
        <div className="flex h-20 w-20 items-center justify-center rounded-full bg-accent text-2xl font-semibold text-accentFg">
          {initials}
        </div>
        <p className="text-center text-sm font-medium text-text">{name.trim() || "Perfil"}</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <label className="space-y-2">
          <span className="text-sm font-medium text-text">Nome</span>
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Seu nome"
            className={fieldClass()}
          />
        </label>

        <label className="space-y-2">
          <span className="text-sm font-medium text-text">E-mail</span>
          <input
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="voce@email.com"
            type="email"
            className={fieldClass(Boolean(localError?.includes("e-mail")))}
          />
        </label>

        <label className="space-y-2">
          <span className="text-sm font-medium text-text">Renda Mensal</span>
          <div className="flex h-10 items-center rounded-md border border-border bg-bg focus-within:border-accent">
            <span className="px-3 text-sm text-muted">R$</span>
            <input
              value={income}
              onChange={(event) => setIncome(event.target.value)}
              onBlur={() => setIncome(formatCurrencyInput(parsedIncome))}
              inputMode="decimal"
              className="min-w-0 flex-1 bg-transparent pr-3 text-sm text-text outline-none"
            />
          </div>
        </label>

        <label className="space-y-2">
          <span className="text-sm font-medium text-text">Início do Mês Financeiro</span>
          <div className="flex h-10 items-center rounded-md border border-border bg-bg focus-within:border-accent">
            <CalendarDays size={16} aria-hidden className="ml-3 shrink-0 text-muted" />
            <input
              value={startDay}
              onChange={(event) => setStartDay(event.target.value)}
              min={1}
              max={28}
              type="number"
              className="min-w-0 flex-1 bg-transparent px-3 text-sm text-text outline-none"
            />
          </div>
        </label>

        <label className="space-y-2 md:col-span-2">
          <span className="text-sm font-medium text-text">Objetivos Financeiros</span>
          <textarea
            value={goals}
            onChange={(event) => setGoals(event.target.value)}
            rows={5}
            placeholder="Ex.: Quitar financiamento; reserva de emergência"
            className="w-full resize-y rounded-md border border-border bg-bg px-3 py-3 text-sm text-text outline-none placeholder:text-muted focus:border-accent"
          />
        </label>

        {localError || error || savedMessage ? (
          <p className={localError || error ? "text-sm text-negative" : "text-sm text-positive"}>
            {localError ?? error ?? savedMessage}
          </p>
        ) : null}

        <div className="flex justify-end md:col-span-2">
          <button
            type="submit"
            disabled={saving}
            className="inline-flex h-10 items-center gap-2 rounded-md bg-accent px-4 text-sm font-semibold text-accentFg transition hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Save size={17} aria-hidden />
            <span>{saving ? "Salvando..." : "Salvar"}</span>
          </button>
        </div>
      </div>
    </form>
  );
}
