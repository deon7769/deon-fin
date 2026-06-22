import { formatBRL } from "./format";

export type CalculatorKey =
  | "juros-compostos"
  | "renda"
  | "pix-parcelado"
  | "cdb"
  | "marcacao-mercado"
  | "amortizacao"
  | "imovel";

export type SimulationPayload = Record<string, unknown>;

export type SimulationSeriesRow = {
  mes?: number;
  [key: string]: unknown;
};

export type SimulationResponse = {
  resumo: Record<string, unknown>;
  serie?: SimulationSeriesRow[];
  avisos?: Array<{ code: string; message: string }>;
};

export type CalculatorDefinition = {
  key: CalculatorKey;
  label: string;
  description: string;
};

export type CalculatorField = {
  key: string;
  label: string;
  type: "number" | "text" | "date" | "select" | "checkbox" | "json";
  options?: Array<{ value: string; label: string }>;
};

const TAX_PERIOD_OPTIONS = [
  { value: "anual", label: "Anual" },
  { value: "mensal", label: "Mensal" },
];

const TERM_UNIT_OPTIONS = [
  { value: "anos", label: "Anos" },
  { value: "meses", label: "Meses" },
];

const YES_NO_OPTIONS = [
  { value: "true", label: "Sim" },
  { value: "false", label: "Não" },
];

export const CALCULATORS: CalculatorDefinition[] = [
  {
    key: "juros-compostos",
    label: "Juros Compostos",
    description: "Acumulação com aporte mensal.",
  },
  {
    key: "renda",
    label: "Renda / Retiradas",
    description: "Decumulação com retirada mensal.",
  },
  {
    key: "pix-parcelado",
    label: "Pix Parcelado",
    description: "CET e juros de parcelamento.",
  },
  {
    key: "cdb",
    label: "CDB",
    description: "Rendimento bruto, IR e líquido.",
  },
  {
    key: "marcacao-mercado",
    label: "Marcação a Mercado",
    description: "Alvo a bater antes de vender.",
  },
  {
    key: "amortizacao",
    label: "Amortização",
    description: "Tabela completa com aportes extras.",
  },
  {
    key: "imovel",
    label: "Alugar ou Financiar",
    description: "Patrimônio líquido das duas estratégias.",
  },
];

export const DEFAULT_INPUTS: Record<CalculatorKey, SimulationPayload> = {
  "juros-compostos": {
    valor_inicial: 500,
    valor_mensal: 500,
    taxa: 8,
    taxa_periodo: "anual",
    periodo: 1,
    periodo_unidade: "anos",
  },
  renda: {
    valor_inicial: 200000,
    retirada_mensal: 800,
    taxa: 13,
    taxa_periodo: "anual",
    periodo: 10,
    periodo_unidade: "anos",
  },
  "pix-parcelado": {
    valor_pix: 1000,
    n_parcelas: 4,
    juros_mensal_pct: 2,
    incluir_valor_parcela: false,
  },
  cdb: {
    investimento_inicial: 1000,
    investimento_mensal: 0,
    cdi_pct: 100,
    tempo: 1,
    tempo_unidade: "anos",
  },
  "marcacao-mercado": {
    tipo: "prefixado",
    data_aplicacao: "2026-01-01",
    data_vencimento: "2030-01-01",
    valor_investido: 10000,
    valor_atual_bruto: 10500,
    rentabilidade_contratada_aa: 10,
    isento_ir: false,
    rentabilidade_nova_oferta_aa: 12,
  },
  amortizacao: {
    valor_emprestimo: 12000,
    data_inicio: "2026-01-01",
    sistema: "price",
    taxa: 12,
    taxa_periodo: "anual",
    n_parcelas: 12,
    correcao: "nenhuma",
    aportes_extra: [{ mes: 1, valor: 1000 }],
    modo_aporte: "reduzir_prazo",
    seguros_taxas_mensal: 0,
  },
  imovel: {
    valor_imovel: 300000,
    entrada: 60000,
    custos_financiamento: 10000,
    prazo_meses: 24,
    taxa_aa: 10,
    sistema: "price",
    aluguel_mensal: 1800,
    reajuste_aluguel_aa: 5,
    rendimento_investimento_aa: 8,
    valorizacao_imovel_aa: 4,
  },
};

export const CALCULATOR_FIELDS: Record<CalculatorKey, CalculatorField[]> = {
  "juros-compostos": [
    { key: "valor_inicial", label: "Valor inicial", type: "number" },
    { key: "valor_mensal", label: "Aporte mensal", type: "number" },
    { key: "taxa", label: "Taxa", type: "number" },
    { key: "taxa_periodo", label: "Período da taxa", type: "select", options: TAX_PERIOD_OPTIONS },
    { key: "periodo", label: "Prazo", type: "number" },
    { key: "periodo_unidade", label: "Unidade do prazo", type: "select", options: TERM_UNIT_OPTIONS },
  ],
  renda: [
    { key: "valor_inicial", label: "Valor inicial", type: "number" },
    { key: "retirada_mensal", label: "Retirada mensal", type: "number" },
    { key: "taxa", label: "Taxa", type: "number" },
    { key: "taxa_periodo", label: "Período da taxa", type: "select", options: TAX_PERIOD_OPTIONS },
    { key: "periodo", label: "Prazo", type: "number" },
    { key: "periodo_unidade", label: "Unidade do prazo", type: "select", options: TERM_UNIT_OPTIONS },
  ],
  "pix-parcelado": [
    { key: "valor_pix", label: "Valor do Pix", type: "number" },
    { key: "n_parcelas", label: "Número de parcelas", type: "number" },
    { key: "juros_mensal_pct", label: "Juros mensal (%)", type: "number" },
    { key: "incluir_valor_parcela", label: "Calcular taxa pela parcela", type: "select", options: YES_NO_OPTIONS },
    { key: "valor_parcela", label: "Valor da parcela", type: "number" },
  ],
  cdb: [
    { key: "investimento_inicial", label: "Investimento inicial", type: "number" },
    { key: "investimento_mensal", label: "Investimento mensal", type: "number" },
    { key: "cdi_pct", label: "% do CDI", type: "number" },
    { key: "tempo", label: "Prazo", type: "number" },
    { key: "tempo_unidade", label: "Unidade do prazo", type: "select", options: TERM_UNIT_OPTIONS },
    { key: "cdi_aa", label: "CDI anual (%)", type: "number" },
  ],
  "marcacao-mercado": [
    { key: "tipo", label: "Tipo do título", type: "select", options: [
      { value: "prefixado", label: "Prefixado" },
      { value: "ipca", label: "IPCA+" },
    ] },
    { key: "data_aplicacao", label: "Data da aplicação", type: "date" },
    { key: "data_vencimento", label: "Data de vencimento", type: "date" },
    { key: "valor_investido", label: "Valor investido", type: "number" },
    { key: "valor_atual_bruto", label: "Valor atual bruto", type: "number" },
    { key: "rentabilidade_contratada_aa", label: "Taxa contratada a.a. (%)", type: "number" },
    { key: "isento_ir", label: "Título isento de IR", type: "select", options: YES_NO_OPTIONS },
    { key: "ipca_projetado_aa", label: "IPCA projetado a.a. (%)", type: "number" },
    { key: "rentabilidade_nova_oferta_aa", label: "Nova oferta a.a. (%)", type: "number" },
  ],
  amortizacao: [
    { key: "valor_emprestimo", label: "Valor do empréstimo", type: "number" },
    { key: "data_inicio", label: "Data de início", type: "date" },
    { key: "sistema", label: "Sistema", type: "select", options: [
      { value: "price", label: "Price" },
      { value: "sac", label: "SAC" },
    ] },
    { key: "taxa", label: "Taxa", type: "number" },
    { key: "taxa_periodo", label: "Período da taxa", type: "select", options: TAX_PERIOD_OPTIONS },
    { key: "n_parcelas", label: "Número de parcelas", type: "number" },
    { key: "correcao", label: "Correção", type: "select", options: [
      { value: "nenhuma", label: "Nenhuma" },
      { value: "tr", label: "TR" },
      { value: "ipca", label: "IPCA" },
    ] },
    { key: "aportes_extra", label: "Aportes extras", type: "json" },
    { key: "modo_aporte", label: "Modo do aporte", type: "select", options: [
      { value: "reduzir_prazo", label: "Reduzir prazo" },
      { value: "reduzir_parcela", label: "Reduzir parcela" },
    ] },
    { key: "seguros_taxas_mensal", label: "Seguros e taxas mensais", type: "number" },
  ],
  imovel: [
    { key: "valor_imovel", label: "Valor do imóvel", type: "number" },
    { key: "entrada", label: "Entrada", type: "number" },
    { key: "custos_financiamento", label: "Custos do financiamento", type: "number" },
    { key: "prazo_meses", label: "Prazo em meses", type: "number" },
    { key: "taxa_aa", label: "Taxa do financiamento a.a. (%)", type: "number" },
    { key: "sistema", label: "Sistema", type: "select", options: [
      { value: "price", label: "Price" },
      { value: "sac", label: "SAC" },
    ] },
    { key: "aluguel_mensal", label: "Aluguel mensal", type: "number" },
    { key: "reajuste_aluguel_aa", label: "Reajuste do aluguel a.a. (%)", type: "number" },
    { key: "rendimento_investimento_aa", label: "Rendimento do investimento a.a. (%)", type: "number" },
    { key: "valorizacao_imovel_aa", label: "Valorização do imóvel a.a. (%)", type: "number" },
  ],
};

export function fieldsForCalculator(key: CalculatorKey): CalculatorField[] {
  return CALCULATOR_FIELDS[key];
}

const SUMMARY_LABELS: Record<string, string> = {
  valor_final: "Valor final",
  total_investido: "Total investido",
  total_juros: "Total juros",
  valor_liquido: "Valor líquido",
  valor_bruto: "Valor bruto",
  valor_parcela: "Valor parcela",
  total_pago: "Total pago",
  tir_implicita_aa: "Alvo a bater",
  parcela_inicial: "Parcela inicial",
  patrimonio_final_comprar: "Patrimônio comprar",
  patrimonio_final_alugar: "Patrimônio alugar",
  vantagem: "Vantagem",
};

export function endpointForCalculator(key: CalculatorKey): string {
  return `/sim/${key}`;
}

function labelFor(key: string): string {
  return SUMMARY_LABELS[key] ?? key.replaceAll("_", " ");
}

function isCurrencyKey(key: string): boolean {
  return !/(pct|taxa|tir|aliquota|meses|dias|anos|vantagem|sustentavel|tipo)/.test(key);
}

export function formatSimulationValue(key: string, value: unknown): string {
  if (typeof value === "boolean") {
    return value ? "Sim" : "Não";
  }
  if (typeof value === "number") {
    if (isCurrencyKey(key)) {
      return formatBRL(value);
    }
    return key.includes("pct") || key.includes("tir") || key.includes("aliquota")
      ? `${value.toLocaleString("pt-BR", { maximumFractionDigits: 2 })}%`
      : value.toLocaleString("pt-BR", { maximumFractionDigits: 2 });
  }
  if (value === null || value === undefined) {
    return "--";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

export function summaryCards(result: SimulationResponse) {
  return Object.entries(result.resumo)
    .filter(([, value]) => typeof value !== "object" || value === null)
    .slice(0, 6)
    .map(([key, value]) => ({
      key,
      label: labelFor(key),
      value: formatSimulationValue(key, value),
    }));
}

export function resultRows(result: SimulationResponse) {
  return (result.serie ?? []).map((row, index) => {
    const firstKey = "juros" in row ? "juros" : "parcela" in row ? "parcela" : "patrimonio_comprar";
    const secondKey =
      "total_acumulado" in row
        ? "total_acumulado"
        : "valor_com_retiradas" in row
          ? "valor_com_retiradas"
          : "saldo" in row
            ? "saldo"
            : "patrimonio_alugar";
    return {
      key: String(row.mes ?? index + 1),
      month: String(row.mes ?? index + 1),
      firstMetric: formatSimulationValue(firstKey, row[firstKey]),
      secondMetric: formatSimulationValue(secondKey, row[secondKey]),
    };
  });
}

export function chartRows(result: SimulationResponse) {
  return resultRows(result).map((row) => ({
    mes: row.month,
    metrica1: Number(row.firstMetric.replace(/[^\d,.-]/g, "").replace(/\./g, "").replace(",", ".")) || 0,
    metrica2: Number(row.secondMetric.replace(/[^\d,.-]/g, "").replace(/\./g, "").replace(",", ".")) || 0,
  }));
}
