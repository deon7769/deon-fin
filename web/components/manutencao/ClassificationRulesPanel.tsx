"use client";

import { useState } from "react";
import { Save, Trash2 } from "lucide-react";
import { BucketSelect } from "@/components/ui/BucketSelect";
import { SectionCard } from "@/components/ui/SectionCard";
import { TagSelect } from "@/components/ui/TagSelect";
import type {
  Bucket,
  MaintenanceClassificationRule,
  MaintenanceClassificationRuleKind,
  MaintenanceClassificationRulePatch,
  MaintenanceClassificationRulesResponse,
  Tag,
} from "@/lib/types";

type ClassificationRulesPanelProps = {
  rules?: MaintenanceClassificationRulesResponse;
  buckets?: Bucket[];
  tags?: Tag[];
  saving?: boolean;
  onSaveRule: (patch: MaintenanceClassificationRulePatch) => Promise<void>;
};

type RuleTarget = {
  id: number;
  name: string;
  color?: string | null;
};

function ruleKey(rule: MaintenanceClassificationRule): string {
  return `${rule.kind}:${rule.match_key}`;
}

function targetName(rule: MaintenanceClassificationRule, targets: RuleTarget[]): string {
  return targets.find((target) => target.id === rule.target_id)?.name ?? rule.target_name ?? "Sem destino";
}

function targetColor(rule: MaintenanceClassificationRule, targets: RuleTarget[]): string | null | undefined {
  return targets.find((target) => target.id === rule.target_id)?.color ?? rule.target_color;
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

function RuleRow({
  rule,
  targets,
  buckets,
  tags,
  disabled,
  draftValue,
  onDraftChange,
  onSave,
  onRemove,
}: {
  rule: MaintenanceClassificationRule;
  targets: RuleTarget[];
  buckets: Bucket[];
  tags: Tag[];
  disabled?: boolean;
  draftValue?: number | null;
  onDraftChange: (rule: MaintenanceClassificationRule, targetId: number | null) => void;
  onSave: (rule: MaintenanceClassificationRule, targetId: number | null) => void;
  onRemove: (rule: MaintenanceClassificationRule) => void;
}) {
  const selectedTargetId = draftValue === undefined ? rule.target_id : draftValue;
  const currentColor = targetColor(
    { ...rule, target_id: selectedTargetId },
    targets,
  );

  return (
    <div className="grid gap-3 rounded-md border border-border bg-bg p-3 lg:grid-cols-[minmax(0,1fr)_minmax(180px,240px)_auto_auto] lg:items-center">
      <div className="min-w-0">
        <p className="flex min-w-0 items-center gap-2 text-sm font-semibold text-text">
          {colorDot(currentColor)}
          <span className="truncate">{targetName({ ...rule, target_id: selectedTargetId }, targets)}</span>
        </p>
        <p className="mt-1 truncate font-mono text-xs text-muted">Chave: {rule.match_key}</p>
      </div>

      <div className="space-y-1">
        <span className="text-xs font-medium text-muted">Destino</span>
        {rule.kind === "tag" ? (
          <TagSelect
            value={selectedTargetId}
            options={tags}
            disabled={disabled}
            onChange={(targetId) => onDraftChange(rule, targetId)}
            placeholder="Selecione a Tag"
          />
        ) : (
          <BucketSelect
            value={selectedTargetId}
            options={buckets}
            disabled={disabled}
            onChange={(targetId) => onDraftChange(rule, targetId)}
            placeholder="Selecione a Meta"
          />
        )}
      </div>

      <button
        type="button"
        disabled={disabled || !selectedTargetId}
        onClick={() => onSave(rule, selectedTargetId)}
        className="inline-flex h-9 items-center justify-center gap-2 rounded-md border border-border px-3 text-sm font-medium text-text transition hover:bg-surface2 disabled:cursor-not-allowed disabled:opacity-60"
      >
        <Save size={15} aria-hidden />
        Salvar
      </button>

      <button
        type="button"
        disabled={disabled}
        onClick={() => onRemove(rule)}
        className="inline-flex h-9 items-center justify-center gap-2 rounded-md border border-border px-3 text-sm font-medium text-negative transition hover:bg-negative/10 disabled:cursor-not-allowed disabled:opacity-60"
      >
        <Trash2 size={15} aria-hidden />
        Remover regra
      </button>
    </div>
  );
}

function RuleGroup({
  title,
  description,
  kind,
  rules,
  targets,
  buckets,
  tags,
  saving,
  drafts,
  onDraftChange,
  onSave,
  onRemove,
}: {
  title: string;
  description: string;
  kind: MaintenanceClassificationRuleKind;
  rules: MaintenanceClassificationRule[];
  targets: RuleTarget[];
  buckets: Bucket[];
  tags: Tag[];
  saving?: boolean;
  drafts: Record<string, number | null>;
  onDraftChange: (rule: MaintenanceClassificationRule, targetId: number | null) => void;
  onSave: (rule: MaintenanceClassificationRule, targetId: number | null) => void;
  onRemove: (rule: MaintenanceClassificationRule) => void;
}) {
  const filtered = rules.filter((rule) => rule.kind === kind);

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h3 className="text-sm font-semibold text-text">{title}</h3>
          <p className="text-xs text-muted">{description}</p>
        </div>
        <span className="text-xs font-medium text-muted">{filtered.length} regra(s)</span>
      </div>

      {filtered.length ? (
        <div className="space-y-2">
          {filtered.map((rule) => (
            <RuleRow
              key={ruleKey(rule)}
              rule={rule}
              targets={targets}
              buckets={buckets}
              tags={tags}
              disabled={saving}
              draftValue={drafts[ruleKey(rule)]}
              onDraftChange={onDraftChange}
              onSave={onSave}
              onRemove={onRemove}
            />
          ))}
        </div>
      ) : (
        <div className="rounded-md border border-dashed border-border bg-bg p-4 text-sm text-muted">
          Nenhuma regra aprendida.
        </div>
      )}
    </div>
  );
}

export function ClassificationRulesPanel({
  rules,
  buckets = [],
  tags = [],
  saving = false,
  onSaveRule,
}: ClassificationRulesPanelProps) {
  const [drafts, setDrafts] = useState<Record<string, number | null>>({});
  const [status, setStatus] = useState<string | null>(null);
  const tagRules = rules?.tag_rules ?? [];
  const bucketRules = rules?.bucket_rules ?? [];

  const changeDraft = (rule: MaintenanceClassificationRule, targetId: number | null) => {
    setDrafts((current) => ({ ...current, [ruleKey(rule)]: targetId }));
  };

  const saveRule = async (rule: MaintenanceClassificationRule, targetId: number | null) => {
    if (!targetId) {
      setStatus("Selecione um destino antes de salvar.");
      return;
    }
    setStatus("Salvando regra...");
    try {
      await onSaveRule({ kind: rule.kind, match_key: rule.match_key, target_id: targetId });
      setDrafts((current) => {
        const next = { ...current };
        delete next[ruleKey(rule)];
        return next;
      });
      setStatus("Regra salva.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Falha ao salvar regra.");
    }
  };

  const removeRule = async (rule: MaintenanceClassificationRule) => {
    setStatus("Removendo regra...");
    try {
      await onSaveRule({ kind: rule.kind, match_key: rule.match_key, target_id: null });
      setDrafts((current) => {
        const next = { ...current };
        delete next[ruleKey(rule)];
        return next;
      });
      setStatus("Regra removida.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Falha ao remover regra.");
    }
  };

  return (
    <SectionCard
      title="Regras aprendidas"
      subtitle="Revise associações automáticas de descrição para Tag e Meta antes de reprocessar."
    >
      <div className="space-y-5">
        <RuleGroup
          title="Tags"
          description="Palavras normalizadas que alimentam a classificação por Tag."
          kind="tag"
          rules={tagRules}
          targets={tags}
          buckets={buckets}
          tags={tags}
          saving={saving}
          drafts={drafts}
          onDraftChange={changeDraft}
          onSave={(rule, targetId) => void saveRule(rule, targetId)}
          onRemove={(rule) => void removeRule(rule)}
        />

        <RuleGroup
          title="Metas"
          description="Palavras normalizadas que alimentam a classificação por pote/meta."
          kind="bucket"
          rules={bucketRules}
          targets={buckets}
          buckets={buckets}
          tags={tags}
          saving={saving}
          drafts={drafts}
          onDraftChange={changeDraft}
          onSave={(rule, targetId) => void saveRule(rule, targetId)}
          onRemove={(rule) => void removeRule(rule)}
        />

        {status ? (
          <p className="rounded-md border border-border bg-bg px-3 py-2 text-sm text-muted">
            {status}
          </p>
        ) : null}
      </div>
    </SectionCard>
  );
}
