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
