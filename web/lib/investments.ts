import { api } from "@/lib/api";
import type {
  InvestmentAsset,
  InvestmentAssetAnswersInput,
  InvestmentAssetAnswersResponse,
  InvestmentAssetInput,
  InvestmentAporteConfirmInput,
  InvestmentAporteCalculateInput,
  InvestmentAporteResponse,
  InvestmentAporteSuggestion,
  InvestmentCountryDetail,
  InvestmentQuestion,
  InvestmentQuestionInput,
  InvestmentQuestionsResponse,
  InvestmentMapCountry,
  InvestmentProfilePreset,
  InvestmentProfilesResponse,
  InvestmentRefreshQuotesResponse,
  InvestmentTargetsMap,
  InvestmentTargetsResponse,
  InvestmentsResponse,
  InvestmentTickerSearchItem,
} from "@/lib/types";

export const INVESTMENT_CLASSES = [
  { value: "acoes_nac", label: "Ações nacionais" },
  { value: "acoes_int", label: "Ações internacionais" },
  { value: "etf", label: "ETFs" },
  { value: "fii", label: "Fundos imobiliários" },
  { value: "reit", label: "REITs" },
  { value: "cripto", label: "Criptomoedas" },
  { value: "rf", label: "Renda fixa" },
  { value: "rf_int", label: "Renda fixa internacional" },
];

export type InvestmentAssetFormValues = {
  assetClass: string;
  ticker: string;
  name: string;
  quantity: string;
  manualValue: string;
};

export type InvestmentQuestionFormValues = {
  diagramType: string;
  criterio: string;
  pergunta: string;
  peso: string;
  sortOrder: string;
  ativo: boolean;
};

function toNumber(value: string): number | undefined {
  const normalized = value.trim().replace(/\./g, "").replace(",", ".");
  if (!normalized) {
    return undefined;
  }
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function toMoneyNumber(value: number): number {
  return Number(value.toFixed(2));
}

function toRequiredNumber(value: string, fallback: number): number {
  return toNumber(value) ?? fallback;
}

function normalizeText(value: string): string {
  return value.trim().replace(/\s+/g, " ");
}

export function isFixedIncomeClass(assetClass: string) {
  return assetClass === "rf" || assetClass === "rf_int";
}

export function buildAssetPayload(values: InvestmentAssetFormValues): InvestmentAssetInput {
  const assetClass = values.assetClass;
  const name = values.name.trim().replace(/\s+/g, " ");
  if (isFixedIncomeClass(assetClass)) {
    return {
      asset_class: assetClass,
      ...(name ? { name } : {}),
      ...(toNumber(values.manualValue) !== undefined ? { manual_value: toNumber(values.manualValue) } : {}),
    };
  }
  const ticker = values.ticker.trim().toUpperCase();
  return {
    asset_class: assetClass,
    ...(ticker ? { ticker } : {}),
    ...(name ? { name } : {}),
    ...(toNumber(values.quantity) !== undefined ? { quantity: toNumber(values.quantity) } : {}),
  };
}

export function diagramLabel(diagramType: string) {
  if (diagramType === "imobiliario") {
    return "Imobiliario";
  }
  return "Acoes";
}

export function buildQuestionPayload(values: InvestmentQuestionFormValues): InvestmentQuestionInput {
  return {
    diagram_type: values.diagramType,
    criterio: normalizeText(values.criterio) || null,
    pergunta: normalizeText(values.pergunta),
    peso: toRequiredNumber(values.peso, 1),
    sort_order: Math.trunc(toRequiredNumber(values.sortOrder, 0)),
    ativo: values.ativo,
  };
}

export function buildAportePayload(value: string): InvestmentAporteCalculateInput {
  return { aporte: toRequiredNumber(value, 0) };
}

export function investmentSuggestionAporteValue(
  suggestion: InvestmentAporteSuggestion,
  quantity: number,
): number {
  if (Number(suggestion.preco) > 0) {
    return toMoneyNumber(quantity * Number(suggestion.preco));
  }
  return toMoneyNumber(quantity);
}

export function aporteComprasFromSuggestions(result: InvestmentAporteResponse): InvestmentAporteConfirmInput {
  const sugestoes = result.sugestoes.filter(
    (item) => Number(item.sugest_un) > 0 && Number(item.sugest_rs) > 0,
  );
  return {
    aporte: toMoneyNumber(sugestoes.reduce((total, item) => total + Number(item.sugest_rs || 0), 0)),
    compras: sugestoes.map((item) => ({
      asset_id: item.id,
      quantidade: item.sugest_un,
    })),
  };
}

export function sumInvestmentTargets(targets: InvestmentTargetsMap): number {
  return Number(
    Object.values(targets)
      .reduce((total, value) => total + Number(value || 0), 0)
      .toFixed(2),
  );
}

export function investmentTargetStatus(total: number): {
  state: "under" | "valid" | "over";
  message: string;
  canSave: boolean;
} {
  if (Math.abs(total - 100) < 0.001) {
    return { state: "valid", message: "Total completo", canSave: true };
  }
  if (total > 100) {
    const overflow = Number((total - 100).toFixed(2));
    return {
      state: "over",
      message: `O valor ultrapassou ${overflow}% do valor das metas`,
      canSave: false,
    };
  }
  const missing = Number((100 - total).toFixed(2));
  return { state: "under", message: `Faltam ${missing}% para 100%`, canSave: false };
}

export function targetsFromProfile(profile: InvestmentProfilePreset): InvestmentTargetsMap {
  return { ...profile.targets };
}

export function getInvestments(includeInactive = false, signal?: AbortSignal) {
  return api.get<InvestmentsResponse>(
    "/investments",
    includeInactive ? { include_inactive: true } : undefined,
    signal,
  );
}

export function refreshInvestmentQuotes() {
  return api.post<InvestmentRefreshQuotesResponse>("/investments/refresh-quotes");
}

export function searchInvestmentTickers(q: string, classe: string, signal?: AbortSignal) {
  return api
    .get<{ items: InvestmentTickerSearchItem[] }>("/investments/ticker-search", { q, classe }, signal)
    .then((response) => response.items);
}

export function createInvestmentAsset(input: InvestmentAssetInput) {
  return api.post<InvestmentAsset>("/investments/assets", input);
}

export function updateInvestmentAsset(id: number, input: Partial<InvestmentAssetInput>) {
  return api.patch<InvestmentAsset>(`/investments/assets/${id}`, input);
}

export function deleteInvestmentAsset(id: number) {
  return api.del<{ deleted_id: number }>(`/investments/assets/${id}`);
}

export function getInvestmentTargets(signal?: AbortSignal) {
  return api.get<InvestmentTargetsResponse>("/investments/targets", undefined, signal);
}

export function getInvestmentProfiles(signal?: AbortSignal) {
  return api.get<InvestmentProfilesResponse>("/investments/profiles", undefined, signal);
}

export function getInvestmentMap(signal?: AbortSignal) {
  return api.get<InvestmentMapCountry[]>("/investments/map", undefined, signal);
}

export function getInvestmentCountry(code: string, signal?: AbortSignal) {
  return api.get<InvestmentCountryDetail>(
    `/investments/map/${encodeURIComponent(code.toUpperCase())}`,
    undefined,
    signal,
  );
}

export function buildInvestmentCountryDetailsMap(
  countries: Array<InvestmentCountryDetail | undefined | null>,
): Record<string, InvestmentCountryDetail> {
  return countries.reduce<Record<string, InvestmentCountryDetail>>((acc, country) => {
    if (country?.code) {
      acc[country.code.toUpperCase()] = country;
    }
    return acc;
  }, {});
}

export function saveInvestmentTargets(input: { targets: InvestmentTargetsMap; perfil?: string }) {
  return api.put<InvestmentTargetsResponse>("/investments/targets", input);
}

export function calcularInvestmentAporte(input: InvestmentAporteCalculateInput) {
  return api.post<InvestmentAporteResponse>("/investments/aporte/calcular", input);
}

export function confirmarInvestmentAporte(input: InvestmentAporteConfirmInput) {
  return api.post<InvestmentsResponse>("/investments/aporte/confirmar", input);
}

export function getInvestmentQuestions(diagramType: string, signal?: AbortSignal) {
  return api.get<InvestmentQuestionsResponse>(
    "/investments/questions",
    { diagram_type: diagramType },
    signal,
  );
}

export function createInvestmentQuestion(input: InvestmentQuestionInput) {
  return api.post<InvestmentQuestion>("/investments/questions", input);
}

export function updateInvestmentQuestion(id: number, input: Partial<InvestmentQuestionInput>) {
  return api.patch<InvestmentQuestion>(`/investments/questions/${id}`, input);
}

export function deleteInvestmentQuestion(id: number) {
  return api.del<{ deleted_id: number }>(`/investments/questions/${id}`);
}

export function restoreInvestmentQuestions(diagramType: string) {
  return api.post<InvestmentQuestionsResponse>(
    `/investments/questions/restore-defaults?diagram_type=${encodeURIComponent(diagramType)}`,
  );
}

export function getInvestmentAssetAnswers(assetId: number, signal?: AbortSignal) {
  return api.get<InvestmentAssetAnswersResponse>(
    `/investments/assets/${assetId}/answers`,
    undefined,
    signal,
  );
}

export function saveInvestmentAssetAnswers(assetId: number, input: InvestmentAssetAnswersInput) {
  return api.put<InvestmentAssetAnswersResponse>(`/investments/assets/${assetId}/answers`, input);
}
