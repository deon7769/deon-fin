"use client";

import { useMemo, useState } from "react";
import { RotateCcw, Save } from "lucide-react";

import { SectionCard } from "@/components/ui/SectionCard";
import {
  investmentTargetStatus,
  sumInvestmentTargets,
  targetsFromProfile,
} from "@/lib/investments";
import { cn } from "@/lib/cn";
import type {
  InvestmentProfilePreset,
  InvestmentTargetClass,
  InvestmentTargetsMap,
  InvestmentTargetsResponse,
} from "@/lib/types";

type InvestmentTargetsPanelProps = {
  targets: InvestmentTargetsResponse;
  profiles: InvestmentProfilePreset[];
  saving?: boolean;
  error?: string | null;
  onSave: (input: { targets: InvestmentTargetsMap; perfil?: string }) => void | Promise<void>;
};

function formatPct(value: number) {
  return Number(value.toFixed(2)).toString();
}

function profileMatchesDraft(profile: InvestmentProfilePreset, draft: InvestmentTargetsMap) {
  return Object.entries(profile.targets).every(
    ([key, value]) => Math.abs(Number(draft[key] ?? 0) - Number(value)) < 0.001,
  );
}

function DonutSummary({
  total,
  classes,
  draft,
}: {
  total: number;
  classes: InvestmentTargetClass[];
  draft: InvestmentTargetsMap;
}) {
  const status = investmentTargetStatus(total);
  const ringColor =
    status.state === "valid" ? "#3b82f6" : status.state === "over" ? "#ef4444" : "#f59e0b";
  const clamped = Math.min(total, 100);
  const background = `conic-gradient(${ringColor} ${clamped}%, #27272a ${clamped}% 100%)`;

  return (
    <div className="grid gap-5 lg:grid-cols-[260px_1fr]">
      <div className="flex items-center justify-center">
        <div
          className="flex h-56 w-56 items-center justify-center rounded-full p-5"
          style={{ background }}
          aria-label={`Total: ${formatPct(total)}%`}
        >
          <div className="flex h-full w-full flex-col items-center justify-center rounded-full bg-surface text-center">
            <span className="text-xs font-medium uppercase tracking-normal text-muted">Total</span>
            <span className="mt-1 text-3xl font-semibold text-text">Total: {formatPct(total)}%</span>
            <span
              className={cn(
                "mt-2 max-w-40 text-xs",
                status.state === "valid" && "text-blue-200",
                status.state === "under" && "text-amber-200",
                status.state === "over" && "text-negative",
              )}
            >
              {status.message}
            </span>
          </div>
        </div>
      </div>

      <div className="grid content-start gap-2 sm:grid-cols-2">
        {classes.map((item) => (
          <div key={item.asset_class} className="flex items-center justify-between border-b border-border py-2">
            <span className="text-sm text-muted">{item.label}</span>
            <span className="text-sm font-semibold text-text">{formatPct(Number(draft[item.asset_class] ?? 0))}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function InvestmentTargetsPanel({
  targets,
  profiles,
  saving = false,
  error = null,
  onSave,
}: InvestmentTargetsPanelProps) {
  const [draft, setDraft] = useState<InvestmentTargetsMap>(targets.targets);
  const [perfil, setPerfil] = useState(targets.perfil);

  const total = useMemo(() => sumInvestmentTargets(draft), [draft]);
  const status = investmentTargetStatus(total);
  const matchedProfile = profiles.find((profile) => profileMatchesDraft(profile, draft));

  const setTarget = (assetClass: string, value: number) => {
    setDraft((current) => ({ ...current, [assetClass]: value }));
    setPerfil("custom");
  };

  const applyProfile = (profile: InvestmentProfilePreset) => {
    setDraft(targetsFromProfile(profile));
    setPerfil(profile.key);
  };

  const reset = () => {
    setDraft(targets.targets);
    setPerfil(targets.perfil);
  };

  return (
    <div className="space-y-4">
      <SectionCard
        title="Metas de Investimento"
        subtitle="Edite os itens abaixo para ajustar suas metas de alocação por classe."
      >
        <div className="grid gap-3 md:grid-cols-3">
          {profiles.map((profile) => {
            const selected = (matchedProfile?.key ?? perfil) === profile.key;
            return (
              <button
                key={profile.key}
                type="button"
                onClick={() => applyProfile(profile)}
                className={cn(
                  "rounded-md border p-4 text-left transition",
                  selected
                    ? "border-blue-400 bg-blue-500/10"
                    : "border-border bg-surface2 hover:border-blue-400/50",
                )}
              >
                <span className="text-sm font-semibold text-text">{profile.label}</span>
                <span className="mt-2 block text-xs leading-5 text-muted">{profile.description}</span>
              </button>
            );
          })}
        </div>
      </SectionCard>

      <SectionCard title="Distribuição alvo" subtitle="A soma precisa fechar exatamente 100%.">
        <DonutSummary total={total} classes={targets.classes} draft={draft} />
      </SectionCard>

      <SectionCard title="Classes" subtitle="Ajuste os percentuais alvo para o próximo aporte.">
        <div className="space-y-4">
          {targets.classes.map((item) => {
            const value = Number(draft[item.asset_class] ?? 0);
            return (
              <label key={item.asset_class} className="grid gap-2 md:grid-cols-[220px_1fr_76px] md:items-center">
                <span className="text-sm font-medium text-text">{item.label}</span>
                <input
                  type="range"
                  min={0}
                  max={100}
                  step={1}
                  value={value}
                  onChange={(event) => setTarget(item.asset_class, Number(event.target.value))}
                  className="h-2 accent-blue-500"
                />
                <input
                  type="number"
                  min={0}
                  max={100}
                  step={1}
                  value={value}
                  onChange={(event) => setTarget(item.asset_class, Number(event.target.value))}
                  className="h-9 rounded-md border border-border bg-bg px-2 text-right text-sm text-text outline-none focus:border-blue-500"
                  aria-label={`Percentual de ${item.label}`}
                />
              </label>
            );
          })}
        </div>

        {error ? <p className="mt-4 text-sm text-negative">{error}</p> : null}

        <div className="mt-5 flex flex-col gap-2 sm:flex-row sm:justify-end">
          <button
            type="button"
            onClick={reset}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-border px-3 text-sm font-medium text-muted transition hover:bg-surface2 hover:text-text"
          >
            <RotateCcw size={16} aria-hidden />
            Resetar valores
          </button>
          <button
            type="button"
            onClick={() => onSave({ targets: draft, perfil: matchedProfile?.key ?? perfil })}
            disabled={!status.canSave || saving}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-blue-500 px-3 text-sm font-semibold text-white transition hover:bg-blue-600 disabled:cursor-not-allowed disabled:bg-zinc-600 disabled:text-zinc-300"
          >
            <Save size={16} aria-hidden />
            {saving ? "Salvando..." : "Salvar"}
          </button>
        </div>
      </SectionCard>
    </div>
  );
}
