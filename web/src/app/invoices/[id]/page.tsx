"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import {
  apiFetch,
  ApiError,
  type AIResponse,
  type AnomalySignal,
  type InvoiceDetail,
  type Payment,
  type PoCandidatesResponse,
} from "@/lib/api";

export default function InvoiceDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [inv, setInv] = useState<InvoiceDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [rejectComment, setRejectComment] = useState("");
  const [payAmount, setPayAmount] = useState("");
  const [payMethod, setPayMethod] = useState("ach");
  const [payRef, setPayRef] = useState("");
  const [radarSignals, setRadarSignals] = useState<AnomalySignal[]>([]);
  const [radarExplanation, setRadarExplanation] = useState<string | null>(null);
  const [categoryNote, setCategoryNote] = useState<string | null>(null);
  const [categoryId, setCategoryId] = useState<string | null>(null);
  const [categoryConfirmed, setCategoryConfirmed] = useState(false);
  const [categorySaved, setCategorySaved] = useState(false);
  const [poData, setPoData] = useState<PoCandidatesResponse | null>(null);
  const [poConfirmId, setPoConfirmId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await apiFetch<InvoiceDetail>(`/api/v1/invoices/${id}`);
      setInv(data);
      setPayAmount(data.balance_due);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load invoice");
    }
  }, [id]);

  const loadPoCandidates = useCallback(async () => {
    try {
      const data = await apiFetch<PoCandidatesResponse>(
        `/api/v1/invoices/${id}/po-candidates`
      );
      setPoData(data);
      setPoConfirmId(null);
    } catch {
      setPoData(null);
    }
  }, [id]);

  const loadAssist = useCallback(async () => {
    try {
      const radar = await apiFetch<AIResponse>("/api/v1/ai/invoice-anomalies", {
        method: "POST",
        body: JSON.stringify({
          input: { invoice_id: id },
          context_ids: [id],
          options: {},
        }),
      });
      setRadarSignals((radar.result.signals as AnomalySignal[]) || []);
      setRadarExplanation(radar.explanation);

      const cat = await apiFetch<AIResponse>("/api/v1/ai/category-suggestion", {
        method: "POST",
        body: JSON.stringify({
          input: { invoice_id: id },
          context_ids: [id],
          options: {},
        }),
      });
      const suggested = cat.result.suggested_category as
        | { id?: string; code?: string; name?: string }
        | null
        | undefined;
      setCategoryId(suggested?.id || null);
      setCategoryNote(
        suggested
          ? `Suggested: ${suggested.code} — ${suggested.name}. ${cat.explanation}`
          : cat.explanation
      );
      setCategoryConfirmed(false);
      setCategorySaved(false);
    } catch {
      // Assist panels are optional; invoice detail still works
    }
  }, [id]);

  async function persistCategory() {
    if (!categoryId || !categoryConfirmed) return;
    setBusy(true);
    setError(null);
    try {
      const data = await apiFetch<InvoiceDetail>(
        `/api/v1/invoices/${id}/category`,
        {
          method: "PATCH",
          body: JSON.stringify({
            accounting_category_id: categoryId,
            confirmed: true,
          }),
        }
      );
      setInv(data);
      setCategorySaved(true);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Category save failed");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    void loadAssist();
  }, [loadAssist]);

  useEffect(() => {
    void loadPoCandidates();
  }, [loadPoCandidates]);

  async function confirmPoMatch(poId: string) {
    if (poConfirmId !== poId) return;
    setBusy(true);
    setError(null);
    try {
      const data = await apiFetch<InvoiceDetail>(
        `/api/v1/invoices/${id}/po-match`,
        {
          method: "POST",
          body: JSON.stringify({
            purchase_order_reference_id: poId,
            confirmed: true,
          }),
        }
      );
      setInv(data);
      setPoConfirmId(null);
      await loadPoCandidates();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "PO match confirm failed");
    } finally {
      setBusy(false);
    }
  }

  async function workflow(action: "submit_review" | "submit_approval") {
    setBusy(true);
    setError(null);
    try {
      const data = await apiFetch<InvoiceDetail>(
        `/api/v1/invoices/${id}/workflow`,
        {
          method: "POST",
          body: JSON.stringify({ action }),
        }
      );
      setInv(data);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Workflow failed");
    } finally {
      setBusy(false);
    }
  }

  async function decide(decision: "approved" | "rejected") {
    setBusy(true);
    setError(null);
    try {
      await apiFetch(`/api/v1/approvals?invoice_id=${id}`, {
        method: "POST",
        body: JSON.stringify({
          decision,
          comment: decision === "rejected" ? rejectComment : "Approved",
        }),
      });
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Approval failed");
    } finally {
      setBusy(false);
    }
  }

  async function recordPayment(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await apiFetch<Payment>("/api/v1/payments", {
        method: "POST",
        body: JSON.stringify({
          invoice_id: id,
          amount: payAmount,
          payment_date: new Date().toISOString().slice(0, 10),
          method: payMethod,
          reference: payRef || null,
        }),
      });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Payment failed");
    } finally {
      setBusy(false);
    }
  }

  if (!inv && !error) {
    return (
      <AppShell>
        <p className="text-slate">Loading invoice…</p>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <header>
          <p className="text-sm text-slate">
            <Link href="/invoices" className="text-accent hover:underline">
              Invoices
            </Link>{" "}
            / {inv?.invoice_number || id}
          </p>
          {inv && (
            <>
              <h1 className="mt-1 font-display text-3xl text-ink">
                {inv.invoice_number}
              </h1>
              <p className="mt-1 text-sm text-slate">
                Status{" "}
                <span className="rounded bg-mist px-2 py-0.5 text-xs">
                  {inv.status}
                </span>
                {" · "}
                {inv.currency} {inv.total} · balance {inv.balance_due}
              </p>
            </>
          )}
        </header>

        {error && (
          <p className="rounded-md border border-warn/30 bg-warn/10 px-3 py-2 text-sm text-warn">
            {error}
          </p>
        )}

        {inv && (
          <>
            {(inv.has_duplicate_warning ||
              inv.validation_issues.length > 0) && (
              <div className="rounded-lg border border-warn/25 bg-warn/5 px-4 py-3 text-sm text-warn">
                <p className="font-medium">Review signals</p>
                <ul className="mt-1 list-inside list-disc">
                  {inv.has_duplicate_warning && (
                    <li>Duplicate supplier + invoice number</li>
                  )}
                  {inv.validation_issues.map((issue) => (
                    <li key={issue}>{issue}</li>
                  ))}
                </ul>
              </div>
            )}

            <section className="space-y-3 rounded-lg border border-slate/15 bg-white/80 p-4">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h2 className="font-medium text-ink">Anomaly Radar</h2>
                <Link
                  href="/anomaly-radar"
                  className="text-xs text-accent hover:underline"
                >
                  Open radar
                </Link>
              </div>
              <p className="text-xs text-slate">
                Rules-first review hints. Never a fraud verdict.
              </p>
              {radarExplanation && (
                <p className="text-sm text-slate">{radarExplanation}</p>
              )}
              {radarSignals.length === 0 ? (
                <p className="text-sm text-slate">No radar signals for this invoice.</p>
              ) : (
                <ul className="space-y-2">
                  {radarSignals.map((s) => (
                    <li
                      key={s.code + s.message}
                      className="rounded-md border border-slate/10 bg-mist/40 px-3 py-2 text-sm"
                    >
                      <span className="font-medium text-ink">{s.code}</span>
                      <span className="ml-2 text-xs text-accent">
                        not fraud
                      </span>
                      <p className="mt-1 text-slate">{s.message}</p>
                      {s.explanation && (
                        <p className="mt-1 text-xs text-slate">{s.explanation}</p>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </section>

            {categoryNote && (
              <section className="space-y-2 rounded-lg border border-slate/15 bg-white/80 p-4">
                <h2 className="font-medium text-ink">Category suggestion</h2>
                <p className="text-sm text-slate">{categoryNote}</p>
                {inv.accounting_category_code && (
                  <p className="text-xs text-accent">
                    Saved category: {inv.accounting_category_code} —{" "}
                    {inv.accounting_category_name}
                  </p>
                )}
                <label className="flex items-start gap-2 text-sm text-ink">
                  <input
                    type="checkbox"
                    checked={categoryConfirmed}
                    onChange={(e) => setCategoryConfirmed(e.target.checked)}
                    className="mt-1"
                    disabled={!categoryId}
                  />
                  <span>
                    I confirm this category (AI does not write it — you must
                    save after checking).
                  </span>
                </label>
                <button
                  type="button"
                  disabled={busy || !categoryConfirmed || !categoryId}
                  onClick={() => void persistCategory()}
                  className="rounded-md bg-accent px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"
                >
                  Save confirmed category
                </button>
                {categorySaved && (
                  <p className="text-xs text-accent">
                    Category persisted on the invoice via PATCH.
                  </p>
                )}
              </section>
            )}

            {inv.documents && inv.documents.length > 0 && (
              <section className="space-y-3 rounded-lg border border-slate/15 bg-white/80 p-4">
                <h2 className="font-medium text-ink">Document preview</h2>
                <p className="text-xs text-slate">
                  Metadata only — no paid OCR; pasted text previews when present.
                </p>
                <ul className="space-y-3">
                  {inv.documents.map((doc) => (
                    <li
                      key={doc.id}
                      className="rounded-md border border-slate/10 bg-mist/30 px-3 py-2 text-sm"
                    >
                      <p className="font-medium text-ink">{doc.filename}</p>
                      <p className="mt-1 text-xs text-slate">
                        {doc.content_type} · {doc.byte_size} bytes ·{" "}
                        {doc.storage_path}
                        {doc.created_at ? ` · ${doc.created_at}` : ""}
                      </p>
                      {doc.has_ocr_text ? (
                        <p className="mt-2 whitespace-pre-wrap text-xs text-slate">
                          OCR preview ({doc.ocr_char_count} chars):{" "}
                          {doc.ocr_text_preview || "—"}
                        </p>
                      ) : (
                        <p className="mt-2 text-xs text-slate">
                          No OCR text attached.
                        </p>
                      )}
                    </li>
                  ))}
                </ul>
              </section>
            )}

            <section className="space-y-3 rounded-lg border border-slate/15 bg-white/80 p-4">
              <h2 className="font-medium text-ink">PO match</h2>
              <p className="text-xs text-slate">
                Candidates with differences only — never auto-linked. Reviewer
                or admin must confirm.
              </p>
              <p className="text-sm text-slate">
                Invoice PO ref: {inv.po_reference || "—"}
                {inv.matched_po_number
                  ? ` · Matched: ${inv.matched_po_number}`
                  : " · Not confirmed"}
              </p>
              {poData && poData.candidates.length === 0 && (
                <p className="text-sm text-slate">No PO candidates ranked.</p>
              )}
              {poData?.candidates.map((c) => (
                <div
                  key={c.id}
                  className="rounded-md border border-slate/10 bg-mist/30 px-3 py-2 text-sm"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="font-medium text-ink">
                      {c.po_number}{" "}
                      <span className="text-xs font-normal text-slate">
                        score {c.score}
                      </span>
                    </p>
                    <div className="flex items-center gap-2">
                      <label className="flex items-center gap-1 text-xs text-ink">
                        <input
                          type="checkbox"
                          checked={poConfirmId === c.id}
                          onChange={(e) =>
                            setPoConfirmId(e.target.checked ? c.id : null)
                          }
                        />
                        Confirm
                      </label>
                      <button
                        type="button"
                        disabled={busy || poConfirmId !== c.id}
                        onClick={() => void confirmPoMatch(c.id)}
                        className="rounded-md bg-accent px-2 py-1 text-xs font-medium text-white disabled:opacity-50"
                      >
                        Link PO
                      </button>
                    </div>
                  </div>
                  {c.differences && c.differences.length > 0 && (
                    <ul className="mt-2 space-y-1 text-xs text-slate">
                      {c.differences.map((d) => (
                        <li key={d.field}>
                          {d.field}: invoice {d.invoice_value ?? "—"} vs PO{" "}
                          {d.po_value ?? "—"}{" "}
                          {d.match ? "(match)" : "(mismatch)"}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </section>

            <section className="grid gap-4 rounded-lg border border-slate/15 bg-white/80 p-4 sm:grid-cols-3">
              <div>
                <p className="text-xs uppercase text-slate">Invoice date</p>
                <p className="font-medium">{inv.invoice_date}</p>
              </div>
              <div>
                <p className="text-xs uppercase text-slate">Due date</p>
                <p className="font-medium">{inv.due_date || "—"}</p>
              </div>
              <div>
                <p className="text-xs uppercase text-slate">Paid / balance</p>
                <p className="font-medium">
                  {inv.amount_paid} / {inv.balance_due}
                </p>
              </div>
              <div>
                <p className="text-xs uppercase text-slate">Subtotal</p>
                <p className="font-medium">{inv.subtotal}</p>
              </div>
              <div>
                <p className="text-xs uppercase text-slate">Tax</p>
                <p className="font-medium">{inv.tax_total}</p>
              </div>
              <div>
                <p className="text-xs uppercase text-slate">Total</p>
                <p className="font-medium">{inv.total}</p>
              </div>
            </section>

            <section className="overflow-x-auto rounded-lg border border-slate/15 bg-white/80">
              <table className="min-w-full text-left text-sm">
                <thead className="border-b border-slate/10 text-xs uppercase text-slate">
                  <tr>
                    <th className="px-4 py-3">#</th>
                    <th className="px-4 py-3">Description</th>
                    <th className="px-4 py-3">Qty</th>
                    <th className="px-4 py-3">Unit</th>
                    <th className="px-4 py-3">Tax</th>
                    <th className="px-4 py-3">Line total</th>
                  </tr>
                </thead>
                <tbody>
                  {inv.lines.map((ln) => (
                    <tr
                      key={ln.id}
                      className="border-b border-slate/5 last:border-0"
                    >
                      <td className="px-4 py-2">{ln.line_number}</td>
                      <td className="px-4 py-2">{ln.description}</td>
                      <td className="px-4 py-2">{ln.quantity}</td>
                      <td className="px-4 py-2">{ln.unit_price}</td>
                      <td className="px-4 py-2">{ln.tax_rate}</td>
                      <td className="px-4 py-2">{ln.line_total}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>

            <section className="flex flex-wrap gap-2">
              {(inv.status === "uploaded" || inv.status === "rejected") && (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void workflow("submit_review")}
                  className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
                >
                  Submit for review
                </button>
              )}
              {(inv.status === "needs_review" || inv.status === "uploaded") && (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void workflow("submit_approval")}
                  className="rounded-md border border-accent px-4 py-2 text-sm font-medium text-accent disabled:opacity-50"
                >
                  Submit for approval
                </button>
              )}
            </section>

            {inv.status === "pending_approval" && (
              <section className="space-y-3 rounded-lg border border-slate/15 bg-white/80 p-4">
                <h2 className="font-medium text-ink">Approval decision</h2>
                <p className="text-xs text-slate">
                  Approver or admin role required. Decisions are audited.
                </p>
                <label className="block text-sm text-slate">
                  Rejection reason
                  <input
                    value={rejectComment}
                    onChange={(e) => setRejectComment(e.target.value)}
                    className="mt-1 w-full rounded-md border border-slate/20 bg-paper px-3 py-2 text-ink"
                    placeholder="Required when rejecting"
                  />
                </label>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void decide("approved")}
                    className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
                  >
                    Approve
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void decide("rejected")}
                    className="rounded-md border border-warn px-4 py-2 text-sm font-medium text-warn disabled:opacity-50"
                  >
                    Reject
                  </button>
                </div>
              </section>
            )}

            {(inv.status === "approved" ||
              inv.status === "partially_paid") && (
              <section className="rounded-lg border border-slate/15 bg-white/80 p-4">
                <h2 className="font-medium text-ink">Record payment</h2>
                <p className="mt-1 text-xs text-slate">
                  Approver or admin. Partial payments update balance.
                </p>
                <form
                  onSubmit={recordPayment}
                  className="mt-3 grid gap-3 sm:grid-cols-4"
                >
                  <label className="text-sm text-slate">
                    Amount
                    <input
                      required
                      value={payAmount}
                      onChange={(e) => setPayAmount(e.target.value)}
                      className="mt-1 w-full rounded-md border border-slate/20 bg-paper px-3 py-2 text-ink"
                    />
                  </label>
                  <label className="text-sm text-slate">
                    Method
                    <select
                      value={payMethod}
                      onChange={(e) => setPayMethod(e.target.value)}
                      className="mt-1 w-full rounded-md border border-slate/20 bg-paper px-3 py-2 text-ink"
                    >
                      <option value="ach">ACH</option>
                      <option value="wire">Wire</option>
                      <option value="check">Check</option>
                      <option value="card">Card</option>
                      <option value="other">Other</option>
                    </select>
                  </label>
                  <label className="text-sm text-slate sm:col-span-2">
                    Reference
                    <input
                      value={payRef}
                      onChange={(e) => setPayRef(e.target.value)}
                      className="mt-1 w-full rounded-md border border-slate/20 bg-paper px-3 py-2 text-ink"
                    />
                  </label>
                  <button
                    type="submit"
                    disabled={busy}
                    className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white disabled:opacity-50 sm:col-span-4 sm:w-fit"
                  >
                    Record payment
                  </button>
                </form>
              </section>
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}
