"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { apiFetch, type InvoiceListItem } from "@/lib/api";

const STATUS_FILTERS = [
  "",
  "uploaded",
  "needs_review",
  "pending_approval",
  "approved",
  "rejected",
  "partially_paid",
  "paid",
];

export default function InvoicesPage() {
  const [items, setItems] = useState<InvoiceListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [anomalyOnly, setAnomalyOnly] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const qs = new URLSearchParams({ page_size: "100" });
      if (status) qs.set("status", status);
      if (query.trim()) qs.set("search", query.trim());
      if (anomalyOnly) qs.set("has_anomaly", "true");
      const data = await apiFetch<{ items: InvoiceListItem[]; total: number }>(
        `/api/v1/invoices?${qs}`
      );
      setItems(data.items);
      setTotal(data.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load invoices");
    } finally {
      setLoading(false);
    }
  }, [status, query, anomalyOnly]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <AppShell>
      <div className="space-y-6">
        <header className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="font-display text-3xl text-ink">Invoices</h1>
            <p className="mt-1 text-sm text-slate">
              Capture, review, approve, and pay — {total} matching
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              href="/extract"
              className="rounded-md border border-accent px-4 py-2 text-sm font-medium text-accent hover:bg-accentSoft"
            >
              Extract assist
            </Link>
            <Link
              href="/invoices/new"
              className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90"
            >
              New invoice
            </Link>
          </div>
        </header>

        <form
          className="flex flex-wrap gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            setQuery(search);
          }}
        >
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search invoice number…"
            className="min-w-[12rem] flex-1 rounded-md border border-slate/20 bg-white/80 px-3 py-2 text-sm text-ink"
          />
          <button
            type="submit"
            className="rounded-md border border-slate/20 px-3 py-2 text-sm text-slate hover:bg-mist"
          >
            Search
          </button>
          <label className="flex items-center gap-2 rounded-md border border-slate/15 bg-white/70 px-3 py-2 text-xs text-slate">
            <input
              type="checkbox"
              checked={anomalyOnly}
              onChange={(e) => setAnomalyOnly(e.target.checked)}
            />
            Anomaly / duplicate flags
          </label>
        </form>

        <div className="flex flex-wrap gap-2">
          {STATUS_FILTERS.map((s) => (
            <button
              key={s || "all"}
              type="button"
              onClick={() => setStatus(s)}
              className={`rounded-md px-3 py-1.5 text-xs ${
                status === s
                  ? "bg-accentSoft font-medium text-accent"
                  : "bg-white/70 text-slate hover:bg-mist"
              }`}
            >
              {s || "all"}
            </button>
          ))}
        </div>

        {loading && <p className="text-sm text-slate">Loading invoices…</p>}

        {error && (
          <p className="rounded-md border border-warn/30 bg-warn/10 px-3 py-2 text-sm text-warn">
            {error}
          </p>
        )}

        <div className="overflow-x-auto rounded-lg border border-slate/15 bg-white/80">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-slate/10 text-xs uppercase tracking-wide text-slate">
              <tr>
                <th className="px-4 py-3">Number</th>
                <th className="px-4 py-3">Supplier</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Total</th>
                <th className="px-4 py-3">Balance</th>
                <th className="px-4 py-3">Flags</th>
              </tr>
            </thead>
            <tbody>
              {items.map((inv) => (
                <tr key={inv.id} className="border-b border-slate/5 last:border-0">
                  <td className="px-4 py-3">
                    <Link
                      href={`/invoices/${inv.id}`}
                      className="font-medium text-accent hover:underline"
                    >
                      {inv.invoice_number}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-slate">
                    {inv.supplier_name || inv.supplier_id.slice(0, 8)}
                  </td>
                  <td className="px-4 py-3">
                    <span className="rounded bg-mist px-2 py-0.5 text-xs">
                      {inv.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {inv.currency} {inv.total}
                  </td>
                  <td className="px-4 py-3">{inv.balance_due}</td>
                  <td className="px-4 py-3 text-xs text-warn">
                    {inv.has_duplicate_warning ? "duplicate " : ""}
                    {inv.has_anomaly_signal ? "anomaly" : ""}
                    {!inv.has_duplicate_warning && !inv.has_anomaly_signal
                      ? "—"
                      : ""}
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-slate">
                    No invoices match this filter.
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
