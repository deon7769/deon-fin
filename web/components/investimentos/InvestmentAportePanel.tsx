"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { Calculator, Check, CircleDollarSign, X } from "lucide-react";

import { MoneyText } from "@/components/ui/MoneyText";
import { Pill } from "@/components/ui/Pill";
import { SectionCard } from "@/components/ui/SectionCard";
import {
  aporteComprasFromSuggestions,
  buildAportePayload,
  INVESTMENT_CLASSES,
} from "@/lib/investments";
import type {
  InvestmentAporteConfirmInput,
  InvestmentAporteResponse,
  InvestmentAporteSuggestion,
  InvestmentTargetsResponse,
} from "@/lib/types";

type InvestmentAportePanelProps = {
  targets: InvestmentTargetsResponse;
  result: InvestmentAporteResponse | null;
  calculating?: boolean;
  confirming?: boolean;
  error?: string | null;
  onCalculate: (input: { aporte: number }) => void | Promise<void>;
  onConfirmAll: (input: InvestmentAporteConfirmInput) => void | Promise<void>;
};

const CLASS_COLORS: Record<string, string> = {
  acoes_nac: "#3b82f6",
  fii: "#22c55e",
  rf: "#f59e0b",
  cripto: "#a855f7",
  acoes_int: "#06b6d4",
  reit: "#ef4444",
  rf_int: "#84cc16",
};

function displayNumber(value: number | null | undefined) {
  return value === null || value === undefined ? "" : String(value).replace(".", ",");
}

function parseNumber(value: string) {
  const parsed = Number(value.trim().replace(/\./g, "").replace(",", "."));
  return Number.isFinite(parsed) ? parsed : 0;
}

function classLabel(assetClass: string) {
  return INVESTMENT_CLASSES.find((item) => item.value === assetClass)?.label ?? assetClass;
}

function scoreText(value: number | null) {
  return value === null ? "--" : Number(value.toFixed(2)).toString();
}

function ConfirmModal({
  suggestion,
  confirming,
  onClose,
  onConfirm,
}: {
  suggestion: InvestmentAporteSuggestion;
  confirming: boolean;
  onClose: () => void;
  onConfirm: (input: InvestmentAporteConfirmInput) => void | Promise<void>;
}) {
  const [quantity, setQuantity] = useState(displayNumber(suggestion.sugest_un));
  const quantidade = parseNumber(quantity);
  const aporte = Number((quantidade * suggestion.preco).toFixed(2));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="investment-aporte-modal-title"
        className="w-full max-w-md rounded-md border border-border bg-surface shadow-2xl"
      >
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <h2 id="investment-aporte-modal-title" className="text-base font-semibold text-text">
            Novo aporte
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Fechar"
            title="Fechar"
            className="inline-flex h-9 w-9 items-center justify-center rounded-md text-muted transition hover:bg-surface2 hover:text-text"
          >
            <X size={17} aria-hidden />
          </button>
        </div>
        <div className="space-y-4 px-5 py-5">
          <div>
            <p className="text-sm text-muted">Ativo</p>
            <p className="text-lg font-semibold text-text">{suggestion.ticker ?? suggestion.asset_class}</p>
          </div>
          <label className="block space-y-2">
            <span className="text-sm font-medium text-text">Quantidade a ser aportada</span>
            <input
              value={quantity}
              onChange={(event) => setQuantity(event.target.value)}
              inputMode="decimal"
              className="h-10 w-full rounded-md border border-border bg-bg px-3 text-sm text-text outline-none focus:border-blue-500"
            />
          </label>
          <p className="rounded-md border border-blue-400/30 bg-blue-500/10 px-3 py-2 text-xs text-blue-200">
            Quantidade sugerida: {displayNumber(suggestion.sugest_un)}, valor sugerido:{" "}
            <MoneyText value={suggestion.sugest_rs} />
          </p>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="h-10 rounded-md border border-border px-4 text-sm font-medium text-muted transition hover:bg-surface2 hover:text-text"
            >
              Cancelar
            </button>
            <button
              type="button"
              disabled={confirming || quantidade <= 0}
              onClick={() =>
                onConfirm({
                  aporte,
                  compras: [{ asset_id: suggestion.id, quantidade }],
                })
              }
              className="inline-flex h-10 items-center gap-2 rounded-md bg-blue-500 px-4 text-sm font-semibold text-white transition hover:bg-blue-600 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Check size={16} aria-hidden />
              {confirming ? "Aportando..." : "Aportar"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export function InvestmentAportePanel({
  targets,
  result,
  calculating = false,
  confirming = false,
  error = null,
  onCalculate,
  onConfirmAll,
}: InvestmentAportePanelProps) {
  const [aporte, setAporte] = useState(displayNumber(targets.ultimo_aporte ?? 0));
  const [selected, setSelected] = useState<InvestmentAporteSuggestion | null>(null);
  const hasExecutableSuggestions = Boolean(
    result?.sugestoes.some((item) => item.sugest_un > 0 && item.sugest_rs > 0),
  );

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void onCalculate(buildAportePayload(aporte));
  };

  const confirm = async (input: InvestmentAporteConfirmInput) => {
    await onConfirmAll(input);
    setSelected(null);
  };

  if (!targets.valid) {
    return (
      <SectionCard title="Novo Aporte">
        <div className="rounded-md border border-amber-400/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
          Para calcular um aporte, ajuste as Metas da carteira para 100%.
          <Link href="/investimentos/metas" className="ml-2 font-semibold text-blue-200 underline">
            /investimentos/metas
          </Link>
        </div>
      </SectionCard>
    );
  }

  return (
    <div className="space-y-4">
      <SectionCard title="Novo Aporte" subtitle="Quanto voce vai investir?">
        <form onSubmit={submit} className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <label className="block flex-1 space-y-2">
            <span className="text-sm font-medium text-text">Valor do investimento</span>
            <input
              value={aporte}
              onChange={(event) => setAporte(event.target.value)}
              inputMode="decimal"
              className="h-10 w-full rounded-md border border-border bg-bg px-3 text-sm text-text outline-none focus:border-blue-500"
              placeholder="0,00"
            />
          </label>
          <button
            type="submit"
            disabled={calculating || parseNumber(aporte) <= 0}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-blue-500 px-4 text-sm font-semibold text-white transition hover:bg-blue-600 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Calculator size={16} aria-hidden />
            {calculating ? "Calculando..." : "Calcular"}
          </button>
        </form>
        {error ? <p className="mt-3 text-sm text-negative">{error}</p> : null}
      </SectionCard>

      {result ? (
        <>
          <SectionCard title="Distribuicao do investimento">
            <div className="grid gap-3 md:grid-cols-3">
              <div className="rounded-md border border-border bg-bg p-4">
                <p className="text-sm text-muted">Patrimonio atual</p>
                <MoneyText value={result.patrimonio} className="mt-1 block text-2xl font-semibold" />
              </div>
              <div className="rounded-md border border-border bg-bg p-4">
                <p className="text-sm text-muted">Patrimonio total</p>
                <MoneyText value={result.pl_alvo} className="mt-1 block text-2xl font-semibold" />
              </div>
              <div className="rounded-md border border-border bg-bg p-4">
                <p className="text-sm text-muted">Troco</p>
                <MoneyText value={result.troco} className="mt-1 block text-2xl font-semibold" />
              </div>
            </div>
          </SectionCard>

          <SectionCard
            title="Sugestoes de investimento"
            actions={
              <button
                type="button"
                onClick={() => void onConfirmAll(aporteComprasFromSuggestions(result))}
                disabled={confirming || !hasExecutableSuggestions}
                className="inline-flex h-9 items-center gap-2 rounded-md bg-blue-500 px-3 text-sm font-medium text-white transition hover:bg-blue-600 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <CircleDollarSign size={16} aria-hidden />
                {confirming ? "Aportando..." : "Aportar tudo"}
              </button>
            }
          >
            {hasExecutableSuggestions ? (
              <div className="overflow-x-auto">
                <table className="min-w-[1060px] w-full border-collapse text-sm">
                  <thead>
                    <tr className="border-b border-border text-left text-xs font-semibold uppercase tracking-normal text-muted">
                      <th className="py-3 pr-4">Tipo</th>
                      <th className="px-4 py-3">Ticker</th>
                      <th className="px-4 py-3 text-right">Atual</th>
                      <th className="px-4 py-3 text-right">Preco atual</th>
                      <th className="px-4 py-3 text-right">Nota</th>
                      <th className="px-4 py-3 text-right">Total apos aporte</th>
                      <th className="px-4 py-3 text-right">Sugest. R$</th>
                      <th className="px-4 py-3 text-right">Sugest. un</th>
                      <th className="py-3 pl-4 text-right">Acao</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.sugestoes.map((item) => (
                      <tr key={item.id} className="border-b border-border last:border-0">
                        <td className="py-3 pr-4">
                          <Pill color={CLASS_COLORS[item.asset_class]}>{classLabel(item.asset_class)}</Pill>
                        </td>
                        <td className="px-4 py-3 font-medium text-text">{item.ticker ?? "--"}</td>
                        <td className="px-4 py-3 text-right">
                          <MoneyText value={item.valor_atual} />
                        </td>
                        <td className="px-4 py-3 text-right">
                          <MoneyText value={item.preco} />
                        </td>
                        <td className="px-4 py-3 text-right tabular-nums text-text">{scoreText(item.nota)}</td>
                        <td className="px-4 py-3 text-right tabular-nums text-text">
                          {item.total_apos_aporte_pct.toFixed(2)}%
                        </td>
                        <td className="px-4 py-3 text-right font-medium">
                          <MoneyText value={item.sugest_rs} />
                        </td>
                        <td className="px-4 py-3 text-right tabular-nums text-text">{displayNumber(item.sugest_un)}</td>
                        <td className="py-3 pl-4 text-right">
                          <button
                            type="button"
                            onClick={() => setSelected(item)}
                            disabled={item.sugest_un <= 0}
                            className="h-9 rounded-md border border-blue-400/40 bg-blue-500/10 px-3 text-sm font-medium text-blue-200 transition hover:bg-blue-500/20 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            Aportar!
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="rounded-md border border-dashed border-border bg-bg px-4 py-5 text-sm text-muted">
                <p className="font-medium text-text">Nenhuma sugestao executavel para este aporte.</p>
                <p className="mt-1">Ajuste ativos, precos ou metas antes de confirmar.</p>
              </div>
            )}
          </SectionCard>
        </>
      ) : null}

      {selected ? (
        <ConfirmModal
          suggestion={selected}
          confirming={confirming}
          onClose={() => setSelected(null)}
          onConfirm={confirm}
        />
      ) : null}
    </div>
  );
}
