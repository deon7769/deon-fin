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
