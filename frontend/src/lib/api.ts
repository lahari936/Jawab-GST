// Types mirror backend/app/pipeline/case.py. Money arrives as decimal strings; the UI only formats it.
export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8010";

export type Money = string;
export type TaxAmount = { igst: Money; cgst: Money; sgst: Money; cess: Money };
export type Status = "explained" | "partly_explained" | "payable" | "needs_ca";

export type Ground = {
  ground_no: number;
  category: "output_tax_r1_vs_3b" | "itc_2b_vs_3b" | "other";
  description: string;
  tax_period: string;
  officer_amount: TaxAmount;
};

export type Recon = {
  our_amount: TaxAmount;
  difference: TaxAmount;
  fy_net: TaxAmount;
  periods: ({ period: string } & TaxAmount)[];
  evidence: { text: string; amount: TaxAmount }[];
};

export type Cause = { cause: string; why: string; proof_document: string };

export type GroundState = {
  ground: Ground;
  status: Status;
  recon: Recon | null;
  payable: TaxAmount | null;
  interest: TaxAmount | null;
  payable_total: Money | null;
  interest_total: Money | null;
  analysed: boolean;
  causes: Cause[];
  confirmed: string[];
  source_ids: number[];
};

export type Issue = { kind: "number" | "citation" | "url"; value: string; start: number; end: number };

export type CaseState = {
  id: string;
  notice: {
    gstin: string; notice_ref: string; issue_date: string; reply_due_date: string;
    due_date_computed: boolean; financial_year: string; grounds: Ground[];
  };
  grounds: GroundState[];
  paid_on: string | null;
  draft: string | null;
  issues: Issue[];
};

export type Source = { id: number; ground_no: number; title: string; url: string; snippet: string };
export type CostRow = { tier: string; calls: number; input_tokens: number; output_tokens: number; cost: Money };
export type CaseView = { case: CaseState; sources: Source[]; cost: CostRow[] };

export type CaseRow = {
  id: string; gstin: string; notice_ref: string; reply_due_date: string; days_left: number;
  statuses: Status[]; has_draft: boolean; issues: number; cost: Money;
};

export async function api<T>(path: string, init?: RequestInit & { json?: unknown }): Promise<T> {
  const { json, ...rest } = init ?? {};
  const res = await fetch(`${API}${path}`, {
    ...rest,
    ...(json !== undefined && { body: JSON.stringify(json), headers: { "Content-Type": "application/json" } }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `${res.status} ${res.statusText}`);
  }
  return res.json();
}

export const HEADS = ["igst", "cgst", "sgst", "cess"] as const;

export const inr = (v: Money | number | null | undefined) =>
  v == null ? "—" : `${Number(v) < 0 ? "−" : ""}₹${Math.abs(Number(v)).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;

/** "CGST ₹6,000 · SGST ₹6,000"; zero heads hidden. */
export const heads = (a: TaxAmount | null | undefined) => {
  if (!a) return "—";
  const parts = HEADS.filter((h) => Number(a[h]) !== 0).map((h) => `${h.toUpperCase()} ${inr(a[h])}`);
  return parts.length ? parts.join(" · ") : "₹0";
};
