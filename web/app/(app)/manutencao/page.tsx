"use client";

import { useMemo, useState } from "react";
import {
  AlertCircle,
  DatabaseZap,
  Landmark,
  ListChecks,
  RefreshCw,
  Save,
  Wallet,
} from "lucide-react";
import {
  EditableMaintenanceTable,
  type EditableColumn,
} from "@/components/manutencao/EditableMaintenanceTable";
import { CategoryMapPreview } from "@/components/manutencao/CategoryMapPreview";
import { HealthChecklist } from "@/components/manutencao/HealthChecklist";
import { MaintenanceSectionTable } from "@/components/manutencao/MaintenanceSectionTable";
import { MissingCategoryTranslations } from "@/components/manutencao/MissingCategoryTranslations";
import { RecurrenceRulesTable } from "@/components/manutencao/RecurrenceRulesTable";
import { SystemTotalsPolicyPanel } from "@/components/manutencao/SystemTotalsPolicyPanel";
import { Header } from "@/components/layout/Header";
import { EmptyState } from "@/components/ui/EmptyState";
import { KpiCard } from "@/components/ui/KpiCard";
import { MoneyText } from "@/components/ui/MoneyText";
import { SectionCard } from "@/components/ui/SectionCard";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  useMaintenance,
  useMaintenanceSystemTotals,
  useSaveMaintenance,
  useSaveMaintenanceSystemTotals,
} from "@/hooks/useMaintenance";
import {
  buildMaintenanceSavePayload,
  buildMaintenanceHealth,
  buildMaintenanceSections,
  maintenanceToEditorState,
  maintenanceSummary,
  missingCategoryTranslations,
  type MaintenanceEditorState,
} from "@/lib/maintenance";

type EditorSection<K extends keyof MaintenanceEditorState> = {
  key: K;
  title: string;
  subtitle?: string;
  columns: EditableColumn<MaintenanceEditorState[K][number] & Record<string, unknown>>[];
};

const editorSections: Array<EditorSection<keyof MaintenanceEditorState>> = [
  {
    key: "receitas",
    title: "Receitas",
    subtitle: "A soma vira a renda informada usada pelo dashboard.",
    columns: [
      { key: "membro", label: "Membro", type: "text" },
      { key: "valor", label: "Valor (R$)", type: "number" },
    ],
  },
  {
    key: "caixa",
    title: "Reserva e caixa",
    columns: [
      { key: "local", label: "Local / Conta", type: "text" },
      { key: "valor", label: "Saldo (R$)", type: "number" },
      { key: "aporte_mensal_recorrente", label: "Aporte/mês", type: "number" },
    ],
  },
  {
    key: "provisoes",
    title: "Provisões mensais",
    subtitle: "Revisão do carro, pneus, seguro, material escolar e afins.",
    columns: [
      { key: "nome", label: "Nome", type: "text" },
      { key: "mensal", label: "Mensal", type: "number" },
      { key: "alvo", label: "Alvo", type: "number" },
      { key: "periodicidade_meses", label: "Period. (m)", type: "number" },
      { key: "proxima_ocorrencia", label: "Próxima (AAAA-MM)", type: "text" },
    ],
  },
  {
    key: "metas",
    title: "Metas de longo prazo",
    columns: [
      { key: "nome", label: "Nome", type: "text" },
      { key: "alvo", label: "Alvo", type: "number" },
      { key: "atual", label: "Atual", type: "number" },
      { key: "prazo", label: "Prazo", type: "text" },
    ],
  },
  {
    key: "wishlist",
    title: "Desejos de economia",
    subtitle: "Prioridade menor significa mais importante.",
    columns: [
      { key: "nome", label: "Desejo", type: "text" },
      { key: "valor_alvo", label: "Valor alvo", type: "number" },
      { key: "prazo_meses", label: "Prazo (m)", type: "number" },
      { key: "guardado", label: "Já guardado", type: "number" },
      { key: "prioridade", label: "Prioridade", type: "number" },
    ],
  },
  {
    key: "imoveis",
    title: "Patrimônio - Imóveis",
    subtitle: "Custos mensais nas últimas colunas.",
    columns: [
      { key: "nome", label: "Imóvel", type: "text" },
      { key: "valor_mercado", label: "Valor mercado", type: "number" },
      { key: "saldo_devedor", label: "Saldo devedor", type: "number" },
      { key: "taxa_juros_anual", label: "Juros % a.a.", type: "number" },
      { key: "prazo_restante_meses", label: "Prazo (m)", type: "number" },
      { key: "aluguel_receita", label: "Aluguel", type: "number" },
      { key: "custo_financiamento", label: "Financiamento", type: "number" },
      { key: "custo_condominio", label: "Condomínio", type: "number" },
      { key: "custo_iptu_lixo", label: "IPTU/lixo", type: "number" },
    ],
  },
  {
    key: "categorias",
    title: "Tradução de categorias",
    subtitle: "Categoria de origem Pluggy em inglês para nome em português.",
    columns: [
      { key: "en", label: "Origem", type: "text" },
      { key: "pt", label: "Tradução (PT)", type: "text" },
    ],
  },
  {
    key: "recorrencias",
    title: "Classificação de recorrências",
    subtitle: "Use ignorar para remover itens da lista de recorrências prováveis.",
    columns: [
      { key: "match", label: "Contém", type: "text" },
      {
        key: "tipo",
        label: "Tipo",
        type: "select",
        options: ["assinatura", "recorrencia", "ignorar"],
      },
      { key: "rotulo", label: "Rótulo", type: "text" },
    ],
  },
];

const profileEditorSections = editorSections.filter(
  (section) => section.key !== "categorias" && section.key !== "recorrencias",
);
const rulesEditorSections = editorSections.filter(
  (section) => section.key === "categorias" || section.key === "recorrencias",
);

function MaintenanceSkeleton() {
  return (
    <>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <KpiCard key={index} title="Carregando" value={<Skeleton className="h-8 w-28" />} />
        ))}
      </div>
      <SectionCard title="Saúde dos dados">
        <Skeleton className="h-56 w-full" />
      </SectionCard>
      <SectionCard title="Seções monitoradas">
        <Skeleton className="h-72 w-full" />
      </SectionCard>
    </>
  );
}

function RetryState({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  return (
    <SectionCard>
      <EmptyState
        icon={<AlertCircle size={28} aria-hidden />}
        title="Não foi possível carregar a manutenção"
        description={error instanceof Error ? error.message : undefined}
        action={
          <button
            type="button"
            onClick={onRetry}
            className="inline-flex h-9 items-center gap-2 rounded-md border border-border px-3 text-sm font-medium text-text transition hover:bg-surface2"
          >
            <RefreshCw size={15} aria-hidden />
            Tentar novamente
          </button>
        }
      />
    </SectionCard>
  );
}

export default function ManutencaoPage() {
  const maintenance = useMaintenance();
  const saveMaintenance = useSaveMaintenance();
  const systemTotals = useMaintenanceSystemTotals();
  const saveSystemTotals = useSaveMaintenanceSystemTotals();
  const [editorOverride, setEditorOverride] = useState<{
    dataUpdatedAt: number;
    value: MaintenanceEditorState;
  } | null>(null);
  const [editorStatus, setEditorStatus] = useState<string | null>(null);
  const data = maintenance.data;
  const summary = useMemo(() => (data ? maintenanceSummary(data) : null), [data]);
  const sections = useMemo(() => (data ? buildMaintenanceSections(data) : []), [data]);
  const health = useMemo(() => (data ? buildMaintenanceHealth(data) : null), [data]);
  const missingCategoryRows = useMemo(
    () => (data ? missingCategoryTranslations(data) : []),
    [data],
  );
  const editor = useMemo(() => {
    if (!data) {
      return null;
    }
    if (editorOverride?.dataUpdatedAt === maintenance.dataUpdatedAt) {
      return editorOverride.value;
    }
    return maintenanceToEditorState(data);
  }, [data, editorOverride, maintenance.dataUpdatedAt]);

  const updateEditorSection = <K extends keyof MaintenanceEditorState>(
    key: K,
    rows: MaintenanceEditorState[K],
  ) => {
    if (!editor) {
      return;
    }
    setEditorOverride({
      dataUpdatedAt: maintenance.dataUpdatedAt,
      value: { ...editor, [key]: rows },
    });
  };

  const reloadEditor = async () => {
    await maintenance.refetch();
    setEditorOverride(null);
    setEditorStatus("Dados recarregados.");
  };

  const saveEditor = async () => {
    if (!data || !editor) {
      setEditorStatus("Carregue os dados antes de salvar.");
      return;
    }
    setEditorStatus("Salvando...");
    try {
      await saveMaintenance.mutateAsync(buildMaintenanceSavePayload(data, editor));
      await maintenance.refetch();
      setEditorOverride(null);
      setEditorStatus("Salvo.");
    } catch (error) {
      setEditorStatus(error instanceof Error ? error.message : "Falha ao salvar.");
    }
  };

  const renderEditorSections = (sectionsToRender: typeof editorSections) => {
    if (!editor) {
      return <Skeleton className="h-72 w-full" />;
    }
    return (
      <div className="space-y-6">
        {sectionsToRender.map((section) => (
          <div
            key={section.key}
            className="space-y-2 border-b border-border pb-5 last:border-b-0 last:pb-0"
          >
            <div>
              <h3 className="text-sm font-semibold text-text">{section.title}</h3>
              {section.subtitle ? (
                <p className="mt-1 text-sm text-muted">{section.subtitle}</p>
              ) : null}
            </div>
            <EditableMaintenanceTable
              section={section.key}
              title={section.title}
              rows={editor[section.key]}
              columns={section.columns}
              onChange={(rows) => updateEditorSection(section.key, rows)}
            />
          </div>
        ))}
      </div>
    );
  };

  return (
    <>
      <Header
        title="Manutenção"
        subtitle="Saúde dos dados fixos e de/para usados pelas análises."
      />

      <div className="space-y-5 p-4 sm:p-6">
        {maintenance.isError ? (
          <RetryState error={maintenance.error} onRetry={() => void maintenance.refetch()} />
        ) : maintenance.isLoading || !data || !summary || !health ? (
          <MaintenanceSkeleton />
        ) : (
          <>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <KpiCard
                title="Renda informada"
                value={<MoneyText value={summary.incomeTotal} />}
                subtitle={`${data.family_profile.receitas?.length ?? 0} receita(s)`}
                icon={<Wallet size={18} aria-hidden />}
              />
              <KpiCard
                title="Reserva e caixa"
                value={<MoneyText value={summary.cashTotal} />}
                subtitle={`${data.family_profile.patrimonio?.investimentos_caixa?.length ?? 0} posição(ões)`}
                icon={<DatabaseZap size={18} aria-hidden />}
              />
              <KpiCard
                title="Provisões mensais"
                value={<MoneyText value={summary.provisionMonthlyTotal} />}
                subtitle={`${data.family_profile.provisoes?.length ?? 0} provisão(ões)`}
                icon={<ListChecks size={18} aria-hidden />}
              />
              <KpiCard
                title="Patrimônio em imóveis"
                value={<MoneyText value={summary.propertyEquity} />}
                subtitle={`${data.family_profile.patrimonio?.imoveis?.length ?? 0} imóvel(is)`}
                icon={<Landmark size={18} aria-hidden />}
              />
            </div>

            <SectionCard
              title="Saúde dos dados"
              subtitle={
                health.status === "ok"
                  ? "Todas as seções principais possuem dados."
                  : `${summary.missingSections} seção(ões) pedem revisão.`
              }
              actions={
                <a
                  href="/legacy"
                  className="inline-flex h-9 items-center rounded-md border border-border px-3 text-sm font-medium text-text transition hover:bg-surface2"
                >
                  Abrir editor legado
                </a>
              }
            >
              <HealthChecklist health={health} />
            </SectionCard>

            <SectionCard
              title="Seções monitoradas"
              subtitle={`${summary.configuredSections} de 8 seções com dados configurados`}
            >
              <MaintenanceSectionTable rows={sections} />
            </SectionCard>

            <SystemTotalsPolicyPanel
              data={systemTotals.data}
              loading={systemTotals.isLoading}
              saving={saveSystemTotals.isPending}
              error={systemTotals.error}
              onSave={async (payload) => {
                await saveSystemTotals.mutateAsync(payload);
              }}
            />

            <div className="grid gap-5 xl:grid-cols-2">
              <SectionCard
                title="Tradução de categorias"
                subtitle={`${summary.categoryCount} de/para configurado(s); mostrando os primeiros 10.`}
              >
                <CategoryMapPreview overrides={data.overrides} />
              </SectionCard>

              <SectionCard
                title="Regras de recorrência"
                subtitle={`${summary.recurrenceCount} regra(s); mostrando as primeiras 8.`}
              >
                <RecurrenceRulesTable overrides={data.overrides} />
              </SectionCard>
            </div>

            <SectionCard
              title="Categorias sem tradução"
              subtitle={
                data.category_audit
                  ? `${data.category_audit.translated} de ${data.category_audit.total_categories} categoria(s) vistas já traduzidas.`
                  : "Auditoria indisponível."
              }
            >
              <MissingCategoryTranslations rows={missingCategoryRows} />
            </SectionCard>

            <div className="space-y-3">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0">
                  <h2 className="text-base font-semibold text-text">Editar dados fixos</h2>
                  <p className="mt-1 text-sm text-muted">
                    Altere as informações que não vêm da integração bancária.
                  </p>
                </div>
                <div className="flex flex-wrap justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => void reloadEditor()}
                    disabled={maintenance.isFetching || saveMaintenance.isPending}
                    className="inline-flex h-9 items-center gap-2 rounded-md border border-border px-3 text-sm font-medium text-text transition hover:bg-surface2 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <RefreshCw size={15} aria-hidden />
                    Recarregar
                  </button>
                  <button
                    type="button"
                    onClick={() => void saveEditor()}
                    disabled={!editor || saveMaintenance.isPending}
                    className="inline-flex h-9 items-center gap-2 rounded-md bg-accent px-3 text-sm font-semibold text-accentFg transition hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <Save size={15} aria-hidden />
                    {saveMaintenance.isPending ? "Salvando..." : "Salvar tudo"}
                  </button>
                </div>
              </div>
              {editorStatus ? (
                <p className="rounded-md border border-border bg-surface2 px-3 py-2 text-sm text-muted">
                  {editorStatus}
                </p>
              ) : null}
              <div className="grid gap-5 2xl:grid-cols-[minmax(0,1.4fr)_minmax(360px,0.8fr)]">
                <SectionCard title="Perfil familiar">
                  {renderEditorSections(profileEditorSections)}
                </SectionCard>
                <SectionCard title="Regras e traduções">
                  {renderEditorSections(rulesEditorSections)}
                </SectionCard>
              </div>
            </div>
          </>
        )}
      </div>
    </>
  );
}
