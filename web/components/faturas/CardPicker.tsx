"use client";

import { ArrowDown, ArrowUp, CreditCard } from "lucide-react";
import { EmptyState } from "@/components/ui/EmptyState";
import { MoneyText } from "@/components/ui/MoneyText";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { Skeleton } from "@/components/ui/Skeleton";
import { cardDetailLine } from "@/lib/invoices";
import { cn } from "@/lib/cn";
import type { CardItem } from "@/lib/types";

type CardPickerProps = {
  cards: CardItem[];
  value: string | null;
  onChange: (accountId: string) => void;
  loading?: boolean;
  orderMode?: boolean;
  savingOrder?: boolean;
  canSaveOrder?: boolean;
  onStartOrder?: () => void;
  onCancelOrder?: () => void;
  onSaveOrder?: () => void;
  onMove?: (cardId: string, direction: -1 | 1) => void;
};

function limitUsage(card: CardItem): number | null {
  if (card.credit_limit === null || card.available === null || card.credit_limit <= 0) {
    return null;
  }
  return ((card.credit_limit - card.available) / card.credit_limit) * 100;
}

function CardBody({ card }: { card: CardItem }) {
  const detail = cardDetailLine(card);
  const usage = limitUsage(card);

  return (
    <>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-text">{card.name}</p>
          {detail ? <p className="mt-1 text-xs text-muted">{detail}</p> : null}
        </div>
        <CreditCard size={17} aria-hidden className="shrink-0 text-muted" />
      </div>

      {usage !== null && card.credit_limit !== null && card.available !== null ? (
        <div className="mt-5 space-y-2">
          <ProgressBar value={usage} />
          <p className="text-xs text-muted">
            Disponível <MoneyText value={card.available} /> de{" "}
            <MoneyText value={card.credit_limit} />
          </p>
        </div>
      ) : (
        <p className="mt-5 text-xs text-muted">Limite indisponível</p>
      )}
    </>
  );
}

export function CardPicker({
  cards,
  value,
  onChange,
  loading = false,
  orderMode = false,
  savingOrder = false,
  canSaveOrder = true,
  onStartOrder,
  onCancelOrder,
  onSaveOrder,
  onMove,
}: CardPickerProps) {
  if (loading) {
    return (
      <div className="flex gap-3 overflow-x-auto pb-1">
        <Skeleton className="h-32 min-w-64" />
        <Skeleton className="h-32 min-w-64" />
        <Skeleton className="h-32 min-w-64" />
      </div>
    );
  }

  if (!cards.length) {
    return (
      <EmptyState
        icon={<CreditCard size={28} aria-hidden />}
        title="Nenhum cartão"
        description="Conecte um cartão de crédito ou importe uma fatura para vê-la aqui."
      />
    );
  }

  if (orderMode) {
    return (
      <div className="space-y-3">
        <div className="flex flex-wrap items-center justify-end gap-2">
          <button
            type="button"
            onClick={onCancelOrder}
            disabled={savingOrder}
            className="inline-flex h-9 items-center rounded-md border border-border px-3 text-sm font-medium text-muted transition hover:bg-surface2 hover:text-text disabled:cursor-not-allowed disabled:opacity-50"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={onSaveOrder}
            disabled={savingOrder || !canSaveOrder}
            className="inline-flex h-9 items-center rounded-md bg-accent px-3 text-sm font-semibold text-black transition hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {savingOrder ? "Salvando..." : "Salvar ordem"}
          </button>
        </div>

        <div role="list" aria-label="Ordenar cartões" className="flex gap-3 overflow-x-auto pb-1">
          {cards.map((card, index) => (
            <article
              key={card.id}
              role="listitem"
              className={cn(
                "min-h-32 min-w-64 rounded-card border p-4 text-left transition",
                card.id === value ? "border-accent bg-surface2 shadow-sm" : "border-border bg-bg",
              )}
            >
              <CardBody card={card} />
              <div className="mt-4 flex justify-end gap-2 border-t border-border pt-3">
                <button
                  type="button"
                  onClick={() => onMove?.(card.id, -1)}
                  disabled={savingOrder || index === 0}
                  aria-label={`Mover ${card.name} para cima`}
                  title="Mover para cima"
                  className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-border text-muted transition hover:bg-surface2 hover:text-text disabled:cursor-not-allowed disabled:opacity-40"
                >
                  <ArrowUp size={15} aria-hidden />
                </button>
                <button
                  type="button"
                  onClick={() => onMove?.(card.id, 1)}
                  disabled={savingOrder || index === cards.length - 1}
                  aria-label={`Mover ${card.name} para baixo`}
                  title="Mover para baixo"
                  className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-border text-muted transition hover:bg-surface2 hover:text-text disabled:cursor-not-allowed disabled:opacity-40"
                >
                  <ArrowDown size={15} aria-hidden />
                </button>
              </div>
            </article>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {onStartOrder ? (
        <div className="flex justify-end">
          <button
            type="button"
            onClick={onStartOrder}
            className="inline-flex h-9 items-center rounded-md border border-border px-3 text-sm font-medium text-muted transition hover:bg-surface2 hover:text-text"
          >
            Ordenar cartões
          </button>
        </div>
      ) : null}

      <div role="radiogroup" aria-label="Selecionar cartão" className="flex gap-3 overflow-x-auto pb-1">
        {cards.map((card) => {
          const selected = card.id === value;

          return (
            <button
              key={card.id}
              type="button"
              role="radio"
              aria-checked={selected}
              onClick={() => onChange(card.id)}
              className={cn(
                "min-h-32 min-w-64 rounded-card border p-4 text-left transition",
                selected
                  ? "border-accent bg-surface2 shadow-sm"
                  : "border-border bg-bg hover:bg-surface2",
              )}
            >
              <CardBody card={card} />
            </button>
          );
        })}
      </div>
    </div>
  );
}
