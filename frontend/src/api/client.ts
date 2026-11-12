import type { components } from "./schema";

export type MoneySignals = components["schemas"]["MoneySignals"];
export type SeriesResponse = components["schemas"]["SeriesResponse"];
export type PoliciesResponse = components["schemas"]["PoliciesResponse"];
export type PolicyItem = components["schemas"]["PolicyItem"];
export type SignalVariant = components["schemas"]["SignalVariant"];
export type ProbabilityBlock = components["schemas"]["ProbabilityBlock"];
export type EvidenceBlock = components["schemas"]["EvidenceBlock"];
export type ComparisonBlock = components["schemas"]["ComparisonBlock"];
export type BenchmarkBlock = components["schemas"]["BenchmarkBlock"];
export type SpreadSeries = components["schemas"]["SpreadSeries"];
export type RatesPoint = components["schemas"]["RatesPoint"];

/** Тело ошибки в формате problem+json. */
export type Problem = {
  type?: string;
  title?: string;
  status?: number;
  detail?: string;
};

export class ApiError extends Error {
  readonly status: number;
  readonly problem: Problem;

  constructor(status: number, problem: Problem) {
    super(problem.detail ?? problem.title ?? `HTTP ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.problem = problem;
  }
}

export type PolicyParams = {
  p_borrow_now?: number;
  p_wait?: number;
  preset?: string;
};

export type SeriesParams = {
  from: string;
  to: string;
  bucket: "day" | "week" | "month";
};

async function request<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, { signal });
  if (!response.ok) {
    let problem: Problem = {};
    try {
      problem = (await response.json()) as Problem;
    } catch {
      problem = { detail: response.statusText };
    }
    throw new ApiError(response.status, problem);
  }
  return (await response.json()) as T;
}

function toQuery(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) {
      search.set(key, String(value));
    }
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

export const api = {
  signals(policy: PolicyParams, signal?: AbortSignal): Promise<MoneySignals> {
    const query = toQuery({
      p_borrow_now: policy.p_borrow_now,
      p_wait: policy.p_wait,
      preset: policy.preset,
    });
    return request<MoneySignals>(`/api/v1/money/signals${query}`, signal);
  },

  series(params: SeriesParams, signal?: AbortSignal): Promise<SeriesResponse> {
    const query = toQuery({ from: params.from, to: params.to, bucket: params.bucket });
    return request<SeriesResponse>(`/api/v1/money/series${query}`, signal);
  },

  policies(signal?: AbortSignal): Promise<PoliciesResponse> {
    return request<PoliciesResponse>("/api/v1/money/policies", signal);
  },
};
