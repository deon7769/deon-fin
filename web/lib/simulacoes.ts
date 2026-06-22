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
};

export type CalculatorDefinition = {
  key: CalculatorKey;
  label: string;
  description: string;
};

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
    data_aplicacao: "2024-01-01",
    data_vencimento: "2026-01-01",
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
