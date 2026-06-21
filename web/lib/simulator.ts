import { formatBRL } from "@/lib/format";
import type {
  AmortizationRequest,
  AmortizationResponse,
  MaintenanceResponse,
  ScenarioSimulationRequest,
  ScenarioSimulationResponse,
} from "@/lib/types";

export type ValidationResult = { valid: true } | { valid: false; message: string };
export type ResultTone = "neutral" | "positive" | "negative";

export type ScenarioPresetKey = "carro" | "imovel";

export type ScenarioSummaryItem = {
  label: string;
  value: string;
  tone: ResultTone;
};

export type ScenarioSummaryCard = {
  key: "financiar" | "consorcio" | "juntar";
  title: string;
  subtitle: string;
  items: ScenarioSummaryItem[];
};

export type AmortizationRow = {
  key: "sem_extra" | "com_extra" | "economia";
  label: string;
  months: string;
  interest: string;
  tone: ResultTone;
};

export const DEFAULT_SCENARIO_INPUT: ScenarioSimulationRequest = {
  preco: 50000,
  entrada: 10000,
  prazo_meses: 48,
  juros_aa: 24,
  sobra_mensal: 0,
  rendimento_aa: 10,
  taxa_adm_consorcio: 18,
};

export const SCENARIO_PRESETS: Record<ScenarioPresetKey, ScenarioSimulationRequest> = {
  carro: {
    ...DEFAULT_SCENARIO_INPUT,
    preco: 80000,
    entrada: 20000,
    prazo_meses: 48,
    juros_aa: 26,
    rendimento_aa: 11,
  },
  imovel: {
    ...DEFAULT_SCENARIO_INPUT,
    preco: 300000,
    entrada: 60000,
    prazo_meses: 360,
    juros_aa: 9,
    rendimento_aa: 11,
  },
};

export const DEFAULT_AMORTIZATION_INPUT: AmortizationRequest = {
  saldo: 32200.6,
  juros_aa: 4.5,
  parcela: 395,
  aporte_extra: 500,
};

function finiteNumber(value: number): boolean {
  return Number.isFinite(value);
}

function monthlyRate(annualPercent: number): number {
  return (1 + annualPercent / 100) ** (1 / 12) - 1;
}

function monthsText(months: number | null | undefined): string {
  return typeof months === "number" ? `${months} meses` : "não quita";
}

function timeToSaveText(months: number | null, years: number | null): string {
  if (!months) {
    return "não atinge";
  }
  if (!years) {
    return `${months} meses`;
  }
  return `${months} meses (~${years.toLocaleString("pt-BR", { maximumFractionDigits: 1 })} anos)`;
}

export function validateScenarioInput(input: ScenarioSimulationRequest): ValidationResult {
  if (!finiteNumber(input.preco) || input.preco <= 0) {
    return { valid: false, message: "Informe um preço maior que zero." };
  }
  if (!finiteNumber(input.entrada) || input.entrada < 0) {
    return { valid: false, message: "Informe uma entrada válida." };
  }
  if (input.entrada > input.preco) {
    return { valid: false, message: "A entrada não pode ser maior que o preço." };
  }
  if (!finiteNumber(input.prazo_meses) || input.prazo_meses < 1) {
    return { valid: false, message: "Informe um prazo de pelo menos 1 mês." };
  }
  if (!finiteNumber(input.juros_aa) || input.juros_aa < 0) {
    return { valid: false, message: "Informe uma taxa de juros válida." };
  }
  if (!finiteNumber(input.sobra_mensal) || input.sobra_mensal < 0) {
    return { valid: false, message: "A sobra mensal não pode ser negativa." };
  }
  if (!finiteNumber(input.rendimento_aa) || input.rendimento_aa < 0) {
    return { valid: false, message: "O rendimento não pode ser negativo." };
  }
  if (!finiteNumber(input.taxa_adm_consorcio) || input.taxa_adm_consorcio < 0) {
    return { valid: false, message: "A taxa de administração não pode ser negativa." };
  }
  return { valid: true };
}

export function validateAmortizationInput(input: AmortizationRequest): ValidationResult {
  if (!finiteNumber(input.saldo) || input.saldo <= 0) {
    return { valid: false, message: "Informe um saldo devedor maior que zero." };
  }
  if (!finiteNumber(input.juros_aa) || input.juros_aa < 0) {
    return { valid: false, message: "Informe uma taxa de juros válida." };
  }
  if (!finiteNumber(input.parcela) || input.parcela <= 0) {
    return { valid: false, message: "Informe uma parcela maior que zero." };
  }
  if (!finiteNumber(input.aporte_extra) || input.aporte_extra < 0) {
    return { valid: false, message: "O aporte extra não pode ser negativo." };
  }

  const firstMonthInterest = input.saldo * monthlyRate(input.juros_aa);
  if (firstMonthInterest > 0 && input.parcela <= firstMonthInterest) {
    return { valid: false, message: "A parcela precisa cobrir os juros do primeiro mês." };
  }

  return { valid: true };
}

export function scenarioSummary(result: ScenarioSimulationResponse): ScenarioSummaryCard[] {
  return [
    {
      key: "financiar",
      title: "Financiar",
      subtitle: `Valor financiado ${formatBRL(result.valor_financiado)} com entrada de ${formatBRL(result.entrada)}.`,
      items: [
        {
          label: "Parcela Price",
          value: `${formatBRL(result.financiar.price.parcela)}/mês`,
          tone: "neutral",
        },
        {
          label: "Total pago Price",
          value: formatBRL(result.financiar.custo_total_price),
          tone: "negative",
        },
        {
          label: "Juros Price",
          value: formatBRL(result.financiar.price.total_juros),
          tone: "negative",
        },
        {
          label: "SAC 1ª → última",
          value: `${formatBRL(result.financiar.sac.primeira_parcela)} → ${formatBRL(result.financiar.sac.ultima_parcela)}`,
          tone: "neutral",
        },
        {
          label: "Total pago SAC",
          value: formatBRL(result.financiar.custo_total_sac),
          tone: "negative",
        },
      ],
    },
    {
      key: "consorcio",
      title: "Consórcio",
      subtitle: `Sem juros, com taxa administrativa de ${result.consorcio.taxa_adm_pct}%.`,
      items: [
        {
          label: "Parcela",
          value: `${formatBRL(result.consorcio.parcela)}/mês`,
          tone: "neutral",
        },
        {
          label: "Total pago",
          value: formatBRL(result.consorcio.total_parcelas),
          tone: "negative",
        },
        {
          label: "Custo da taxa",
          value: formatBRL(result.consorcio.custo_taxa_adm),
          tone: "negative",
        },
      ],
    },
    {
      key: "juntar",
      title: "Juntar à vista",
      subtitle: `Guardando ${formatBRL(result.juntar_a_vista.aporte_mensal)}/mês a ${result.juntar_a_vista.rendimento_aa}% a.a.`,
      items: [
        {
          label: "Tempo para juntar",
          value: timeToSaveText(
            result.juntar_a_vista.meses_para_juntar,
            result.juntar_a_vista.anos_para_juntar,
          ),
          tone: "neutral",
        },
        {
          label: "Custo à vista",
          value: formatBRL(result.juntar_a_vista.custo_total),
          tone: "positive",
        },
        {
          label: "Economia vs. Price",
          value: formatBRL(result.economia_juntando_vs_price),
          tone: "positive",
        },
      ],
    },
  ];
}

export function amortizationRows(result: AmortizationResponse): AmortizationRow[] {
  return [
    {
      key: "sem_extra",
      label: "Sem aporte extra",
      months: monthsText(result.sem_extra?.meses),
      interest: result.sem_extra ? formatBRL(result.sem_extra.juros_pagos) : "não quita",
      tone: "neutral",
    },
    {
      key: "com_extra",
      label: `Com aporte de ${formatBRL(result.aporte_extra)}/mês`,
      months: monthsText(result.com_extra?.meses),
      interest: result.com_extra ? formatBRL(result.com_extra.juros_pagos) : "não quita",
      tone: "positive",
    },
    {
      key: "economia",
      label: "Você economiza",
      months: monthsText(result.meses_economizados),
      interest:
        typeof result.juros_economizados === "number"
          ? formatBRL(result.juros_economizados)
          : "sem economia",
      tone: "positive",
    },
  ];
}

export function propertyToAmortizationInput(
  maintenance: MaintenanceResponse | null | undefined,
): AmortizationRequest | null {
  const property = maintenance?.family_profile.patrimonio?.imoveis?.[0];
  if (!property) {
    return null;
  }

  const saldo = Number(property.saldo_devedor ?? DEFAULT_AMORTIZATION_INPUT.saldo);
  const juros = Number(property.taxa_juros_anual ?? DEFAULT_AMORTIZATION_INPUT.juros_aa);
  const parcela = Number(
    property.custos?.financiamento ?? DEFAULT_AMORTIZATION_INPUT.parcela,
  );

  return {
    saldo: finiteNumber(saldo) && saldo > 0 ? saldo : DEFAULT_AMORTIZATION_INPUT.saldo,
    juros_aa: finiteNumber(juros) && juros >= 0 ? juros : DEFAULT_AMORTIZATION_INPUT.juros_aa,
    parcela: finiteNumber(parcela) && parcela > 0 ? parcela : DEFAULT_AMORTIZATION_INPUT.parcela,
    aporte_extra: DEFAULT_AMORTIZATION_INPUT.aporte_extra,
  };
}
