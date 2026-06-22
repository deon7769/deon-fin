"use client";

import { useMemo } from "react";
import { BucketSelect } from "@/components/ui/BucketSelect";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { MoneyText } from "@/components/ui/MoneyText";
import { TagSelect } from "@/components/ui/TagSelect";
import { formatDate } from "@/lib/format";
import { installmentLabel, invoiceItemCategoryLabel } from "@/lib/invoices";
import type { Bucket, InvoiceItem, Tag } from "@/lib/types";

type InvoiceTableProps = {
  items: InvoiceItem[];
  buckets: Bucket[];
  tags: Tag[];
  loading?: boolean;
  bucketsLoading?: boolean;
  tagsLoading?: boolean;
  savingBucket?: boolean;
  savingTag?: boolean;
  onSetBucket: (item: InvoiceItem, bucketId: number | null, applyToSimilar: boolean) => void;
  onSetTag: (item: InvoiceItem, tagId: number | null) => void;
  onCreateTag: (name: string) => Promise<Tag>;
};

export function InvoiceTable({
  items,
  buckets,
  tags,
  loading = false,
  bucketsLoading = false,
  tagsLoading = false,
  savingBucket = false,
  savingTag = false,
  onSetBucket,
  onSetTag,
  onCreateTag,
}: InvoiceTableProps) {
  const columns = useMemo<DataTableColumn<InvoiceItem>[]>(
    () => [
      {
        key: "date",
        header: "Data",
        className: "min-w-[110px] px-3 py-3 align-top",
        cell: (item) => <span className="text-muted">{formatDate(item.date)}</span>,
      },
      {
        key: "description",
        header: "Descrição",
        className: "min-w-[260px] px-3 py-3 align-top",
        cell: (item) => (
          <div className="min-w-0">
            <p className="truncate font-medium text-text" title={item.description}>
              {item.description}
            </p>
            <p className="mt-1 text-xs text-muted">{invoiceItemCategoryLabel(item)}</p>
          </div>
        ),
      },
      {
        key: "amount",
        header: "Valor",
        className: "min-w-[130px] px-3 py-3 text-right align-top",
        cell: (item) => (
          <MoneyText value={item.amount} className="font-semibold text-negative" />
        ),
      },
      {
        key: "bucket",
        header: "Meta",
        className: "min-w-[190px] px-3 py-3 align-top",
        cell: (item) => (
          <BucketSelect
            value={item.bucket?.id ?? null}
            options={buckets}
            disabled={savingBucket}
            loading={bucketsLoading}
            onChangeWithPropagation={(bucketId, applyToSimilar) =>
              onSetBucket(item, bucketId, applyToSimilar)
            }
          />
        ),
      },
      {
        key: "tag",
        header: "Tag",
        className: "min-w-[190px] px-3 py-3 align-top",
        cell: (item) => (
          <TagSelect
            value={item.tag?.id ?? null}
            options={tags}
            disabled={savingTag}
            loading={tagsLoading}
            onChange={(tagId) => onSetTag(item, tagId)}
            onCreate={onCreateTag}
          />
        ),
      },
      {
        key: "installment",
        header: "Parcela",
        className: "min-w-[90px] px-3 py-3 align-top text-muted",
        cell: (item) => installmentLabel(item.installment),
      },
    ],
    [
      buckets,
      bucketsLoading,
      onCreateTag,
      onSetBucket,
      onSetTag,
      savingBucket,
      savingTag,
      tags,
      tagsLoading,
    ],
  );

  return (
    <DataTable
      columns={columns}
      rows={items}
      getRowKey={(item) => item.id}
      loading={loading}
      empty={<EmptyState title="Sem lançamentos nesta fatura" />}
    />
  );
}
