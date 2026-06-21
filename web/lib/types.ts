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
  category_source?: string | null;
  source: string;
  external_id?: string | null;
  bucket_id?: number | null;
  bucket_source?: string | null;
  bucket?: Pick<Bucket, "id" | "name" | "color"> | null;
  tag_id?: number | null;
  tag?: Pick<Tag, "id" | "name" | "color"> | null;
  reference_month?: string | null;
  hidden: boolean;
  note?: string | null;
  account_name?: string | null;
  account_type?: string | null;
  signed_value: number;
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
  bucket: Pick<Bucket, "id" | "name" | "color"> | null;
  bucket_source?: string | null;
  tag: Pick<Tag, "id" | "name" | "color"> | null;
  installment: InvoiceInstallment | null;
};

export type InvoiceCategory = {
  name: string;
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

export type MaintenanceResponse = {
  family_profile: MaintenanceFamilyProfile;
  overrides: MaintenanceOverrides;
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
