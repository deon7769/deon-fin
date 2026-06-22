import { api } from "@/lib/api";
import type {
  InvestmentAsset,
  InvestmentAssetAnswersInput,
  InvestmentAssetAnswersResponse,
  InvestmentAssetInput,
  InvestmentQuestion,
  InvestmentQuestionInput,
  InvestmentQuestionsResponse,
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

export function saveInvestmentTargets(input: { targets: InvestmentTargetsMap; perfil?: string }) {
  return api.put<InvestmentTargetsResponse>("/investments/targets", input);
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
