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
