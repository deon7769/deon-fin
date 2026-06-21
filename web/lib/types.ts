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
