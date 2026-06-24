"use client";

import { useCallback, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { AlertCircle, ReceiptText } from "lucide-react";
import { CardPicker } from "@/components/faturas/CardPicker";
import { InvoiceHeader } from "@/components/faturas/InvoiceHeader";
import { InvoiceTable } from "@/components/faturas/InvoiceTable";
import { Header } from "@/components/layout/Header";
import { EmptyState } from "@/components/ui/EmptyState";
import { MoneyText } from "@/components/ui/MoneyText";
import { Pill } from "@/components/ui/Pill";
import { SectionCard } from "@/components/ui/SectionCard";
import { Skeleton } from "@/components/ui/Skeleton";
import { useReorderAccounts } from "@/hooks/useAccounts";
import { useBuckets } from "@/hooks/useBuckets";
import { useCards, useInvoice } from "@/hooks/useInvoices";
import { useSetBucket } from "@/hooks/useSetBucket";
import { useSetTag } from "@/hooks/useSetTag";
import { useCreateTag } from "@/hooks/useTagMutations";
import { useTags } from "@/hooks/useTags";
import { formatMonthYear } from "@/lib/format";
import { invoiceCategoryLabel } from "@/lib/invoices";
import { transactionClassificationFeedback } from "@/lib/transactions";
import { usePeriod } from "@/providers/PeriodProvider";
import type { CardItem, InvoiceItem, Tag } from "@/lib/types";

const EMPTY_CARDS: CardItem[] = [];

function RetryState({
  title,
  error,
  onRetry,
}: {
  title: string;
  error: unknown;
  onRetry: () => void;
}) {
  return (
    <SectionCard>
      <EmptyState
        icon={<AlertCircle size={28} aria-hidden />}
        title={title}
        description={error instanceof Error ? error.message : undefined}
        action={
          <button
            type="button"
            onClick={onRetry}
            className="h-9 rounded-md border border-border px-3 text-sm font-medium text-text transition hover:bg-surface2"
          >
            Tentar novamente
          </button>
        }
      />
    </SectionCard>
  );
}

function selectedCardId(cards: CardItem[], accountId: string | null): string | null {
  if (accountId && cards.some((card) => card.id === accountId)) {
    return accountId;
  }
  return cards[0]?.id ?? null;
}

function moveCard(order: string[], cardId: string, direction: -1 | 1): string[] {
  const currentIndex = order.indexOf(cardId);
  const nextIndex = currentIndex + direction;
  if (currentIndex < 0 || nextIndex < 0 || nextIndex >= order.length) {
    return order;
  }

  const next = [...order];
  [next[currentIndex], next[nextIndex]] = [next[nextIndex], next[currentIndex]];
  return next;
}

function sameCardOrderDraft(order: string[], cards: CardItem[]): boolean {
  if (order.length !== cards.length) {
    return false;
  }

  const cardIds = new Set(cards.map((card) => card.id));
  return order.every((cardId) => cardIds.has(cardId));
}

export default function FaturasPage() {
  const { month } = usePeriod();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [orderMode, setOrderMode] = useState(false);
  const [draftOrder, setDraftOrder] = useState<string[]>([]);
  const cardsQuery = useCards();
  const bucketsQuery = useBuckets();
  const tagsQuery = useTags();
  const setBucket = useSetBucket();
  const setTag = useSetTag();
  const createTag = useCreateTag();
  const reorderCards = useReorderAccounts();
  const [classificationStatus, setClassificationStatus] = useState<string | null>(null);
  const cards = cardsQuery.data?.items ?? EMPTY_CARDS;
  const canSaveCardOrder = sameCardOrderDraft(draftOrder, cards);
  const displayCards = useMemo(() => {
    if (!orderMode || draftOrder.length !== cards.length) {
      return cards;
    }

    const byId = new Map(cards.map((card) => [card.id, card]));
    const ordered = draftOrder
      .map((cardId) => byId.get(cardId))
      .filter((card): card is CardItem => Boolean(card));
    return ordered.length === cards.length ? ordered : cards;
  }, [cards, draftOrder, orderMode]);
  const accountId = selectedCardId(cards, searchParams.get("account_id"));
  const invoiceQuery = useInvoice(accountId, month);
  const invoice = invoiceQuery.data;

  const changeCard = (nextAccountId: string) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("account_id", nextAccountId);
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  };

  const createInlineTag = async (name: string): Promise<Tag> =>
    createTag.mutateAsync({ name, color: null });

  const setInvoiceBucket = useCallback(
    async (item: InvoiceItem, bucketId: number | null, applyToSimilar: boolean) => {
      setClassificationStatus("Atualizando Meta...");
      try {
        const result = await setBucket.mutateAsync({ txId: item.id, bucketId, applyToSimilar });
        setClassificationStatus(transactionClassificationFeedback("bucket", result));
      } catch (error) {
        setClassificationStatus(error instanceof Error ? error.message : "Falha ao atualizar Meta.");
      }
    },
    [setBucket],
  );

  const setInvoiceTag = useCallback(
    async (item: InvoiceItem, tagId: number | null, applyToSimilar: boolean) => {
      setClassificationStatus("Atualizando Tag...");
      try {
        const result = await setTag.mutateAsync({ txId: item.id, tagId, applyToSimilar });
        setClassificationStatus(transactionClassificationFeedback("tag", result));
      } catch (error) {
        setClassificationStatus(error instanceof Error ? error.message : "Falha ao atualizar Tag.");
      }
    },
    [setTag],
  );

  const startOrder = () => {
    setDraftOrder(cards.map((card) => card.id));
    setOrderMode(true);
  };

  const cancelOrder = () => {
    setOrderMode(false);
    setDraftOrder([]);
  };

  const saveOrder = () => {
    if (!canSaveCardOrder) {
      cancelOrder();
      return;
    }

    reorderCards.mutate(draftOrder, {
      onSuccess: cancelOrder,
    });
  };

  const categoryTotal = useMemo(
    () => invoice?.by_category.reduce((total, item) => total + item.total, 0) ?? 0,
    [invoice?.by_category],
  );

  return (
    <>
      <Header title="Faturas" subtitle="Acompanhe cada fatura por cartão e mês." />

      <div className="space-y-5 p-4 sm:p-6">
        {cardsQuery.isError ? (
          <RetryState
            title="Não foi possível carregar os cartões"
            error={cardsQuery.error}
            onRetry={() => void cardsQuery.refetch()}
          />
        ) : (
          <SectionCard title="Cartões">
            <CardPicker
              cards={displayCards}
              value={accountId}
              loading={cardsQuery.isLoading}
              orderMode={orderMode}
              savingOrder={reorderCards.isPending}
              canSaveOrder={canSaveCardOrder}
              onStartOrder={cards.length > 1 ? startOrder : undefined}
              onCancelOrder={cancelOrder}
              onSaveOrder={saveOrder}
              onMove={(cardId, direction) =>
                setDraftOrder((current) => moveCard(current, cardId, direction))
              }
              onChange={changeCard}
            />
          </SectionCard>
        )}

        {!cardsQuery.isLoading && !cards.length ? null : invoiceQuery.isError ? (
          <RetryState
            title="Não foi possível carregar a fatura"
            error={invoiceQuery.error}
            onRetry={() => void invoiceQuery.refetch()}
          />
        ) : invoiceQuery.isLoading || !invoice ? (
          <>
            <SectionCard>
              <Skeleton className="h-24 w-full" />
            </SectionCard>
            <SectionCard title="Lançamentos">
              <Skeleton className="h-64 w-full" />
            </SectionCard>
          </>
        ) : (
          <>
            <InvoiceHeader invoice={invoice.invoice} />

            <SectionCard
              title="Lançamentos"
              subtitle={formatMonthYear(invoice.invoice.reference_month)}
            >
              <div className="space-y-3">
                {classificationStatus ? (
                  <div className="rounded-md border border-border bg-surface2 px-4 py-3 text-sm text-muted">
                    {classificationStatus}
                  </div>
                ) : null}
                <InvoiceTable
                  items={invoice.items}
                  buckets={bucketsQuery.data ?? []}
                  tags={tagsQuery.data ?? []}
                  loading={invoiceQuery.isLoading}
                  bucketsLoading={bucketsQuery.isLoading}
                  tagsLoading={tagsQuery.isLoading}
                  savingBucket={setBucket.isPending}
                  savingTag={setTag.isPending || createTag.isPending}
                  onSetBucket={(item: InvoiceItem, bucketId, applyToSimilar) =>
                    void setInvoiceBucket(item, bucketId, applyToSimilar)
                  }
                  onSetTag={(item: InvoiceItem, tagId, applyToSimilar) =>
                    void setInvoiceTag(item, tagId, applyToSimilar)
                  }
                  onCreateTag={createInlineTag}
                />
              </div>
            </SectionCard>

            <SectionCard title="Resumo por categoria">
              {invoice.by_category.length ? (
                <div className="space-y-3">
                  {invoice.by_category.map((item) => (
                    <div
                      key={item.name}
                      className="flex items-center justify-between gap-3 border-b border-border pb-3 last:border-b-0 last:pb-0"
                    >
                      <Pill color={item.color}>{invoiceCategoryLabel(item)}</Pill>
                      <MoneyText value={item.total} className="font-semibold text-negative" />
                    </div>
                  ))}
                  <div className="flex items-center justify-between border-t border-border pt-3 text-sm">
                    <span className="font-medium text-text">Total</span>
                    <MoneyText value={categoryTotal} className="font-semibold text-negative" />
                  </div>
                </div>
              ) : (
                <EmptyState
                  icon={<ReceiptText size={28} aria-hidden />}
                  title="Sem lançamentos nesta fatura"
                  description="Tente outro mês no seletor."
                />
              )}
            </SectionCard>
          </>
        )}
      </div>
    </>
  );
}
