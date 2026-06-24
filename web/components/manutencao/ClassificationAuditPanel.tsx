import { Clock3 } from "lucide-react";
import { SectionCard } from "@/components/ui/SectionCard";
import type {
  MaintenanceClassificationAuditItem,
  MaintenanceClassificationAuditResponse,
} from "@/lib/types";

type ClassificationAuditPanelProps = {
  data?: MaintenanceClassificationAuditResponse;
  loading?: boolean;
  error?: unknown;
};

function actionLabel(action: string): string {
  switch (action) {
    case "bulk_apply":
      return "Aplicação em massa";
    case "rule_update":
      return "Regra atualizada";
    case "rule_delete":
      return "Regra removida";
    default:
      return action;
  }
}

function kindLabel(kind: MaintenanceClassificationAuditItem["kind"]): string {
  return kind === "bucket" ? "Meta" : "Tag";
}

function createdAtLabel(value: string): string {
  return value ? value.replace("T", " ").slice(0, 16) : "-";
}

function metadataMonth(item: MaintenanceClassificationAuditItem): string | null {
  const month = item.metadata?.month;
  return typeof month === "string" ? month : null;
}

function AuditItem({ item }: { item: MaintenanceClassificationAuditItem }) {
  const month = metadataMonth(item);
  const primaryLabel = item.target_name ?? item.match_key ?? "Sem destino";

  return (
    <li className="grid gap-3 border-b border-border py-3 last:border-b-0 lg:grid-cols-[minmax(0,1.2fr)_minmax(140px,0.45fr)_minmax(120px,0.35fr)] lg:items-center">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-md border border-border bg-bg px-2 py-1 text-xs font-semibold text-text">
            {actionLabel(item.action)}
          </span>
          <span className="text-xs font-medium text-muted">{kindLabel(item.kind)}</span>
          {month ? <span className="text-xs text-muted">{month}</span> : null}
        </div>
        <p className="mt-2 truncate text-sm font-semibold text-text">{primaryLabel}</p>
        {item.match_key ? (
          <p className="mt-1 truncate font-mono text-xs text-muted">Chave: {item.match_key}</p>
        ) : null}
      </div>

      <div>
        <p className="text-xs font-medium text-muted">Registros</p>
        <p className="mt-1 text-sm font-semibold text-text">
          {item.preview_total > 0
            ? `${item.affected_count} de ${item.preview_total}`
            : item.affected_count}
        </p>
      </div>

      <div className="flex items-center gap-2 text-xs text-muted lg:justify-end">
        <Clock3 size={14} aria-hidden />
        <span>{createdAtLabel(item.created_at)}</span>
      </div>
    </li>
  );
}

export function ClassificationAuditPanel({
  data,
  loading = false,
  error,
}: ClassificationAuditPanelProps) {
  const items = data?.items ?? [];

  return (
    <SectionCard
      title="Auditoria de classificação"
      subtitle="Histórico recente de aplicações em massa e alterações de regras."
    >
      {loading ? (
        <div className="rounded-md border border-dashed border-border bg-bg p-4 text-sm text-muted">
          Carregando histórico...
        </div>
      ) : error ? (
        <div className="rounded-md border border-negative/40 bg-negative/10 p-4 text-sm text-negative">
          Não foi possível carregar a auditoria.
        </div>
      ) : items.length ? (
        <ul className="divide-y-0">
          {items.map((item) => (
            <AuditItem key={item.id} item={item} />
          ))}
        </ul>
      ) : (
        <div className="rounded-md border border-dashed border-border bg-bg p-4 text-sm text-muted">
          Nenhuma ação de classificação registrada ainda.
        </div>
      )}
    </SectionCard>
  );
}
