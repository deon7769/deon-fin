import type { MaintenanceFamilyProfile, MaintenanceOverrides, MaintenanceResponse } from "./types";

export type MaintenanceSummary = {
  incomeTotal: number;
  cashTotal: number;
  provisionMonthlyTotal: number;
  propertyEquity: number;
  categoryCount: number;
  recurrenceCount: number;
  configuredSections: number;
  missingSections: number;
};

export type MaintenanceSection = {
  key: string;
  label: string;
  count: number;
  total: number | null;
  description: string;
};

export type MaintenanceHealthItem = {
  key: string;
  label: string;
  ok: boolean;
  description: string;
};

export type MaintenanceHealth = {
  status: "ok" | "review";
  items: MaintenanceHealthItem[];
};

export type MissingCategoryTranslationRow = {
  category: string;
  txCount: number;
  totalAbs: number;
};

export type MaintenanceEditorState = {
  receitas: Array<{ membro?: string; valor?: number }>;
  caixa: Array<{ local?: string; valor?: number; aporte_mensal_recorrente?: number }>;
  provisoes: Array<{
    nome?: string;
    mensal?: number;
    alvo?: number;
    periodicidade_meses?: number;
    proxima_ocorrencia?: string;
  }>;
  metas: Array<{ nome?: string; alvo?: number; atual?: number; prazo?: string }>;
  wishlist: Array<{
    nome?: string;
    valor_alvo?: number;
    prazo_meses?: number;
    guardado?: number;
    prioridade?: number;
  }>;
  imoveis: Array<{
    nome?: string;
    valor_mercado?: number;
    saldo_devedor?: number;
    taxa_juros_anual?: number;
    prazo_restante_meses?: number;
    aluguel_receita?: number;
    custo_financiamento?: number;
    custo_condominio?: number;
    custo_iptu_lixo?: number;
  }>;
  categorias: Array<{ en?: string; pt?: string }>;
  recorrencias: Array<{ match?: string; tipo?: string; rotulo?: string }>;
};

export type MaintenanceSavePayload = {
  family_profile: MaintenanceFamilyProfile;
  overrides: MaintenanceOverrides;
};

type MaintenanceProperty = NonNullable<
  NonNullable<MaintenanceFamilyProfile["patrimonio"]>["imoveis"]
>[number];

function asArray<T>(value: T[] | undefined): T[] {
  return Array.isArray(value) ? value : [];
}

function numberValue(value: unknown): number {
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function sumBy<T>(items: T[], getValue: (item: T) => unknown): number {
  return items.reduce((total, item) => total + numberValue(getValue(item)), 0);
}

function categoryEntries(data: MaintenanceResponse): Array<[string, string]> {
  return Object.entries(data.overrides?.categorias_pt ?? {}).filter(
    ([key, value]) => key.trim() && value.trim(),
  );
}

function configuredCount(section: MaintenanceSection): number {
  return section.count > 0 ? 1 : 0;
}

export function maintenanceSummary(data: MaintenanceResponse): MaintenanceSummary {
  const profile = data.family_profile ?? {};
  const patrimonio = profile.patrimonio ?? {};
  const receitas = asArray(profile.receitas);
  const caixa = asArray(patrimonio.investimentos_caixa);
  const provisoes = asArray(profile.provisoes);
  const metas = asArray(profile.metas);
  const wishlist = asArray(profile.wishlist);
  const imoveis = asArray(patrimonio.imoveis);
  const categorias = categoryEntries(data);
  const recorrencias = asArray(data.overrides?.recorrencias);
  const propertyEquity = imoveis.reduce(
    (total, imovel) =>
      total + numberValue(imovel.valor_mercado) - numberValue(imovel.saldo_devedor),
    0,
  );
  const sections = [
    receitas.length,
    caixa.length,
    provisoes.length,
    metas.length,
    wishlist.length,
    imoveis.length,
    categorias.length,
    recorrencias.length,
  ];

  return {
    incomeTotal: sumBy(receitas, (item) => item.valor),
    cashTotal: sumBy(caixa, (item) => item.valor),
    provisionMonthlyTotal: sumBy(provisoes, (item) => item.mensal),
    propertyEquity,
    categoryCount: categorias.length,
    recurrenceCount: recorrencias.length,
    configuredSections: sections.filter((count) => count > 0).length,
    missingSections: sections.filter((count) => count === 0).length,
  };
}

export function buildMaintenanceSections(data: MaintenanceResponse): MaintenanceSection[] {
  const profile = data.family_profile ?? {};
  const patrimonio = profile.patrimonio ?? {};
  const receitas = asArray(profile.receitas);
  const caixa = asArray(patrimonio.investimentos_caixa);
  const provisoes = asArray(profile.provisoes);
  const metas = asArray(profile.metas);
  const wishlist = asArray(profile.wishlist);
  const imoveis = asArray(patrimonio.imoveis);
  const categorias = categoryEntries(data);
  const recorrencias = asArray(data.overrides?.recorrencias);

  return [
    {
      key: "receitas",
      label: "Receitas",
      count: receitas.length,
      total: sumBy(receitas, (item) => item.valor),
      description: "Renda informada usada como referência do orçamento.",
    },
    {
      key: "caixa",
      label: "Reserva e caixa",
      count: caixa.length,
      total: sumBy(caixa, (item) => item.valor),
      description: "Reservas, investimentos líquidos e aportes recorrentes.",
    },
    {
      key: "provisoes",
      label: "Provisões",
      count: provisoes.length,
      total: sumBy(provisoes, (item) => item.mensal),
      description: "Compromissos mensais planejados fora da integração bancária.",
    },
    {
      key: "metas",
      label: "Metas familiares",
      count: metas.length,
      total: sumBy(metas, (item) => item.alvo),
      description: "Metas fixas registradas no perfil familiar.",
    },
    {
      key: "wishlist",
      label: "Wishlist",
      count: wishlist.length,
      total: sumBy(wishlist, (item) => item.valor_alvo),
      description: "Desejos e objetivos que alimentam análises de poupança.",
    },
    {
      key: "imoveis",
      label: "Imóveis",
      count: imoveis.length,
      total: imoveis.reduce(
        (total, imovel) =>
          total + numberValue(imovel.valor_mercado) - numberValue(imovel.saldo_devedor),
        0,
      ),
      description: "Patrimônio imobiliário líquido estimado.",
    },
    {
      key: "categorias",
      label: "Tradução de categorias",
      count: categorias.length,
      total: null,
      description: "De/para Pluggy em inglês para nomes em português.",
    },
    {
      key: "recorrencias",
      label: "Recorrências",
      count: recorrencias.length,
      total: null,
      description: "Regras para assinatura, recorrência ou ignorar.",
    },
  ];
}

export function buildMaintenanceHealth(data: MaintenanceResponse): MaintenanceHealth {
  const items = buildMaintenanceSections(data).map((section) => ({
    key: section.key,
    label: section.label,
    ok: section.count > 0,
    description:
      section.count > 0
        ? `${section.count} registro(s) configurado(s).`
        : "Sem dados configurados nesta seção.",
  }));

  return {
    status: items.every((item) => item.ok) ? "ok" : "review",
    items,
  };
}

export function configuredSectionCount(sections: MaintenanceSection[]): number {
  return sections.reduce((total, section) => total + configuredCount(section), 0);
}

export function recurrenceTypeLabel(type: string | undefined): string {
  if (type === "assinatura") {
    return "Assinatura";
  }
  if (type === "recorrencia") {
    return "Recorrência";
  }
  if (type === "ignorar") {
    return "Ignorar";
  }
  return type ?? "";
}

export function missingCategoryTranslations(
  data: MaintenanceResponse,
): MissingCategoryTranslationRow[] {
  return (data.category_audit?.missing ?? []).map((row) => ({
    category: row.category,
    txCount: row.tx_count,
    totalAbs: row.total_abs,
  }));
}

function cloneRows<T extends object>(rows: T[] | undefined): T[] {
  return asArray(rows).map((row) => ({ ...row }));
}

function imovelToEditorRow(imovel: MaintenanceProperty): MaintenanceEditorState["imoveis"][number] {
  const custos = imovel.custos ?? {};
  return {
    nome: imovel.nome,
    valor_mercado: imovel.valor_mercado,
    saldo_devedor: imovel.saldo_devedor,
    taxa_juros_anual: imovel.taxa_juros_anual,
    prazo_restante_meses: imovel.prazo_restante_meses,
    aluguel_receita: imovel.aluguel_receita,
    custo_financiamento: custos.financiamento,
    custo_condominio: custos.condominio,
    custo_iptu_lixo: custos.iptu_lixo,
  };
}

function editorRowToImovel(row: MaintenanceEditorState["imoveis"][number]) {
  return {
    nome: row.nome,
    valor_mercado: row.valor_mercado,
    saldo_devedor: row.saldo_devedor,
    taxa_juros_anual: row.taxa_juros_anual,
    prazo_restante_meses: row.prazo_restante_meses,
    aluguel_receita: row.aluguel_receita,
    custos: {
      financiamento: row.custo_financiamento,
      condominio: row.custo_condominio,
      iptu_lixo: row.custo_iptu_lixo,
    },
  };
}

export function hasMeaningfulRow(row: Record<string, unknown>): boolean {
  return Object.values(row).some((value) => {
    if (typeof value === "number") {
      return value !== 0 && Number.isFinite(value);
    }
    if (typeof value === "string") {
      return value.trim().length > 0;
    }
    return value !== null && value !== undefined;
  });
}

function cleanRows<T extends Record<string, unknown>>(rows: T[]): T[] {
  return rows.filter(hasMeaningfulRow).map((row) => ({ ...row }));
}

export function emptyMaintenanceRow<K extends keyof MaintenanceEditorState>(
  kind: K,
): MaintenanceEditorState[K][number] {
  if (kind === "recorrencias") {
    return { tipo: "recorrencia" } as MaintenanceEditorState[K][number];
  }
  return {} as MaintenanceEditorState[K][number];
}

export function maintenanceToEditorState(data: MaintenanceResponse): MaintenanceEditorState {
  const profile = data.family_profile ?? {};
  const patrimonio = profile.patrimonio ?? {};

  return {
    receitas: cloneRows(profile.receitas),
    caixa: cloneRows(patrimonio.investimentos_caixa),
    provisoes: cloneRows(profile.provisoes),
    metas: cloneRows(profile.metas),
    wishlist: cloneRows(profile.wishlist),
    imoveis: asArray(patrimonio.imoveis).map(imovelToEditorRow),
    categorias: Object.entries(data.overrides?.categorias_pt ?? {}).map(([en, pt]) => ({
      en,
      pt,
    })),
    recorrencias: cloneRows(data.overrides?.recorrencias),
  };
}

export function buildMaintenanceSavePayload(
  original: MaintenanceResponse,
  editor: MaintenanceEditorState,
): MaintenanceSavePayload {
  const familyProfile: MaintenanceFamilyProfile = { ...(original.family_profile ?? {}) };
  const patrimonio = { ...(familyProfile.patrimonio ?? {}) };

  familyProfile.receitas = cleanRows(editor.receitas);
  familyProfile.provisoes = cleanRows(editor.provisoes);
  familyProfile.metas = cleanRows(editor.metas);
  familyProfile.wishlist = cleanRows(editor.wishlist);
  familyProfile.patrimonio = {
    ...patrimonio,
    investimentos_caixa: cleanRows(editor.caixa),
    imoveis: cleanRows(editor.imoveis).map(editorRowToImovel),
  };

  const categorias_pt: Record<string, string> = {};
  for (const row of cleanRows(editor.categorias)) {
    const key = String(row.en ?? "").toLowerCase().trim();
    const value = String(row.pt ?? "").trim();
    if (key && value) {
      categorias_pt[key] = value;
    }
  }

  const recorrencias = cleanRows(editor.recorrencias).map((row) => ({
    match: String(row.match ?? "").trim(),
    tipo: String(row.tipo ?? "recorrencia").trim() || "recorrencia",
    rotulo: String(row.rotulo ?? "").trim(),
  }));

  return {
    family_profile: familyProfile,
    overrides: { categorias_pt, recorrencias },
  };
}
