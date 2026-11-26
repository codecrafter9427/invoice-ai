import { getDemoToken } from "@/lib/auth";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
  "http://localhost:8004";

export class ApiError extends Error {
  code: string;
  status: number;
  details: unknown;

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

async function parseError(res: Response): Promise<never> {
  const data = await res.json().catch(() => null);
  const err = data?.error || data?.detail?.error;
  throw new ApiError(
    res.status,
    err?.code || "error",
    err?.message || `Request failed (${res.status})`,
    err?.details
  );
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getDemoToken();
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    await parseError(res);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json() as Promise<T>;
}

export async function demoLogin(
  email: string,
  password: string
): Promise<{ access_token: string; email: string; role: string }> {
  const res = await fetch(`${API_BASE}/api/v1/auth/demo-login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    await parseError(res);
  }
  return res.json();
}

export type Supplier = {
  id: string;
  code: string;
  name: string;
  email: string | null;
  phone: string | null;
  payment_details: string | null;
  is_active: boolean;
  organization_id: string;
};

export type InvoiceListItem = {
  id: string;
  invoice_number: string;
  supplier_id: string;
  supplier_name?: string | null;
  status: string;
  invoice_date?: string | null;
  total: string;
  balance_due: string;
  currency: string;
  has_duplicate_warning: boolean;
  has_anomaly_signal: boolean;
  organization_id: string;
};

export type InvoiceLine = {
  id: string;
  line_number: number;
  description: string;
  quantity: string;
  unit_price: string;
  tax_rate: string;
  line_total: string;
};

export type InvoiceDetail = {
  id: string;
  supplier_id: string;
  invoice_number: string;
  invoice_date: string;
  due_date: string | null;
  currency: string;
  subtotal: string;
  tax_total: string;
  total: string;
  amount_paid: string;
  balance_due: string;
  po_reference: string | null;
  terms: string | null;
  status: string;
  has_duplicate_warning: boolean;
  has_anomaly_signal: boolean;
  anomaly_notes: string | null;
  lines: InvoiceLine[];
  validation_issues: string[];
};

export type Payment = {
  id: string;
  invoice_id: string;
  amount: string;
  payment_date: string;
  method: string;
  reference: string | null;
  invoice_status?: string | null;
  invoice_balance_due?: string | null;
  invoice_amount_paid?: string | null;
};

export type AISource = { type: string; id: string; label: string };

export type AIResponse = {
  result: Record<string, unknown>;
  explanation: string;
  sources: AISource[];
  requires_confirmation: boolean;
};

export type AnomalySignal = {
  code: string;
  severity: string;
  message: string;
  explanation?: string;
  evidence?: Record<string, unknown>;
  is_fraud_verdict: boolean;
};

export type ExtractResult = {
  header?: Record<string, string>;
  line_items?: Array<{
    description: string;
    quantity: string;
    unit_price: string;
    tax_rate: string;
    confidence?: number;
  }>;
  field_confidence?: Record<string, number>;
  ocr_verified?: boolean;
  requires_user_review?: boolean;
  validation_issues?: string[];
  validation_explanations?: Array<{ code: string; explanation: string }>;
  po_candidates?: Array<{
    id: string;
    po_number: string;
    score: number;
    match_type?: string;
    note?: string;
  }>;
  provider?: string;
  note?: string;
};

export { API_BASE };
