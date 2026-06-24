"use client";

import { useState } from "react";
import { AlertTriangle, RefreshCw, Tags } from "lucide-react";
import { BucketSelect } from "@/components/ui/BucketSelect";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { MoneyText } from "@/components/ui/MoneyText";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { SectionCard } from "@/components/ui/SectionCard";
import { TagSelect } from "@/components/ui/TagSelect";
import {
  classificationCoverage,
  classificationIssueRows,
  type ClassificationIssueRow,
} from "@/lib/maintenance";
import type {
  Bucket,
  MaintenanceClassificationBulkApplyResponse,
  MaintenanceClassificationBulkKind,
  MaintenanceClassificationBulkPreviewResponse,
  MaintenanceClassificationBulkRequest,
  MaintenanceClassificationPolicyIssue,
  MaintenanceClassificationReprocessResponse,
  MaintenanceClassificationSuggestionsResponse,
  MaintenanceResponse,
  Tag,
} from "@/lib/types";

type ClassificationHealthPanelProps = {
  data: MaintenanceResponse;
  month?: string | null;
  buckets?: Bucket[];
  tags?: Tag[];
  reprocessing?: boolean;
  previewing?: boolean;
  applying?: boolean;
  suggestions?: MaintenanceClassificationSuggestionsResponse;
  suggestionsLoading?: boolean;
  suggestionsError?: unknown;
  onReprocess?: () => Promise<Partial<MaintenanceClassificationReprocessResponse>>;
  onPreviewBulk?: (
    payload: MaintenanceClassificationBulkRequest,
  ) => Promise<MaintenanceClassificationBulkPreviewResponse>;
  onApplyBulk?: (
    payload: MaintenanceClassificationBulkRequest,
  ) => Promise<MaintenanceClassificationBulkApplyResponse>;
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

function PolicyIgnoredColumn({
  title,
  count,
  rows,
}: {
  title: string;
  count: number;
  rows: MaintenanceClassificationPolicyIssue[];
}) {
  return (
    <div className="rounded-md border border-border bg-bg p-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-text">{title}</p>
          <p className="mt-1 text-xs text-muted">{count} lançamento(s) fora da fila acionável</p>
        </div>
      </div>
      {rows.length ? (
        <ul className="mt-3 space-y-2">
          {rows.slice(0, 4).map((row) => (
            <li key={`${title}-${row.id}`} className="min-w-0 rounded-md bg-surface2 px-3 py-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="truncate text-sm font-medium text-text">{row.description}</span>
                <MoneyText value={row.amount_abs} className="text-sm font-semibold" />
              </div>
              <p className="mt-1 text-xs text-muted">
                {row.date} · {row.account_name?.trim() || "Sem conta"} · {row.reason_label}
              </p>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-sm text-muted">Nenhum lançamento ignorado por política.</p>
      )}
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

function colorDot(color?: string | null) {
  return (
    <span
      aria-hidden
      className="h-2.5 w-2.5 shrink-0 rounded-full border border-border"
      style={{ backgroundColor: color ?? "transparent" }}
    />
  );
}

function ClassificationSuggestions({
  data,
  loading,
  error,
}: {
  data?: MaintenanceClassificationSuggestionsResponse;
  loading?: boolean;
  error?: unknown;
}) {
  const items = data?.items ?? [];

  return (
    <div className="space-y-3 rounded-md border border-border bg-surface2 p-4">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h3 className="text-sm font-semibold text-text">Sugestões de classificação</h3>
          <p className="text-xs text-muted">
            Categorias agrupadas com Tag e Meta sugeridas pela regra atual.
          </p>
        </div>
        <span className="text-xs font-medium text-muted">{data?.total ?? 0} grupo(s)</span>
      </div>

      {loading ? (
        <div className="rounded-md border border-dashed border-border bg-bg p-4 text-sm text-muted">
          Carregando sugestões...
        </div>
      ) : error ? (
        <div className="rounded-md border border-negative/40 bg-negative/10 p-4 text-sm text-negative">
          Não foi possível carregar sugestões.
        </div>
      ) : items.length ? (
        <div className="grid gap-3 xl:grid-cols-2">
          {items.slice(0, 6).map((item) => (
            <div key={item.raw_category} className="rounded-md border border-border bg-bg p-3">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-text">{item.category_label}</p>
                  <p className="mt-1 truncate text-xs text-muted">{item.raw_category}</p>
                </div>
                <div className="text-right text-xs text-muted">
                  <p>{item.transaction_count} lançamento(s)</p>
                  <MoneyText value={item.total_abs} className="font-semibold text-text" />
                </div>
              </div>

              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                <div className="rounded-md border border-border bg-surface px-3 py-2">
                  <p className="text-xs font-medium text-muted">Tag sugerida</p>
                  <p className="mt-1 flex min-w-0 items-center gap-2 text-sm font-semibold text-text">
                    {colorDot(item.suggested_tag?.color)}
                    <span className="truncate">{item.suggested_tag?.name ?? "Sem sugestão"}</span>
                  </p>
                </div>
                <div className="rounded-md border border-border bg-surface px-3 py-2">
                  <p className="text-xs font-medium text-muted">Meta sugerida</p>
                  <p className="mt-1 flex min-w-0 items-center gap-2 text-sm font-semibold text-text">
                    {colorDot(item.suggested_bucket?.color)}
                    <span className="truncate">{item.suggested_bucket?.name ?? "Sem sugestão"}</span>
                  </p>
                </div>
              </div>

              {item.examples.length ? (
                <ul className="mt-3 space-y-1 text-xs text-muted">
                  {item.examples.slice(0, 2).map((example) => (
                    <li key={example.id} className="truncate">
                      {example.date} · {example.description}
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          ))}
        </div>
      ) : (
        <div className="rounded-md border border-dashed border-border bg-bg p-4 text-sm text-muted">
          Nenhuma sugestão pendente.
        </div>
      )}
    </div>
  );
}

export function ClassificationHealthPanel({
  data,
  month,
  buckets = [],
  tags = [],
  reprocessing = false,
  previewing = false,
  applying = false,
  suggestions,
  suggestionsLoading = false,
  suggestionsError,
  onReprocess,
  onPreviewBulk,
  onApplyBulk,
}: ClassificationHealthPanelProps) {
  const coverage = classificationCoverage(data);
  const missingTag = classificationIssueRows(data, "missing_tag");
  const missingBucket = classificationIssueRows(data, "missing_bucket");
  const ignoredTagPolicy = data.classification_health?.ignored_tag_policy ?? [];
  const ignoredBucketPolicy = data.classification_health?.ignored_bucket_policy ?? [];
  const ignoredTagPolicyCount = data.classification_health?.ignored_tag_policy_count ?? 0;
  const ignoredBucketPolicyCount = data.classification_health?.ignored_bucket_policy_count ?? 0;
  const missingTagHref = qualityQueueHref("missing_tag", month);
  const missingBucketHref = qualityQueueHref("missing_bucket", month);
  const [bulkKind, setBulkKind] = useState<MaintenanceClassificationBulkKind>("tag");
  const [tagId, setTagId] = useState<number | null>(null);
  const [bucketId, setBucketId] = useState<number | null>(null);
  const [preview, setPreview] = useState<MaintenanceClassificationBulkPreviewResponse | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const hasActions = Boolean(onReprocess || onPreviewBulk || onApplyBulk);
  const selectedTargetId = bulkKind === "tag" ? tagId : bucketId;
  const canPreview = Boolean(onPreviewBulk && selectedTargetId);
  const canApply = Boolean(onApplyBulk && selectedTargetId && preview?.kind === bulkKind);

  const payload = (): MaintenanceClassificationBulkRequest | null => {
    if (!selectedTargetId) {
      return null;
    }
    return { kind: bulkKind, target_id: selectedTargetId, month };
  };

  const handleReprocess = async () => {
    if (!onReprocess) return;
    setStatus("Reprocessando classificação...");
    setPreview(null);
    try {
      const result = await onReprocess();
      setStatus(`${result.changed ?? 0} classificação(ões) atualizada(s).`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Falha ao reprocessar classificação.");
    }
  };

  const handlePreview = async () => {
    const request = payload();
    if (!onPreviewBulk || !request) {
      setStatus("Selecione uma Tag ou Meta antes de gerar a prévia.");
      return;
    }
    setStatus("Gerando prévia...");
    try {
      const result = await onPreviewBulk(request);
      setPreview(result);
      setStatus(`${result.total} lançamento(s) na prévia.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Falha ao gerar prévia.");
    }
  };

  const handleApply = async () => {
    const request = payload();
    if (!onApplyBulk || !request) {
      setStatus("Selecione uma Tag ou Meta antes de aplicar.");
      return;
    }
    setStatus("Aplicando em massa...");
    try {
      const result = await onApplyBulk(request);
      setStatus(`${result.updated} lançamento(s) atualizado(s).`);
      setPreview(null);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Falha ao aplicar em massa.");
    }
  };

  return (
    <SectionCard
      title="Saúde da classificação"
      subtitle="Cobertura automática e filas acionáveis de lançamentos sem Tag ou Meta."
    >
      <div className="space-y-5">
        {hasActions ? (
          <div className="space-y-4 rounded-md border border-border bg-surface2 p-4">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <h3 className="text-sm font-semibold text-text">Ações de classificação</h3>
                <p className="mt-1 text-xs text-muted">
                  Reprocesse regras automáticas ou gere uma prévia antes de aplicar Tag/Meta em massa.
                </p>
              </div>
              {onReprocess ? (
                <button
                  type="button"
                  onClick={() => void handleReprocess()}
                  disabled={reprocessing}
                  className="inline-flex h-9 items-center justify-center gap-2 rounded-md border border-border px-3 text-sm font-medium text-text transition hover:bg-surface disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <RefreshCw
                    size={15}
                    aria-hidden
                    className={reprocessing ? "animate-spin" : undefined}
                  />
                  {reprocessing ? "Reprocessando..." : "Reprocessar classificação"}
                </button>
              ) : null}
            </div>

            <div className="grid gap-3 xl:grid-cols-[160px_minmax(0,1fr)_auto_auto] xl:items-end">
              <label className="space-y-1">
                <span className="text-xs font-medium text-muted">Fila</span>
                <select
                  value={bulkKind}
                  onChange={(event) => {
                    setBulkKind(event.target.value as MaintenanceClassificationBulkKind);
                    setPreview(null);
                  }}
                  className="h-9 w-full rounded-md border border-border bg-bg px-2 text-sm text-text outline-none"
                >
                  <option value="tag">Sem Tag</option>
                  <option value="bucket">Sem Meta</option>
                </select>
              </label>
              <div className="space-y-1">
                <span className="text-xs font-medium text-muted">
                  {bulkKind === "tag" ? "Tag para aplicar" : "Meta para aplicar"}
                </span>
                {bulkKind === "tag" ? (
                  <TagSelect
                    value={tagId}
                    options={tags}
                    onChange={(value) => {
                      setTagId(value);
                      setPreview(null);
                    }}
                    placeholder="Selecione a tag"
                  />
                ) : (
                  <BucketSelect
                    value={bucketId}
                    options={buckets}
                    onChange={(value) => {
                      setBucketId(value);
                      setPreview(null);
                    }}
                    placeholder="Selecione a meta"
                  />
                )}
              </div>
              <button
                type="button"
                onClick={() => void handlePreview()}
                disabled={!canPreview || previewing}
                className="inline-flex h-9 items-center justify-center rounded-md border border-border px-3 text-sm font-medium text-text transition hover:bg-surface disabled:cursor-not-allowed disabled:opacity-60"
              >
                {previewing ? "Gerando..." : "Gerar prévia"}
              </button>
              <button
                type="button"
                onClick={() => void handleApply()}
                disabled={!canApply || applying}
                className="inline-flex h-9 items-center justify-center rounded-md bg-accent px-3 text-sm font-semibold text-accentFg transition hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {applying ? "Aplicando..." : "Aplicar em massa"}
              </button>
            </div>

            <div className="rounded-md border border-border bg-bg p-3">
              <p className="text-sm font-semibold text-text">Prévia de aplicação em massa</p>
              {preview ? (
                <div className="mt-2 space-y-2 text-sm text-muted">
                  <p>
                    {preview.total} lançamento(s) receberão {preview.kind === "tag" ? "a Tag" : "a Meta"}{" "}
                    <span className="font-semibold text-text">{preview.target_name}</span>, somando{" "}
                    <MoneyText value={preview.total_abs} className="font-semibold text-text" />.
                  </p>
                  {preview.items.length ? (
                    <ul className="space-y-1">
                      {preview.items.slice(0, 3).map((item) => (
                        <li key={item.id} className="truncate">
                          {item.date} · {item.description} · {item.category_label}
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              ) : (
                <p className="mt-1 text-sm text-muted">
                  Selecione a fila e o destino para ver quantidade, valor e exemplos antes de salvar.
                </p>
              )}
            </div>

            {status ? (
              <p className="rounded-md border border-border bg-bg px-3 py-2 text-sm text-muted">
                {status}
              </p>
            ) : null}
          </div>
        ) : null}

        <ClassificationSuggestions
          data={suggestions}
          loading={suggestionsLoading}
          error={suggestionsError}
        />

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

        {(ignoredTagPolicyCount > 0 || ignoredBucketPolicyCount > 0) ? (
          <div className="space-y-3 rounded-md border border-border bg-surface2 p-4">
            <div>
              <h3 className="text-sm font-semibold text-text">Ignorados por política</h3>
              <p className="mt-1 text-xs text-muted">
                Lançamentos sem Tag/Meta que não entram nas filas por serem transferência,
                pagamento de fatura, investimento, renda ou categoria bloqueada para pote.
              </p>
            </div>
            <div className="grid gap-3 lg:grid-cols-2">
              <PolicyIgnoredColumn
                title="Sem Tag"
                count={ignoredTagPolicyCount}
                rows={ignoredTagPolicy}
              />
              <PolicyIgnoredColumn
                title="Sem Meta"
                count={ignoredBucketPolicyCount}
                rows={ignoredBucketPolicy}
              />
            </div>
          </div>
        ) : null}

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
