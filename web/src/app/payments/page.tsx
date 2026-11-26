"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import {
  apiFetch,
  ApiError,
  type InvoiceListItem,
  type Payment,
} from "@/lib/api";

export default function PaymentsPage() {
  const [payments, setPayments] = useState<Payment[]>([]);
  const [payable, setPayable] = useState<InvoiceListItem[]>([]);
  const [invoiceId, setInvoiceId] = useState("");
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState("ach");
  const [reference, setReference] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [payRes, approved, partial] = await Promise.all([
        apiFetch<{ items: Payment[] }>("/api/v1/payments?page_size=50"),
        apiFetch<{ items: InvoiceListItem[] }>(
          "/api/v1/invoices?status=approved&page_size=50"
        ),
        apiFetch<{ items: InvoiceListItem[] }>(
          "/api/v1/invoices?status=partially_paid&page_size=50"
        ),
      ]);
      setPayments(payRes.items);
      const list = [...approved.items, ...partial.items];
      setPayable(list);
      if (!invoiceId && list[0]) {
        setInvoiceId(list[0].id);
        setAmount(list[0].balance_due);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load payments");
    }
  }, [invoiceId]);

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await apiFetch<Payment>("/api/v1/payments", {
        method: "POST",
        body: JSON.stringify({
          invoice_id: invoiceId,
          amount,
          payment_date: new Date().toISOString().slice(0, 10),
          method,
          reference: reference || null,
        }),
      });
      setReference("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Payment failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <header>
          <h1 className="font-display text-3xl text-ink">Payments</h1>
          <p className="mt-1 text-sm text-slate">
            Record partial or full payments against approved invoices.
          </p>
        </header>

        {error && (
          <p className="rounded-md border border-warn/30 bg-warn/10 px-3 py-2 text-sm text-warn">
            {error}
          </p>
        )}

        <form
          onSubmit={onSubmit}
          className="grid gap-3 rounded-lg border border-slate/15 bg-white/80 p-4 sm:grid-cols-2"
        >
          <label className="text-sm text-slate sm:col-span-2">
            Invoice
            <select
              required
              value={invoiceId}
              onChange={(e) => {
                const id = e.target.value;
                setInvoiceId(id);
                const found = payable.find((p) => p.id === id);
                if (found) setAmount(found.balance_due);
              }}
              className="mt-1 w-full rounded-md border border-slate/20 bg-paper px-3 py-2 text-ink"
            >
              {payable.length === 0 && (
                <option value="">No payable invoices</option>
              )}
              {payable.map((inv) => (
                <option key={inv.id} value={inv.id}>
                  {inv.invoice_number} — bal {inv.balance_due} ({inv.status})
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm text-slate">
            Amount
            <input
              required
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate/20 bg-paper px-3 py-2 text-ink"
            />
          </label>
          <label className="text-sm text-slate">
            Method
            <select
              value={method}
              onChange={(e) => setMethod(e.target.value)}
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
              value={reference}
              onChange={(e) => setReference(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate/20 bg-paper px-3 py-2 text-ink"
            />
          </label>
          <button
            type="submit"
            disabled={busy || !invoiceId}
            className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {busy ? "Recording…" : "Record payment"}
          </button>
        </form>

        <div className="overflow-x-auto rounded-lg border border-slate/15 bg-white/80">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-slate/10 text-xs uppercase text-slate">
              <tr>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Invoice</th>
                <th className="px-4 py-3">Amount</th>
                <th className="px-4 py-3">Method</th>
                <th className="px-4 py-3">Resulting status</th>
              </tr>
            </thead>
            <tbody>
              {payments.map((p) => (
                <tr key={p.id} className="border-b border-slate/5 last:border-0">
                  <td className="px-4 py-3">{p.payment_date}</td>
                  <td className="px-4 py-3">
                    <Link
                      href={`/invoices/${p.invoice_id}`}
                      className="text-accent hover:underline"
                    >
                      {p.invoice_id.slice(0, 8)}…
                    </Link>
                  </td>
                  <td className="px-4 py-3">{p.amount}</td>
                  <td className="px-4 py-3">{p.method}</td>
                  <td className="px-4 py-3">
                    {p.invoice_status || "—"}
                    {p.invoice_balance_due
                      ? ` · bal ${p.invoice_balance_due}`
                      : ""}
                  </td>
                </tr>
              ))}
              {payments.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-slate">
                    No payments recorded yet in this session list.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </AppShell>
  );
}
