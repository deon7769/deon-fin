"use client";

import { CreditCard } from "lucide-react";
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
};

function limitUsage(card: CardItem): number | null {
  if (card.credit_limit === null || card.available === null || card.credit_limit <= 0) {
    return null;
  }
  return ((card.credit_limit - card.available) / card.credit_limit) * 100;
}

export function CardPicker({ cards, value, onChange, loading = false }: CardPickerProps) {
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

  return (
    <div role="radiogroup" aria-label="Selecionar cartão" className="flex gap-3 overflow-x-auto pb-1">
      {cards.map((card) => {
        const selected = card.id === value;
        const detail = cardDetailLine(card);
        const usage = limitUsage(card);

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
          </button>
        );
      })}
    </div>
  );
}
