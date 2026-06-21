import type { MaintenanceResponse } from "./types";

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
