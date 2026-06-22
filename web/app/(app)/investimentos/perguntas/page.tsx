"use client";

import { useState } from "react";
import { AlertCircle } from "lucide-react";

import { InvestmentQuestionsPanel } from "@/components/investimentos/InvestmentQuestionsPanel";
import { InvestmentTabs } from "@/components/investimentos/InvestmentTabs";
import { Header } from "@/components/layout/Header";
import { EmptyState } from "@/components/ui/EmptyState";
import { SectionCard } from "@/components/ui/SectionCard";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  useCreateInvestmentQuestion,
  useDeleteInvestmentQuestion,
  useInvestmentQuestions,
  useRestoreInvestmentQuestions,
  useUpdateInvestmentQuestion,
} from "@/hooks/useInvestments";
import type { InvestmentQuestionInput } from "@/lib/types";

function QuestionsSkeleton() {
  return (
    <SectionCard title="Perguntas de Score">
      <Skeleton className="h-80 w-full" />
    </SectionCard>
  );
}

function RetryState({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  return (
    <SectionCard>
      <EmptyState
        icon={<AlertCircle size={28} aria-hidden />}
        title="Nao foi possivel carregar as perguntas"
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

export default function InvestmentQuestionsPage() {
  const [diagramType, setDiagramType] = useState("acoes");
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const questions = useInvestmentQuestions(diagramType);
  const createQuestion = useCreateInvestmentQuestion();
  const updateQuestion = useUpdateInvestmentQuestion();
  const deleteQuestion = useDeleteInvestmentQuestion();
  const restoreQuestions = useRestoreInvestmentQuestions();
  const saving = createQuestion.isPending || updateQuestion.isPending;

  const submitCreate = async (input: InvestmentQuestionInput) => {
    try {
      setError(null);
      await createQuestion.mutateAsync(input);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel salvar a pergunta.");
      throw err;
    }
  };

  const submitUpdate = async (id: number, input: Partial<InvestmentQuestionInput>) => {
    try {
      setError(null);
      await updateQuestion.mutateAsync({ id, input });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel salvar a pergunta.");
      throw err;
    }
  };

  const removeQuestion = async (id: number) => {
    try {
      setError(null);
      setDeletingId(id);
      await deleteQuestion.mutateAsync(id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel excluir a pergunta.");
    } finally {
      setDeletingId(null);
    }
  };

  const restoreDefaults = async () => {
    try {
      setError(null);
      await restoreQuestions.mutateAsync(diagramType);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel restaurar o padrao.");
    }
  };

  return (
    <>
      <Header title="Investimentos" subtitle="Perguntas usadas no score dos ativos." />

      <div className="space-y-5 p-4 sm:p-6">
        <InvestmentTabs />

        {questions.isError ? (
          <RetryState error={questions.error} onRetry={() => void questions.refetch()} />
        ) : questions.isLoading || !questions.data ? (
          <QuestionsSkeleton />
        ) : (
          <InvestmentQuestionsPanel
            diagramType={diagramType}
            data={questions.data}
            saving={saving}
            deletingId={deletingId}
            restoring={restoreQuestions.isPending}
            error={error}
            onDiagramChange={(next) => {
              setDiagramType(next);
              setError(null);
            }}
            onCreate={submitCreate}
            onUpdate={submitUpdate}
            onDelete={removeQuestion}
            onRestoreDefaults={restoreDefaults}
          />
        )}
      </div>
    </>
  );
}
