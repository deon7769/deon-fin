"use client";

import { FormEvent, useState } from "react";
import { Pencil, Plus, RotateCcw, Save, Trash2, X } from "lucide-react";

import { SectionCard } from "@/components/ui/SectionCard";
import { buildQuestionPayload, diagramLabel, type InvestmentQuestionFormValues } from "@/lib/investments";
import { cn } from "@/lib/cn";
import type { InvestmentQuestion, InvestmentQuestionInput, InvestmentQuestionsResponse } from "@/lib/types";

type InvestmentQuestionsPanelProps = {
  diagramType: string;
  data: InvestmentQuestionsResponse;
  saving?: boolean;
  deletingId?: number | null;
  restoring?: boolean;
  error?: string | null;
  onDiagramChange: (diagramType: string) => void;
  onCreate: (input: InvestmentQuestionInput) => void | Promise<void>;
  onUpdate: (id: number, input: Partial<InvestmentQuestionInput>) => void | Promise<void>;
  onDelete: (id: number) => void | Promise<void>;
  onRestoreDefaults: () => void | Promise<void>;
};

const DIAGRAMS = ["acoes", "imobiliario"];

function displayNumber(value: number | null | undefined) {
  return value === null || value === undefined ? "" : String(value).replace(".", ",");
}

function questionInitialValues(diagramType: string, question?: InvestmentQuestion | null): InvestmentQuestionFormValues {
  return {
    diagramType: question?.diagram_type ?? diagramType,
    criterio: question?.criterio ?? "",
    pergunta: question?.pergunta ?? "",
    peso: displayNumber(question?.peso ?? 1),
    sortOrder: displayNumber(question?.sort_order ?? 0),
    ativo: question?.ativo ?? true,
  };
}

function QuestionModal({
  mode,
  diagramType,
  question,
  saving,
  error,
  onClose,
  onSubmit,
}: {
  mode: "create" | "edit";
  diagramType: string;
  question?: InvestmentQuestion | null;
  saving: boolean;
  error?: string | null;
  onClose: () => void;
  onSubmit: (input: InvestmentQuestionInput) => void | Promise<void>;
}) {
  const [values, setValues] = useState(() => questionInitialValues(diagramType, question));
  const [localError, setLocalError] = useState<string | null>(null);
  const title = mode === "create" ? "Adicionar pergunta" : "Editar pergunta";

  const update = (field: keyof InvestmentQuestionFormValues, value: string | boolean) => {
    setValues((current) => ({ ...current, [field]: value }));
    setLocalError(null);
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!values.pergunta.trim()) {
      setLocalError("Informe a pergunta.");
      return;
    }
    const payload = buildQuestionPayload(values);
    if (payload.peso <= 0) {
      setLocalError("Informe um peso positivo.");
      return;
    }
    await onSubmit(payload);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="investment-question-modal-title"
        className="w-full max-w-xl rounded-md border border-border bg-surface shadow-2xl"
      >
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <h2 id="investment-question-modal-title" className="text-base font-semibold text-text">
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Fechar"
            title="Fechar"
            className="inline-flex h-9 w-9 items-center justify-center rounded-md text-muted transition hover:bg-surface2 hover:text-text"
          >
            <X size={17} aria-hidden />
          </button>
        </div>

        <form onSubmit={submit} className="space-y-4 px-5 py-5">
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block space-y-2">
              <span className="text-sm font-medium text-text">Diagrama</span>
              <select
                value={values.diagramType}
                onChange={(event) => update("diagramType", event.target.value)}
                className="h-10 w-full rounded-md border border-border bg-bg px-3 text-sm text-text outline-none focus:border-blue-500"
              >
                {DIAGRAMS.map((item) => (
                  <option key={item} value={item}>
                    {diagramLabel(item)}
                  </option>
                ))}
              </select>
            </label>

            <label className="block space-y-2">
              <span className="text-sm font-medium text-text">Criterio</span>
              <input
                value={values.criterio}
                onChange={(event) => update("criterio", event.target.value)}
                className="h-10 w-full rounded-md border border-border bg-bg px-3 text-sm text-text outline-none focus:border-blue-500"
              />
            </label>
          </div>

          <label className="block space-y-2">
            <span className="text-sm font-medium text-text">Pergunta</span>
            <textarea
              value={values.pergunta}
              onChange={(event) => update("pergunta", event.target.value)}
              rows={3}
              className="min-h-24 w-full rounded-md border border-border bg-bg px-3 py-2 text-sm text-text outline-none focus:border-blue-500"
            />
          </label>

          <div className="grid gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
            <label className="block space-y-2">
              <span className="text-sm font-medium text-text">Peso</span>
              <input
                value={values.peso}
                onChange={(event) => update("peso", event.target.value)}
                inputMode="decimal"
                className="h-10 w-full rounded-md border border-border bg-bg px-3 text-sm text-text outline-none focus:border-blue-500"
              />
            </label>

            <label className="block space-y-2">
              <span className="text-sm font-medium text-text">Ordem</span>
              <input
                value={values.sortOrder}
                onChange={(event) => update("sortOrder", event.target.value)}
                inputMode="numeric"
                className="h-10 w-full rounded-md border border-border bg-bg px-3 text-sm text-text outline-none focus:border-blue-500"
              />
            </label>

            <label className="inline-flex h-10 items-center gap-2 rounded-md border border-border px-3 text-sm text-muted">
              <input
                type="checkbox"
                checked={values.ativo}
                onChange={(event) => update("ativo", event.target.checked)}
                className="h-4 w-4 accent-blue-500"
              />
              Ativa
            </label>
          </div>

          {localError || error ? <p className="text-sm text-negative">{localError ?? error}</p> : null}

          <div className="flex justify-end gap-2 pt-2">
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
              className="inline-flex h-10 items-center gap-2 rounded-md bg-blue-500 px-4 text-sm font-semibold text-white transition hover:bg-blue-600 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Save size={16} aria-hidden />
              {saving ? "Salvando..." : "Salvar"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export function InvestmentQuestionsPanel({
  diagramType,
  data,
  saving = false,
  deletingId = null,
  restoring = false,
  error = null,
  onDiagramChange,
  onCreate,
  onUpdate,
  onDelete,
  onRestoreDefaults,
}: InvestmentQuestionsPanelProps) {
  const [modalMode, setModalMode] = useState<"create" | "edit" | null>(null);
  const [editingQuestion, setEditingQuestion] = useState<InvestmentQuestion | null>(null);

  const openCreate = () => {
    setEditingQuestion(null);
    setModalMode("create");
  };

  const openEdit = (question: InvestmentQuestion) => {
    setEditingQuestion(question);
    setModalMode("edit");
  };

  const closeModal = () => {
    setModalMode(null);
    setEditingQuestion(null);
  };

  const submitQuestion = async (input: InvestmentQuestionInput) => {
    if (modalMode === "edit" && editingQuestion) {
      await onUpdate(editingQuestion.id, input);
    } else {
      await onCreate(input);
    }
    closeModal();
  };

  return (
    <div className="space-y-4">
      <SectionCard
        title="Perguntas de Score"
        actions={
          <div className="flex flex-wrap justify-end gap-2">
            <button
              type="button"
              onClick={onRestoreDefaults}
              disabled={restoring}
              className="inline-flex h-9 items-center gap-2 rounded-md border border-blue-400/40 bg-blue-500/10 px-3 text-sm font-medium text-blue-200 transition hover:bg-blue-500/20 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <RotateCcw size={16} aria-hidden className={restoring ? "animate-spin" : undefined} />
              Restaurar padrao
            </button>
            <button
              type="button"
              onClick={openCreate}
              className="inline-flex h-9 items-center gap-2 rounded-md bg-blue-500 px-3 text-sm font-medium text-white transition hover:bg-blue-600"
            >
              <Plus size={16} aria-hidden />
              Adicionar pergunta
            </button>
          </div>
        }
      >
        <div className="mb-4 flex flex-wrap gap-2" role="tablist" aria-label="Diagramas">
          {DIAGRAMS.map((item) => {
            const active = item === diagramType;
            return (
              <button
                key={item}
                type="button"
                onClick={() => onDiagramChange(item)}
                className={cn(
                  "h-9 rounded-md border px-3 text-sm font-medium transition",
                  active
                    ? "border-blue-400 bg-blue-500/15 text-blue-100"
                    : "border-border text-muted hover:bg-surface2 hover:text-text",
                )}
              >
                {diagramLabel(item)}
              </button>
            );
          })}
        </div>

        {error ? <p className="mb-4 text-sm text-negative">{error}</p> : null}

        <div className="overflow-x-auto">
          <table className="min-w-[860px] w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs font-semibold uppercase tracking-normal text-muted">
                <th className="py-3 pr-4">Ordem</th>
                <th className="px-4 py-3">Criterio</th>
                <th className="px-4 py-3">Pergunta</th>
                <th className="px-4 py-3 text-right">Peso</th>
                <th className="px-4 py-3">Status</th>
                <th className="py-3 pl-4 text-right">Acao</th>
              </tr>
            </thead>
            <tbody>
              {data.questions.map((question) => (
                <tr key={question.id} className="border-b border-border last:border-0">
                  <td className="py-3 pr-4 text-muted">{question.sort_order}</td>
                  <td className="px-4 py-3 text-text">{question.criterio ?? "--"}</td>
                  <td className="px-4 py-3 font-medium text-text">{question.pergunta}</td>
                  <td className="px-4 py-3 text-right tabular-nums text-text">{question.peso.toFixed(2)}</td>
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        "inline-flex rounded-full border px-2 py-0.5 text-xs font-medium",
                        question.ativo
                          ? "border-blue-400/40 bg-blue-500/10 text-blue-200"
                          : "border-zinc-600 bg-zinc-800 text-muted",
                      )}
                    >
                      {question.ativo ? "Ativa" : "Inativa"}
                    </span>
                  </td>
                  <td className="py-3 pl-4">
                    <div className="flex justify-end gap-2">
                      <button
                        type="button"
                        onClick={() => openEdit(question)}
                        aria-label={`Editar pergunta ${question.id}`}
                        title="Editar"
                        className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-border text-muted transition hover:bg-surface2 hover:text-text"
                      >
                        <Pencil size={16} aria-hidden />
                      </button>
                      <button
                        type="button"
                        onClick={() => onDelete(question.id)}
                        disabled={deletingId === question.id}
                        aria-label={`Excluir pergunta ${question.id}`}
                        title="Excluir"
                        className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-negative/50 text-negative transition hover:bg-negative/10 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        <Trash2 size={16} aria-hidden />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>

      {modalMode ? (
        <QuestionModal
          mode={modalMode}
          diagramType={diagramType}
          question={editingQuestion}
          saving={saving}
          error={error}
          onClose={closeModal}
          onSubmit={submitQuestion}
        />
      ) : null}
    </div>
  );
}
