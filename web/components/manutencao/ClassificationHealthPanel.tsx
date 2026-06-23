import { AlertTriangle, Tags } from "lucide-react";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { MoneyText } from "@/components/ui/MoneyText";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { SectionCard } from "@/components/ui/SectionCard";
import {
  classificationCoverage,
  classificationIssueRows,
  type ClassificationIssueRow,
} from "@/lib/maintenance";
import type { MaintenanceResponse } from "@/lib/types";

type ClassificationHealthPanelProps = {
  data: MaintenanceResponse;
  month?: string | null;
};

const issueColumns: DataTableColumn<ClassificationIssueRow>[] = [
  {
    key: "description",
    header: "Lançamento",
    cell: (row) => (
      <div className="min-w-0">
        <p className="font-medium text-text">{row.description}</p>
        <p className="mt-1 text-xs text-muted">
          {row.date} · {row.accountName}
        </p>
      </div>
    ),
  },
  {
    key: "category",
    header: "Categoria",
    className: "min-w-[160px] px-3 py-3 align-top",
    cell: (row) => <span className="text-muted">{row.categoryLabel}</span>,
  },
  {
    key: "amount",
    header: "Valor",
    className: "min-w-[120px] px-3 py-3 text-right align-top",
    cell: (row) => <MoneyText value={row.amountAbs} className="font-semibold" />,
  },
];

function CoverageTile({
  title,
  value,
  label,
  reviewCount,
}: {
  title: string;
  value: number;
  label: string;
  reviewCount: number;
}) {
  return (
    <div className="rounded-md border border-border bg-surface2 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-text">{title}</p>
          <p className="mt-1 text-xs text-muted">{label} classificados</p>
        </div>
        <span className="text-lg font-semibold tabular-nums text-text">{value}%</span>
      </div>
      <ProgressBar value={value} className="mt-3" />
      <p className="mt-3 text-xs text-muted">{reviewCount} itens para revisar</p>
    </div>
  );
}

function qualityQueueHref(
  quality: "missing_tag" | "missing_bucket",
  month?: string | null,
): string {
  const params = new URLSearchParams();
  if (month) {
    params.set("month", month);
  }
  params.set("quality", quality);
  return `/transacoes?${params.toString()}`;
}

export function ClassificationHealthPanel({ data, month }: ClassificationHealthPanelProps) {
  const coverage = classificationCoverage(data);
  const missingTag = classificationIssueRows(data, "missing_tag");
  const missingBucket = classificationIssueRows(data, "missing_bucket");
  const missingTagHref = qualityQueueHref("missing_tag", month);
  const missingBucketHref = qualityQueueHref("missing_bucket", month);

  return (
    <SectionCard
      title="Saúde da classificação"
      subtitle="Cobertura automática e filas acionáveis de lançamentos sem Tag ou Meta."
    >
      <div className="space-y-5">
        <div className="grid gap-4 md:grid-cols-2">
          <CoverageTile
            title="Cobertura de Tags"
            value={coverage.tagPct}
            label={coverage.tagLabel}
            reviewCount={coverage.missingTagReviewCount}
          />
          <CoverageTile
            title="Cobertura de Metas"
            value={coverage.bucketPct}
            label={coverage.bucketLabel}
            reviewCount={coverage.missingBucketReviewCount}
          />
        </div>

        <div className="grid gap-5 xl:grid-cols-2">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Tags size={16} className="text-muted" aria-hidden />
                <h3 className="text-sm font-semibold text-text">Sem Tag</h3>
              </div>
              <a
                href={missingTagHref}
                className="inline-flex h-8 items-center rounded-md border border-border px-2.5 text-xs font-medium text-muted transition hover:bg-surface2 hover:text-text"
              >
                Abrir fila sem Tag
              </a>
            </div>
            <DataTable
              columns={issueColumns}
              rows={missingTag}
              getRowKey={(row) => row.id}
              empty={<EmptyState title="Nenhum lançamento acionável sem Tag" />}
            />
          </div>
          <div className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <AlertTriangle size={16} className="text-muted" aria-hidden />
                <h3 className="text-sm font-semibold text-text">Sem Meta</h3>
              </div>
              <a
                href={missingBucketHref}
                className="inline-flex h-8 items-center rounded-md border border-border px-2.5 text-xs font-medium text-muted transition hover:bg-surface2 hover:text-text"
              >
                Abrir fila sem Meta
              </a>
            </div>
            <DataTable
              columns={issueColumns}
              rows={missingBucket}
              getRowKey={(row) => row.id}
              empty={<EmptyState title="Nenhum lançamento acionável sem Meta" />}
            />
          </div>
        </div>
      </div>
    </SectionCard>
  );
}
