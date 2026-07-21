import type { ApiDetailErrorShape, ApiErrorShape } from "./types";

const DEFAULT_BASE_URL = "/api";
const BASE_URL = (process.env.NEXT_PUBLIC_API_URL ?? DEFAULT_BASE_URL).replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type Query = Record<string, string | number | boolean | null | undefined>;

function normalizePath(path: string): string {
  return path.startsWith("/") ? path : `/${path}`;
}

function buildUrl(path: string, query?: Query): string {
  const suffix = normalizePath(path);
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null) {
      params.set(key, String(value));
    }
  }

  const queryString = params.toString();
  if (/^https?:\/\//.test(BASE_URL)) {
    const url = new URL(`${BASE_URL}${suffix}`);
    if (queryString) {
      url.search = queryString;
    }
    return url.toString();
  }

  return `${BASE_URL}${suffix}${queryString ? `?${queryString}` : ""}`;
}

async function parseBody(response: Response): Promise<unknown> {
  const text = await response.text();
  return text ? JSON.parse(text) : null;
}

async function apiFetch<T>(
  path: string,
  opts: { method?: string; query?: Query; body?: unknown; signal?: AbortSignal } = {},
): Promise<T> {
  const { method = "GET", query, body, signal } = opts;
  const response = await fetch(buildUrl(path, query), {
    method,
    signal,
    credentials: "include",
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  const data = await parseBody(response);
  if (!response.ok) {
    const envelope = data as (ApiErrorShape & ApiDetailErrorShape) | null;
    const detail = typeof envelope?.detail === "string" ? envelope.detail : null;
    throw new ApiError(
      envelope?.error?.code ?? "http_error",
      envelope?.error?.message ?? detail ?? `Erro ${response.status}`,
      response.status,
    );
  }

  return data as T;
}

export const api = {
  get: <T>(path: string, query?: Query, signal?: AbortSignal) =>
    apiFetch<T>(path, { query, signal }),
  post: <T>(path: string, body?: unknown) => apiFetch<T>(path, { method: "POST", body }),
  put: <T>(path: string, body?: unknown) => apiFetch<T>(path, { method: "PUT", body }),
  patch: <T>(path: string, body?: unknown) => apiFetch<T>(path, { method: "PATCH", body }),
  del: <T>(path: string) => apiFetch<T>(path, { method: "DELETE" }),
};
