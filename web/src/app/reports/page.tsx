"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import {
  apiFetch,
  exportCsvUrl,
  type AgingReport,
  type SupplierSpendReport,
} from "@/lib/api";
import { getDemoToken } from "@/lib/auth";

const BUCKET_LABELS: Record<string, string> = {
  current: "Current",
  "1_30": "1–30 days",
  "31_60": "31–60 days",
  "61_90": "61–90 days",
  "90_plus": "90+ days",
};

export default function ReportsPage() {
  const [aging, setAging] = useState<AgingReport | null>(null);
  const [spend, setSpend] = useState<SupplierSpendReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const [a, s] = await Promise.all([
        apiFetch<AgingReport>("/api/v1/reports/payables/aging"),
        apiFetch<SupplierSpendReport>("/api/v1/reports/payables/supplier-spend"),
      ]);
      setAging(a);
      setSpend(s);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load reports");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  function downloadCsv(report: "aging" | "supplier_spend") {
    const token = getDemoToken();
    const url = exportCsvUrl(report);
    void fetch(url, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then(async (res) => {
        if (!res.ok) throw new Error("CSV export failed");
        const blob = await res.blob();
        const href = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = href;
        a.download =
          report === "aging"
            ? `payables-aging.csv`
            : `payables-supplier-spend.csv`;
        a.click();
        URL.revokeObjectURL(href);
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : "CSV export failed");
      });
  }

  return (
    <AppShell>
      <div className="space-y-8">
        <header className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="font-display text-3xl text-ink">Payables reports</h1>
            <p className="mt-1 text-sm text-slate">
              Aging and supplier spend from live org data. Totals are
              deterministic — not AI estimates.
            </p>
          </div>
          <button
            type="button"
            onClick={() => void load()}
            className="rounded-md border border-slate/20 px-3 py-1.5 text-sm text-slate hover:bg-mist"
          >
            Refresh
          </button>
        </header>

        {error && (
          <p className="rounded-md border border-warn/30 bg-warn/10 px-3 py-2 text-sm text-warn">
            {error}
          </p>
        )}

        {loading && <p className="text-sm text-slate">Loading reports…</p>}

        {aging && (
          <section className="space-y-4">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <div>
                <h2 className="font-medium text-ink">Aging</h2>
                <p className="text-xs text-slate">
                  As of {aging.as_of} · {aging.invoice_count} open invoices ·{" "}
                  {aging.currency} {aging.total_balance_due} outstanding
                </p>
              </div>
              <button
                type="button"
                onClick={() => downloadCsv("aging")}
                className="rounded-md bg-accent px-3 py-1.5 text-xs font-medium text-white hover:opacity-90"
              >
                Export aging CSV
              </button>
            </div>
            <ul className="grid gap-2 sm:grid-cols-5">
              {aging.buckets.map((b) => (
                <li
                  key={b.bucket}
                  className="rounded-lg border border-slate/15 bg-white/80 px-3 py-3"
                >
                  <p className="text-xs uppercase tracking-wide text-slate">
                    {BUCKET_LABELS[b.bucket] || b.bucket}
                  </p>
                  <p className="mt-1 font-display text-xl text-ink">
                    {b.balance_due}
                  </p>
                  <p className="text-xs text-slate">{b.invoice_count} invoices</p>
                </li>
              ))}
            </ul>
            <div className="overflow-x-auto rounded-lg border border-slate/15 bg-white/80">
              <table className="min-w-full text-left text-sm">
                <thead className="border-b border-slate/10 text-xs uppercase text-slate">
                  <tr>
                    <th className="px-4 py-3">Invoice</th>
                    <th className="px-4 py-3">Supplier</th>
                    <th className="px-4 py-3">Bucket</th>
                    <th className="px-4 py-3">Days past due</th>
                    <th className="px-4 py-3">Balance</th>
                  </tr>
                </thead>
                <tbody>
                  {aging.rows.slice(0, 25).map((row) => (
                    <tr
                      key={row.invoice_id}
                      className="border-b border-slate/5 last:border-0"
                    >
                      <td className="px-4 py-2">
                        <Link
                          href={`/invoices/${row.invoice_id}`}
                          className="text-accent hover:underline"
                        >
                          {row.invoice_number}
                        </Link>
                      </td>
                      <td className="px-4 py-2 text-slate">
                        {row.supplier_name || "—"}
                      </td>
                      <td className="px-4 py-2">
                        {BUCKET_LABELS[row.bucket] || row.bucket}
                      </td>
                      <td className="px-4 py-2">{row.days_past_due}</td>
                      <td className="px-4 py-2">
                        {row.currency} {row.balance_due}
                      </td>
                    </tr>
                  ))}
                  {aging.rows.length === 0 && (
                    <tr>
                      <td
                        colSpan={5}
                        className="px-4 py-8 text-center text-slate"
                      >
                        No outstanding balances.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {spend && (
          <section className="space-y-4">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <div>
                <h2 className="font-medium text-ink">Supplier spend</h2>
                <p className="text-xs text-slate">
                  {spend.supplier_count} suppliers · spend {spend.total_spend} ·
                  outstanding {spend.total_outstanding}
                </p>
              </div>
              <button
                type="button"
                onClick={() => downloadCsv("supplier_spend")}
                className="rounded-md bg-accent px-3 py-1.5 text-xs font-medium text-white hover:opacity-90"
              >
                Export spend CSV
              </button>
            </div>
            <div className="overflow-x-auto rounded-lg border border-slate/15 bg-white/80">
              <table className="min-w-full text-left text-sm">
                <thead className="border-b border-slate/10 text-xs uppercase text-slate">
                  <tr>
                    <th className="px-4 py-3">Code</th>
                    <th className="px-4 py-3">Supplier</th>
                    <th className="px-4 py-3">Invoices</th>
                    <th className="px-4 py-3">Spend</th>
                    <th className="px-4 py-3">Outstanding</th>
                  </tr>
                </thead>
                <tbody>
                  {spend.rows.map((row) => (
                    <tr
                      key={row.supplier_id}
                      className="border-b border-slate/5 last:border-0"
                    >
                      <td className="px-4 py-2 text-slate">
                        {row.supplier_code || "—"}
                      </td>
                      <td className="px-4 py-2">{row.supplier_name || "—"}</td>
                      <td className="px-4 py-2">{row.invoice_count}</td>
                      <td className="px-4 py-2">
                        {row.currency} {row.total_spend}
                      </td>
                      <td className="px-4 py-2">{row.outstanding}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </div>
    </AppShell>
  );
}
