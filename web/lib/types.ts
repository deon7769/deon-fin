export type ApiErrorShape = {
  error: {
    code: string;
    message: string;
  };
};

export type Page<T> = {
  items: T[];
  page: number;
  page_size: number;
  total: number;
};

export type Bucket = {
  id: number;
  key: string;
  name: string;
  color?: string | null;
  planned_kind?: "percent" | "amount" | null;
  planned_value?: number | null;
  sort_order?: number;
};

export type Tag = {
  id: number;
  name: string;
  color?: string | null;
  bucket_id?: number | null;
  bucket_key?: string | null;
  bucket_name?: string | null;
  bucket_color?: string | null;
  tx_count?: number;
};

export type Profile = {
  id: number;
  name: string;
  email: string;
  monthly_income: number;
  financial_month_start_day: number;
  goals_text: string;
  initials: string;
  updated_at?: string | null;
};

export type TransactionType = "income" | "expense";

export type TransactionHiddenFilter = "exclude" | "include" | "only";

export type TransactionSummary = {
  income: number;
  expense: number;
  balance: number;
};

export type Transaction = {
  id: string;
  account_id: string;
  posted_at: string;
  amount: number;
  description: string;
  raw_description?: string | null;
  category?: string | null;
  category_label?: string | null;
  category_source?: string | null;
  source: string;
  external_id?: string | null;
  bucket_id?: number | null;
  bucket_source?: string | null;
  bucket?: Pick<Bucket, "id" | "name" | "color"> | null;
  tag_id?: number | null;
  tag_source?: string | null;
  tag?: Pick<Tag, "id" | "name" | "color"> | null;
  savings_goal_id?: number | null;
  savings_goal_name?: string | null;
  reference_month?: string | null;
  hidden: boolean;
  note?: string | null;
  account_name?: string | null;
  account_type?: string | null;
  signed_value: number;
  display_value?: number;
  type: TransactionType;
};

export type TransactionPage = Page<Transaction> & {
  summary: TransactionSummary;
};

export type PainelSummary = {
  month: string;
  result: number;
  income: number;
  expense: number;
  accounts_balance: number;
  accounts_balance_available: boolean;
};

export type PainelHistoryWindow = "3m" | "6m" | "1a";

export type PainelHistoryPoint = {
  month: string;
  income: number;
  expense: number;
};

export type PainelTagType = "expense" | "income";

export type PainelTagSlice = {
  tag_id: number | null;
  tag_name: string;
  color: string | null;
  total: number;
};

export type PainelByTag = {
  month: string;
  type: PainelTagType;
  total: number;
  items: PainelTagSlice[];
};

export type BudgetIncomeSource =
  | "transactions"
  | "profile"
  | "settings"
  | "family_profile"
  | "none";

export type BudgetCategory = {
  id: number;
  key: string;
  name: string;
  color: string | null;
  planned_kind: "percent" | "amount";
  planned_value: number;
  planned: number;
  spent: number;
  remaining: number;
  used_pct: number | null;
  exceeded: boolean;
  tx_count: number;
};

export type BudgetUncategorized = {
  id: string;
  description: string;
  date: string;
  amount: number;
};

export type Budget = {
  month: string;
  income: number;
  spent: number;
  remaining: number;
  used_pct: number | null;
  income_source: BudgetIncomeSource;
  categories: BudgetCategory[];
  uncategorized: BudgetUncategorized[];
};

export type BucketPlanWarning = {
  code: string;
  message: string;
};

export type BucketPlanItem = {
  id: number;
  key: string;
  name: string;
  color: string | null;
  planned_kind: "percent" | "amount";
  planned_value: number;
  planned_amount: number;
  spent_month: number;
};

export type BucketPlanResponse = {
  month: string;
  income: number;
  income_source: BudgetIncomeSource;
  buckets: BucketPlanItem[];
  sum_percent: number;
  sum_amount: number;
  warning: BucketPlanWarning | null;
};

export type SavingsGoal = {
  id: number;
  name: string;
  target_amount: number;
  term_months: number;
  saved_amount: number;
  saved_manual?: number;
  saved_from_tx?: number;
  saved_total?: number;
  linked_count?: number;
  priority: number;
  monthly_required: number;
  progress_pct: number;
  fits_surplus: boolean;
  created_at?: string;
  updated_at?: string;
};

export type SavingsGoalsResponse = {
  month: string;
  goals: SavingsGoal[];
  total_monthly_required: number;
  monthly_surplus: number;
  surplus_after_goals: number;
};

export type CardItem = {
  id: string;
  name: string;
  brand: string | null;
  last4: string | null;
  credit_limit: number | null;
  available: number | null;
  currency: string;
};

export type InvoiceInstallment = {
  n: number;
  of: number;
};

export type Invoice = {
  account_id: string;
  account_name: string;
  reference_month: string;
  total: number;
  closing_date: string;
  due_date: string;
  paid: boolean;
  approximate_dates: boolean;
  count: number;
};

export type InvoiceItem = {
  id: string;
  account_id: string;
  date: string;
  description: string;
  amount: number;
  signed_value: number;
  category: string;
  category_label?: string | null;
  bucket: Pick<Bucket, "id" | "name" | "color"> | null;
  bucket_source?: string | null;
  tag: Pick<Tag, "id" | "name" | "color"> | null;
  installment: InvoiceInstallment | null;
};

export type InvoiceCategory = {
  name: string;
  label?: string | null;
  color: string | null;
  total: number;
};

export type InvoiceResponse = {
  invoice: Invoice;
  items: InvoiceItem[];
  by_category: InvoiceCategory[];
};

export type AccountBank = {
  id: string;
  institution: string | null;
  name: string;
  type: string;
  agency: string | null;
  number: string | null;
  balance: number;
  currency: string;
  pluggy_item_id: string | null;
  connector_name: string | null;
  last_sync_at: string | null;
  sync_status: string;
  manual: boolean;
};

export type AccountCard = {
  id: string;
  name: string;
  last4: string | null;
  brand: string | null;
  credit_limit: number | null;
  used: number | null;
  available: number | null;
  usage_pct: number | null;
  currency: string;
  pluggy_item_id: string | null;
  connector_name: string | null;
  last_sync_at: string | null;
  sync_status: string;
  manual: boolean;
};

export type AccountsTotals = {
  accounts_balance: number;
  card_debt: number;
  period_result: number;
};

export type AccountsSync = {
  running: boolean;
  last_started: string | null;
  last_finished: string | null;
  last_result: string | null;
  scheduler_on: boolean;
  auto_sync_minutes: number;
};

export type AccountsResponse = {
  banks: AccountBank[];
  cards: AccountCard[];
  totals: AccountsTotals;
  sync: AccountsSync;
};

export type InvestmentAsset = {
  id: number;
  asset_class: string;
  asset_class_label: string;
  ticker: string | null;
  name: string | null;
  quantity: number;
  source: string;
  external_id: string | null;
  manual_value: number | null;
  current_value: number;
  unit_price: number | null;
  currency: string;
  provider_type: string | null;
  provider_subtype: string | null;
  status: string | null;
  as_of_date: string | null;
  manually_adjusted: boolean;
  manual_adjusted_at: string | null;
  price_source: string | null;
  price_updated_at: string | null;
  nota?: number | null;
  pct_carteira: number;
  created_at: string;
  updated_at: string;
};

export type InvestmentRefreshQuotesResponse = {
  quoted: number;
  updated: number;
  skipped: number;
};

export type InvestmentAssetInput = {
  asset_class: string;
  ticker?: string;
  name?: string;
  quantity?: number;
  manual_value?: number;
};

export type InvestmentTickerSearchItem = {
  ticker: string;
  name: string;
};

export type InvestmentTargetsMap = Record<string, number>;

export type InvestmentTargetClass = {
  asset_class: string;
  label: string;
  target_pct: number;
};

export type InvestmentTargetsResponse = {
  targets: InvestmentTargetsMap;
  classes: InvestmentTargetClass[];
  perfil: string;
  ultimo_aporte: number | null;
  sum_pct: number;
  valid: boolean;
};

export type InvestmentProfilePreset = {
  key: string;
  label: string;
  description: string;
  targets: InvestmentTargetsMap;
};

export type InvestmentProfilesResponse = {
  profiles: InvestmentProfilePreset[];
};

export type InvestmentAporteSuggestion = {
  id: number;
  tipo: string | null;
  asset_class: string;
  ticker: string | null;
  valor_atual: number;
  preco: number;
  nota: number | null;
  sugest_rs: number;
  sugest_un: number;
  total_apos_aporte_pct: number;
};

export type InvestmentAporteResponse = {
  patrimonio: number;
  pl_alvo: number;
  sugestoes: InvestmentAporteSuggestion[];
  troco: number;
};

export type InvestmentAporteCalculateInput = {
  aporte: number;
};

export type InvestmentAporteConfirmInput = {
  aporte?: number;
  compras: Array<{ asset_id: number; quantidade: number }>;
};

export type InvestmentQuestion = {
  id: number;
  diagram_type: string;
  criterio: string | null;
  pergunta: string;
  peso: number;
  sort_order: number;
  ativo: boolean;
};

export type InvestmentQuestionsResponse = {
  diagram_type: string;
  questions: InvestmentQuestion[];
};

export type InvestmentCountryTier = "top" | "high" | "medium" | "speculative" | "nodata";

export type InvestmentMapCountry = {
  code: string;
  name: string;
  tier: InvestmentCountryTier;
  color: string;
};

export type InvestmentCountryRating = {
  sp: string | null;
  moody: string | null;
  fitch: string | null;
};

export type InvestmentCountryCompany = {
  name: string;
  ticker: string;
  setor: string;
};

export type InvestmentCountryEtf = {
  ticker: string;
  label?: string | null;
};

export type InvestmentCountryDetail = {
  code: string;
  name: string;
  name_intl: string;
  main_index: string;
  ratings: InvestmentCountryRating;
  tier: InvestmentCountryTier;
  tier_label: string;
  color: string;
  empresas: InvestmentCountryCompany[];
  etfs: InvestmentCountryEtf[];
};

export type InvestmentQuestionInput = {
  diagram_type: string;
  criterio?: string | null;
  pergunta: string;
  peso: number;
  sort_order: number;
  ativo: boolean;
};

export type InvestmentAssetScore = {
  asset_id: number;
  diagram_type: string | null;
  pontos_positivos: number;
  pontos_negativos: number;
  peso_total: number;
  nota: number | null;
};

export type InvestmentAssetAnswer = {
  asset_id: number;
  question_id: number;
  resposta: boolean;
};

export type InvestmentAssetAnswersResponse = {
  asset_id: number;
  diagram_type: string | null;
  questions: InvestmentQuestion[];
  answers: InvestmentAssetAnswer[];
  score: InvestmentAssetScore;
};

export type InvestmentAssetAnswersInput = {
  answers: Array<{ question_id: number; resposta: boolean }>;
};

export type InvestmentClassSummary = {
  asset_class: string;
  label: string;
  count: number;
  current_value: number;
  pct: number;
};

export type InvestmentsResponse = {
  totals: {
    asset_count: number;
    current_value: number;
  };
  by_class: InvestmentClassSummary[];
  assets: InvestmentAsset[];
};

export type MaintenanceFamilyProfile = {
  [key: string]: unknown;
  receitas?: Array<{ membro?: string; valor?: number }>;
  provisoes?: Array<{
    nome?: string;
    mensal?: number;
    alvo?: number;
    periodicidade_meses?: number;
    proxima_ocorrencia?: string;
  }>;
  metas?: Array<{ nome?: string; alvo?: number; atual?: number; prazo?: string }>;
  wishlist?: Array<{
    nome?: string;
    valor_alvo?: number;
    prazo_meses?: number;
    guardado?: number;
    prioridade?: number;
  }>;
  patrimonio?: {
    investimentos_caixa?: Array<{
      local?: string;
      valor?: number;
      aporte_mensal_recorrente?: number;
    }>;
    imoveis?: Array<{
      nome?: string;
      valor_mercado?: number;
      saldo_devedor?: number;
      taxa_juros_anual?: number;
      prazo_restante_meses?: number;
      aluguel_receita?: number;
      custos?: {
        financiamento?: number;
        condominio?: number;
        iptu_lixo?: number;
        [key: string]: number | undefined;
      };
    }>;
  };
};

export type MaintenanceOverrides = {
  categorias_pt?: Record<string, string>;
  recorrencias?: Array<{ match?: string; tipo?: string; rotulo?: string }>;
};

export type MaintenanceCategoryAudit = {
  total_categories: number;
  translated: number;
  missing: Array<{ category: string; tx_count: number; total_abs: number }>;
};

export type SavingsGoalTransactionsResponse = {
  goal_id: number;
  items: Transaction[];
  saved_from_tx: number;
  linked_count: number;
};

export type SavingsGoalCandidatesResponse = TransactionPage & {
  goal_id: number;
};

export type MaintenanceClassificationIssue = {
  id: string;
  date: string;
  description: string;
  account_name?: string | null;
  category?: string | null;
  category_label?: string | null;
  amount_abs: number;
};

export type MaintenanceClassificationHealth = {
  total_transactions: number;
  tagged: number;
  untagged: number;
  bucketed: number;
  unbucketed: number;
  tag_sources: Record<"manual" | "rule" | "auto" | "none", number>;
  bucket_sources: Record<"manual" | "rule" | "auto" | "none", number>;
  missing_tag_review_count: number;
  missing_bucket_review_count: number;
  missing_tag: MaintenanceClassificationIssue[];
  missing_bucket: MaintenanceClassificationIssue[];
};

export type MaintenanceResponse = {
  family_profile: MaintenanceFamilyProfile;
  overrides: MaintenanceOverrides;
  category_audit?: MaintenanceCategoryAudit;
  classification_health?: MaintenanceClassificationHealth;
};

export type MaintenanceSystemAccountSetting = {
  id: string;
  name: string;
  institution?: string | null;
  type?: string | null;
  source?: string | null;
  include_balance: boolean;
  include_transactions: boolean;
};

export type MaintenanceSystemMovementSetting = {
  key: string;
  label: string;
  include_in_totals: boolean;
  sort_order: number;
};

export type MaintenanceSystemTotalsResponse = {
  accounts: MaintenanceSystemAccountSetting[];
  movements: MaintenanceSystemMovementSetting[];
};

export type MaintenanceSystemTotalsPayload = {
  accounts: Array<{
    account_id: string;
    include_balance: boolean;
    include_transactions: boolean;
  }>;
  movements: Array<{
    movement_type: string;
    include_in_totals: boolean;
  }>;
};

export type ScenarioSimulationRequest = {
  preco: number;
  entrada: number;
  prazo_meses: number;
  juros_aa: number;
  sobra_mensal: number;
  rendimento_aa: number;
  taxa_adm_consorcio: number;
};

export type PriceSimulation = {
  sistema: "price";
  parcela: number;
  total_parcelas: number;
  total_juros: number;
};

export type SacSimulation = {
  sistema: "sac";
  primeira_parcela: number;
  ultima_parcela: number;
  total_parcelas: number;
  total_juros: number;
};

export type ConsortiumSimulation = {
  sistema: "consorcio";
  taxa_adm_pct: number;
  parcela: number;
  total_parcelas: number;
  custo_taxa_adm: number;
};

export type CashSavingSimulation = {
  aporte_mensal: number;
  rendimento_aa: number;
  meses_para_juntar: number | null;
  anos_para_juntar: number | null;
  custo_total: number;
};

export type ScenarioSimulationResponse = {
  entrada: number;
  valor_financiado: number;
  financiar: {
    price: PriceSimulation;
    sac: SacSimulation;
    custo_total_price: number;
    custo_total_sac: number;
  };
  consorcio: ConsortiumSimulation;
  juntar_a_vista: CashSavingSimulation;
  economia_juntando_vs_price: number;
};

export type AmortizationRequest = {
  saldo: number;
  juros_aa: number;
  parcela: number;
  aporte_extra: number;
};

export type PayoffResult = {
  meses: number;
  juros_pagos: number;
};

export type AmortizationResponse = {
  saldo: number;
  parcela_atual: number;
  aporte_extra: number;
  sem_extra: PayoffResult | null;
  com_extra: PayoffResult | null;
  meses_economizados: number | null;
  juros_economizados: number | null;
};

export type AccountSyncResponse = {
  account_id: string;
  item_id: string;
  sync_scheduled: boolean;
  days: number;
  detail?: string;
};

export type AccountCredentialsResponse = {
  accessToken: string;
};

export type AccountDeleteResponse = {
  deleted: boolean;
  item_id: string;
  kept_transactions: boolean;
  accounts_disconnected: string[];
};
