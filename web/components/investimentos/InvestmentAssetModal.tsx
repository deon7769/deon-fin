"use client";

import { FormEvent, useState } from "react";
import { Trash2, X } from "lucide-react";
import {
  buildAssetPayload,
  INVESTMENT_CLASSES,
  isFixedIncomeClass,
  type InvestmentAssetFormValues,
} from "@/lib/investments";
import type { InvestmentAsset, InvestmentAssetInput, InvestmentTickerSearchItem } from "@/lib/types";

type InvestmentAssetModalProps = {
  open: boolean;
  mode: "create" | "edit";
  asset?: InvestmentAsset | null;
  tickerOptions?: InvestmentTickerSearchItem[];
  saving?: boolean;
  deleting?: boolean;
  error?: string | null;
  onClose: () => void;
  onSubmit: (input: InvestmentAssetInput) => void | Promise<void>;
  onDelete?: () => void | Promise<void>;
  onTickerSearchChange?: (query: string) => void;
  onAssetClassChange?: (assetClass: string) => void;
};

function displayNumber(value: number | null | undefined) {
  return value === null || value === undefined ? "" : String(value).replace(".", ",");
}

function isPositiveNumber(value: string) {
  const normalized = value.trim().replace(/\./g, "").replace(",", ".");
  return normalized !== "" && Number.isFinite(Number(normalized)) && Number(normalized) >= 0;
}

export function InvestmentAssetModal({
  open,
  mode,
  asset,
  tickerOptions = [],
  saving = false,
  deleting = false,
  error = null,
  onClose,
  onSubmit,
  onDelete,
  onTickerSearchChange,
  onAssetClassChange,
}: InvestmentAssetModalProps) {
  if (!open) {
    return null;
  }

  return (
    <InvestmentAssetModalContent
      key={`${mode}-${asset?.id ?? "new"}`}
      mode={mode}
      asset={asset}
      tickerOptions={tickerOptions}
      saving={saving}
      deleting={deleting}
      error={error}
      onClose={onClose}
      onSubmit={onSubmit}
      onDelete={onDelete}
      onTickerSearchChange={onTickerSearchChange}
      onAssetClassChange={onAssetClassChange}
    />
  );
}

function InvestmentAssetModalContent({
  mode,
  asset,
  tickerOptions = [],
  saving,
  deleting,
  error,
  onClose,
  onSubmit,
  onDelete,
  onTickerSearchChange,
  onAssetClassChange,
}: Omit<InvestmentAssetModalProps, "open">) {
  const [assetClass, setAssetClass] = useState(asset?.asset_class ?? "acoes_nac");
  const [ticker, setTicker] = useState(asset?.ticker ?? "");
  const [name, setName] = useState(asset?.name ?? "");
  const [quantity, setQuantity] = useState(displayNumber(asset?.quantity));
  const [manualValue, setManualValue] = useState(displayNumber(asset?.manual_value ?? asset?.current_value));
  const [localError, setLocalError] = useState<string | null>(null);
  const fixedIncome = isFixedIncomeClass(assetClass);
  const title = mode === "create" ? "Adicionar ativo" : "Editar ativo";
  const submitLabel = saving ? "Salvando..." : mode === "create" ? "Adicionar" : "Atualizar e fechar";

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const values: InvestmentAssetFormValues = {
      assetClass,
      ticker,
      name,
      quantity,
      manualValue,
    };

    if (fixedIncome) {
      if (!name.trim()) {
        setLocalError("Informe um nome para a renda fixa.");
        return;
      }
      if (!isPositiveNumber(manualValue)) {
        setLocalError("Informe o valor atual.");
        return;
      }
    } else {
      if (!ticker.trim()) {
        setLocalError("Informe o ticker.");
        return;
      }
      if (!isPositiveNumber(quantity)) {
        setLocalError("Informe a quantidade.");
        return;
      }
    }

    setLocalError(null);
    await onSubmit(buildAssetPayload(values));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="investment-asset-modal-title"
        className="w-full max-w-lg rounded-md border border-border bg-surface shadow-2xl"
      >
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <h2 id="investment-asset-modal-title" className="text-base font-semibold text-text">
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Fechar"
            className="inline-flex h-9 w-9 items-center justify-center rounded-md text-muted transition hover:bg-surface2 hover:text-text"
          >
            <X size={17} aria-hidden />
          </button>
        </div>

        <form onSubmit={submit} className="space-y-4 px-5 py-5">
          <label className="block space-y-2">
            <span className="text-sm font-medium text-text">Tipo de investimento</span>
            <select
              value={assetClass}
              onChange={(event) => {
                const next = event.target.value;
                setAssetClass(next);
                onAssetClassChange?.(next);
                setLocalError(null);
              }}
              className="h-10 w-full rounded-md border border-border bg-bg px-3 text-sm text-text outline-none focus:border-blue-500"
            >
              {INVESTMENT_CLASSES.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>

          <div className="grid gap-3 sm:grid-cols-2">
            {fixedIncome ? (
              <label className="block space-y-2 sm:col-span-2">
                <span className="text-sm font-medium text-text">Nome</span>
                <input
                  value={name}
                  onChange={(event) => {
                    setName(event.target.value);
                    setLocalError(null);
                  }}
                  className="h-10 w-full rounded-md border border-border bg-bg px-3 text-sm text-text outline-none placeholder:text-muted focus:border-blue-500"
                  placeholder="Ex.: Tesouro Selic"
                />
              </label>
            ) : (
              <>
                <label className="block space-y-2">
                  <span className="text-sm font-medium text-text">Ticker</span>
                  <input
                    value={ticker}
                    list="investment-ticker-options"
                    onChange={(event) => {
                      const next = event.target.value.toUpperCase();
                      setTicker(next);
                      onTickerSearchChange?.(next);
                      setLocalError(null);
                    }}
                    className="h-10 w-full rounded-md border border-border bg-bg px-3 text-sm uppercase text-text outline-none placeholder:text-muted focus:border-blue-500"
                    placeholder="Ex.: WEGE3"
                  />
                  <datalist id="investment-ticker-options">
                    {tickerOptions.map((item) => (
                      <option key={item.ticker} value={item.ticker}>
                        {item.name}
                      </option>
                    ))}
                  </datalist>
                </label>

                <label className="block space-y-2">
                  <span className="text-sm font-medium text-text">Nome</span>
                  <input
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    className="h-10 w-full rounded-md border border-border bg-bg px-3 text-sm text-text outline-none placeholder:text-muted focus:border-blue-500"
                    placeholder="Opcional"
                  />
                </label>
              </>
            )}

            {fixedIncome ? (
              <label className="block space-y-2 sm:col-span-2">
                <span className="text-sm font-medium text-text">Valor informado</span>
                <input
                  value={manualValue}
                  onChange={(event) => {
                    setManualValue(event.target.value);
                    setLocalError(null);
                  }}
                  inputMode="decimal"
                  className="h-10 w-full rounded-md border border-border bg-bg px-3 text-sm text-text outline-none placeholder:text-muted focus:border-blue-500"
                  placeholder="0,00"
                />
              </label>
            ) : (
              <label className="block space-y-2">
                <span className="text-sm font-medium text-text">Quantidade</span>
                <input
                  value={quantity}
                  onChange={(event) => {
                    setQuantity(event.target.value);
                    setLocalError(null);
                  }}
                  inputMode="decimal"
                  className="h-10 w-full rounded-md border border-border bg-bg px-3 text-sm text-text outline-none placeholder:text-muted focus:border-blue-500"
                  placeholder="0"
                />
              </label>
            )}
          </div>

          {asset?.source === "pluggy" ? (
            <p className="rounded-md border border-blue-400/30 bg-blue-500/10 px-3 py-2 text-xs text-blue-200">
              Alterar a quantidade marca o ativo como ajuste manual. No próximo sync, o Pluggy volta a prevalecer.
            </p>
          ) : null}

          {localError || error ? <p className="text-sm text-negative">{localError ?? error}</p> : null}

          <div className="flex flex-col-reverse gap-2 pt-2 sm:flex-row sm:items-center sm:justify-between">
            {mode === "edit" && onDelete ? (
              <button
                type="button"
                onClick={onDelete}
                disabled={deleting}
                className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-negative/50 px-4 text-sm font-medium text-negative transition hover:bg-negative/10 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <Trash2 size={16} aria-hidden />
                {deleting ? "Removendo..." : "Remover"}
              </button>
            ) : (
              <span />
            )}

            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={onClose}
                className="h-10 rounded-md border border-border px-4 text-sm font-medium text-muted transition hover:bg-surface2 hover:text-text"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={saving}
                className="h-10 rounded-md bg-blue-500 px-4 text-sm font-semibold text-white transition hover:bg-blue-600 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {submitLabel}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
