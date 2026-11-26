"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { apiFetch, ApiError, type InvoiceDetail, type Supplier } from "@/lib/api";

type LineDraft = {
  description: string;
  quantity: string;
  unit_price: string;
  tax_rate: string;
};

function money(n: number): string {
  return (Math.round(n * 100) / 100).toFixed(2);
}

export default function NewInvoicePage() {
  const router = useRouter();
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [supplierId, setSupplierId] = useState("");
  const [invoiceNumber, setInvoiceNumber] = useState("");
  const [invoiceDate, setInvoiceDate] = useState(
    new Date().toISOString().slice(0, 10)
  );
  const [dueDate, setDueDate] = useState("");
  const [submitForReview, setSubmitForReview] = useState(false);
  const [lines, setLines] = useState<LineDraft[]>([
    { description: "", quantity: "1", unit_price: "0", tax_rate: "0" },
  ]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void apiFetch<{ items: Supplier[] }>("/api/v1/suppliers?page_size=100")
      .then((data) => {
        setSuppliers(data.items);
        if (data.items[0]) setSupplierId(data.items[0].id);
      })
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Failed to load suppliers")
      );
  }, []);

  const preview = useMemo(() => {
    let subtotal = 0;
    let tax = 0;
    for (const ln of lines) {
      const base = Number(ln.quantity || 0) * Number(ln.unit_price || 0);
      const lineTax = base * Number(ln.tax_rate || 0);
      subtotal += base;
      tax += lineTax;
    }
    return {
      subtotal: money(subtotal),
      tax_total: money(tax),
      total: money(subtotal + tax),
    };
  }, [lines]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const created = await apiFetch<InvoiceDetail>("/api/v1/invoices", {
        method: "POST",
        body: JSON.stringify({
          supplier_id: supplierId,
          invoice_number: invoiceNumber.trim(),
          invoice_date: invoiceDate,
          due_date: dueDate || null,
          currency: "USD",
          submit_for_review: submitForReview,
          lines: lines.map((ln) => ({
            description: ln.description.trim(),
            quantity: ln.quantity,
            unit_price: ln.unit_price,
            tax_rate: ln.tax_rate,
          })),
          subtotal: preview.subtotal,
          tax_total: preview.tax_total,
          total: preview.total,
        }),
      });
      router.push(`/invoices/${created.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <header>
          <p className="text-sm text-slate">
            <Link href="/invoices" className="text-accent hover:underline">
              Invoices
            </Link>{" "}
            / New
          </p>
          <h1 className="mt-1 font-display text-3xl text-ink">
            Manual invoice entry
          </h1>
          <p className="mt-1 text-sm text-slate">
            Totals are calculated from line items (subtotal + tax).
          </p>
        </header>

        {error && (
          <p className="rounded-md border border-warn/30 bg-warn/10 px-3 py-2 text-sm text-warn">
            {error}
          </p>
        )}

        <form onSubmit={onSubmit} className="space-y-6">
          <div className="grid gap-3 rounded-lg border border-slate/15 bg-white/80 p-4 sm:grid-cols-2">
            <label className="text-sm text-slate">
              Supplier
              <select
                required
                value={supplierId}
                onChange={(e) => setSupplierId(e.target.value)}
                className="mt-1 w-full rounded-md border border-slate/20 bg-paper px-3 py-2 text-ink"
              >
                {suppliers.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.code} — {s.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm text-slate">
              Invoice number
              <input
                required
                value={invoiceNumber}
                onChange={(e) => setInvoiceNumber(e.target.value)}
                className="mt-1 w-full rounded-md border border-slate/20 bg-paper px-3 py-2 text-ink"
              />
            </label>
            <label className="text-sm text-slate">
              Invoice date
              <input
                type="date"
                required
                value={invoiceDate}
                onChange={(e) => setInvoiceDate(e.target.value)}
                className="mt-1 w-full rounded-md border border-slate/20 bg-paper px-3 py-2 text-ink"
              />
            </label>
            <label className="text-sm text-slate">
              Due date
              <input
                type="date"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                className="mt-1 w-full rounded-md border border-slate/20 bg-paper px-3 py-2 text-ink"
              />
            </label>
          </div>

          <div className="space-y-3 rounded-lg border border-slate/15 bg-white/80 p-4">
            <div className="flex items-center justify-between">
              <h2 className="font-medium text-ink">Line items</h2>
              <button
                type="button"
                className="text-sm text-accent hover:underline"
                onClick={() =>
                  setLines((prev) => [
                    ...prev,
                    {
                      description: "",
                      quantity: "1",
                      unit_price: "0",
                      tax_rate: "0",
                    },
                  ])
                }
              >
                Add line
              </button>
            </div>
            {lines.map((ln, idx) => (
              <div
                key={idx}
                className="grid gap-2 border-t border-slate/10 pt-3 sm:grid-cols-12"
              >
                <label className="text-xs text-slate sm:col-span-5">
                  Description
                  <input
                    required
                    value={ln.description}
                    onChange={(e) => {
                      const v = e.target.value;
                      setLines((prev) =>
                        prev.map((p, i) =>
                          i === idx ? { ...p, description: v } : p
                        )
                      );
                    }}
                    className="mt-1 w-full rounded-md border border-slate/20 bg-paper px-2 py-1.5 text-sm text-ink"
                  />
                </label>
                <label className="text-xs text-slate sm:col-span-2">
                  Qty
                  <input
                    required
                    value={ln.quantity}
                    onChange={(e) => {
                      const v = e.target.value;
                      setLines((prev) =>
                        prev.map((p, i) =>
                          i === idx ? { ...p, quantity: v } : p
                        )
                      );
                    }}
                    className="mt-1 w-full rounded-md border border-slate/20 bg-paper px-2 py-1.5 text-sm text-ink"
                  />
                </label>
                <label className="text-xs text-slate sm:col-span-2">
                  Unit price
                  <input
                    required
                    value={ln.unit_price}
                    onChange={(e) => {
                      const v = e.target.value;
                      setLines((prev) =>
                        prev.map((p, i) =>
                          i === idx ? { ...p, unit_price: v } : p
                        )
                      );
                    }}
                    className="mt-1 w-full rounded-md border border-slate/20 bg-paper px-2 py-1.5 text-sm text-ink"
                  />
                </label>
                <label className="text-xs text-slate sm:col-span-2">
                  Tax rate
                  <input
                    value={ln.tax_rate}
                    onChange={(e) => {
                      const v = e.target.value;
                      setLines((prev) =>
                        prev.map((p, i) =>
                          i === idx ? { ...p, tax_rate: v } : p
                        )
                      );
                    }}
                    className="mt-1 w-full rounded-md border border-slate/20 bg-paper px-2 py-1.5 text-sm text-ink"
                  />
                </label>
                <div className="flex items-end sm:col-span-1">
                  {lines.length > 1 && (
                    <button
                      type="button"
                      className="mb-1 text-xs text-warn"
                      onClick={() =>
                        setLines((prev) => prev.filter((_, i) => i !== idx))
                      }
                    >
                      Remove
                    </button>
                  )}
                </div>
              </div>
            ))}
            <dl className="mt-4 grid grid-cols-3 gap-2 border-t border-slate/10 pt-3 text-sm">
              <div>
                <dt className="text-slate">Subtotal</dt>
                <dd className="font-medium">{preview.subtotal}</dd>
              </div>
              <div>
                <dt className="text-slate">Tax</dt>
                <dd className="font-medium">{preview.tax_total}</dd>
              </div>
              <div>
                <dt className="text-slate">Total</dt>
                <dd className="font-medium">{preview.total}</dd>
              </div>
            </dl>
          </div>

          <label className="flex items-center gap-2 text-sm text-slate">
            <input
              type="checkbox"
              checked={submitForReview}
              onChange={(e) => setSubmitForReview(e.target.checked)}
            />
            Submit for review immediately (status → needs_review)
          </label>

          <button
            type="submit"
            disabled={busy}
            className="rounded-md bg-accent px-5 py-2.5 text-sm font-medium text-white disabled:opacity-50"
          >
            {busy ? "Creating…" : "Create invoice"}
          </button>
        </form>
      </div>
    </AppShell>
  );
}
