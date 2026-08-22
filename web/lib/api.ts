const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export type Metrics = {
  at_risk_paise: number;
  recovered_paise: number;
  recovery_rate: number;
  recommended_count: number;
  escalated_count: number;
  stopped_count: number;
  queued_count: number;
  policy_violations: number;
  case_count: number;
  degraded: boolean;
};

export type Audit = {
  ts: string;
  actor: string;
  event_type: string;
  severity: string;
  payload: Record<string, unknown>;
};

export type CaseRow = {
  id: string;
  run_id: string;
  event_id: string;
  payment_id: string | null;
  order_id: string | null;
  source_event: string;
  amount_paise: number;
  method: string | null;
  diagnosis_class: string | null;
  diagnosis_rationale: string | null;
  diagnosis_source: string | null;
  action: string | null;
  channel: string | null;
  outcome: string | null;
  recovered_paise: number;
  bucket: string | null;
  degraded: boolean;
  message_en?: string | null;
  message_hinglish?: string | null;
  policy_reasons: string[];
  audit: Audit[];
};

export type RunOut = {
  id: string;
  created_at: string;
  policy_mode: string;
  locale: string;
  status: string;
  metrics: Metrics;
  llm_mode: string;
  case_ids: string[];
  cases: CaseRow[] | null;
};

export type Faults = { llm: "up" | "down"; whatsapp: "ok" | "timeout" };

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) {
    throw new Error(`${res.status} ${await res.text()}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => req<{ ok: boolean; llm: string; faults: Faults }>("/health"),
  run: (policy_mode: string, locale: string) =>
    req<RunOut>("/api/v1/runs", {
      method: "POST",
      body: JSON.stringify({ source: "sample_batch", policy_mode, locale }),
    }),
  getRun: (id: string) => req<RunOut>(`/api/v1/runs/${id}`),
  getCase: (id: string) => req<CaseRow>(`/api/v1/cases/${id}`),
  metrics: () => req<Metrics>("/api/v1/metrics"),
  getFaults: () => req<Faults>("/api/v1/demo/faults"),
  setFaults: (body: Partial<Faults>) =>
    req<Faults>("/api/v1/demo/faults", { method: "POST", body: JSON.stringify(body) }),
};

export function inr(paise: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(paise / 100);
}
