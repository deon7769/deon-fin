"use client";

import { useMemo } from "react";
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
import { useBuckets } from "@/hooks/useBuckets";
import { useCards, useInvoice } from "@/hooks/useInvoices";
import { useSetBucket } from "@/hooks/useSetBucket";
import { useSetTag } from "@/hooks/useSetTag";
import { useCreateTag } from "@/hooks/useTagMutations";
import { useTags } from "@/hooks/useTags";
import { formatMonthYear } from "@/lib/format";
import { invoiceCategoryLabel } from "@/lib/invoices";
import { usePeriod } from "@/providers/PeriodProvider";
import type { CardItem, InvoiceItem, Tag } from "@/lib/types";

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

export default function FaturasPage() {
  const { month } = usePeriod();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const cardsQuery = useCards();
  const bucketsQuery = useBuckets();
  const tagsQuery = useTags();
  const setBucket = useSetBucket();
  const setTag = useSetTag();
  const createTag = useCreateTag();
  const cards = cardsQuery.data?.items ?? [];
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
              cards={cards}
              value={accountId}
              loading={cardsQuery.isLoading}
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
                  setBucket.mutate({ txId: item.id, bucketId, applyToSimilar })
                }
                onSetTag={(item: InvoiceItem, tagId) =>
                  setTag.mutate({ txId: item.id, tagId })
                }
                onCreateTag={createInlineTag}
              />
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
