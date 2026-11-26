"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import {
  apiFetch,
  ApiError,
  type AIResponse,
  type AnomalySignal,
  type InvoiceListItem,
} from "@/lib/api";

export default function AnomalyRadarPage() {
  const [invoices, setInvoices] = useState<InvoiceListItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [signals, setSignals] = useState<AnomalySignal[]>([]);
  const [explanation, setExplanation] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const loadList = useCallback(async () => {
    setError(null);
    try {
      const data = await apiFetch<{ items: InvoiceListItem[] }>(
        "/api/v1/invoices?page_size=50&has_anomaly=true"
      );
      // Fallback: if filter unsupported, client-filter
      let items = data.items || [];
      if (!items.some((i) => i.has_anomaly_signal || i.has_duplicate_warning)) {
        const all = await apiFetch<{ items: InvoiceListItem[] }>(
          "/api/v1/invoices?page_size=50"
        );
        items = (all.items || []).filter(
          (i) => i.has_anomaly_signal || i.has_duplicate_warning
        );
      } else {
        items = items.filter(
          (i) => i.has_anomaly_signal || i.has_duplicate_warning
        );
      }
      setInvoices(items);
      if (items.length && !selectedId) {
        setSelectedId(items[0].id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load invoices");
    }
  }, [selectedId]);

  useEffect(() => {
    void loadList();
  }, [loadList]);

  useEffect(() => {
    if (!selectedId) return;
    let cancelled = false;
    (async () => {
      setBusy(true);
      setError(null);
      try {
        const data = await apiFetch<AIResponse>("/api/v1/ai/invoice-anomalies", {
          method: "POST",
          body: JSON.stringify({
            input: { invoice_id: selectedId },
            context_ids: [selectedId],
            options: {},
          }),
        });
        if (cancelled) return;
        const raw = (data.result.signals as AnomalySignal[]) || [];
        setSignals(
          raw.map((s) => ({ ...s, is_fraud_verdict: false }))
        );
        setExplanation(data.explanation);
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof ApiError ? e.message : "Radar failed");
          setSignals([]);
          setExplanation(null);
        }
      } finally {
        if (!cancelled) setBusy(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  return (
    <AppShell>
      <div className="space-y-6">
        <header>
          <h1 className="font-display text-3xl text-ink">
            Invoice Anomaly Radar
          </h1>
          <p className="mt-1 text-sm text-slate">
            Rules-first review signals: unusual amount, duplicate-like,
            total/tax discrepancy, changed payment details. Never a fraud
            verdict.
          </p>
        </header>

        <div className="rounded-lg border border-slate/15 bg-white/60 px-4 py-3 text-sm text-slate">
          <p className="font-medium text-ink">How to read this</p>
          <p className="mt-1">
            Each signal cites a deterministic rule and evidence. AI may explain
            why the rule fired. The product does <em>not</em> declare fraud —
            treat every signal as a prompt for human review.
          </p>
        </div>

        {error && (
          <p className="rounded-md border border-warn/30 bg-warn/10 px-3 py-2 text-sm text-warn">
            {error}
          </p>
        )}

        <div className="grid gap-6 lg:grid-cols-[minmax(0,14rem)_1fr]">
          <aside className="space-y-2">
            <p className="text-xs uppercase text-slate">Flagged invoices</p>
            {invoices.length === 0 && (
              <p className="text-sm text-slate">No flagged invoices in seed.</p>
            )}
            <ul className="space-y-1">
              {invoices.map((inv) => (
                <li key={inv.id}>
                  <button
                    type="button"
                    onClick={() => setSelectedId(inv.id)}
                    className={`w-full rounded-md px-3 py-2 text-left text-sm ${
                      selectedId === inv.id
                        ? "bg-accentSoft font-medium text-accent"
                        : "text-slate hover:bg-mist"
                    }`}
                  >
                    {inv.invoice_number}
                    <span className="mt-0.5 block text-xs opacity-80">
                      {inv.currency} {inv.total}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </aside>

          <section className="space-y-4">
            {selectedId && (
              <p className="text-sm text-slate">
                Viewing{" "}
                <Link
                  href={`/invoices/${selectedId}`}
                  className="text-accent hover:underline"
                >
                  invoice detail
                </Link>
                {busy ? " · scanning…" : ""}
              </p>
            )}

            {explanation && (
              <p className="rounded-lg border border-slate/15 bg-white/80 px-4 py-3 text-sm text-slate">
                {explanation}
              </p>
            )}

            {signals.length === 0 && !busy && selectedId && (
              <p className="text-sm text-slate">
                No rules fired for this invoice right now.
              </p>
            )}

            <ul className="space-y-3">
              {signals.map((s) => (
                <li
                  key={s.code + s.message}
                  className="rounded-lg border border-slate/15 bg-white/80 px-4 py-3"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded bg-mist px-2 py-0.5 text-xs font-medium uppercase text-ink">
                      {s.code}
                    </span>
                    <span className="text-xs text-slate">{s.severity}</span>
                    <span className="rounded bg-accentSoft px-2 py-0.5 text-xs text-accent">
                      review signal — not fraud
                    </span>
                  </div>
                  <p className="mt-2 text-sm font-medium text-ink">{s.message}</p>
                  {s.explanation && (
                    <p className="mt-1 text-sm text-slate">{s.explanation}</p>
                  )}
                  {s.evidence && Object.keys(s.evidence).length > 0 && (
                    <pre className="mt-2 overflow-x-auto rounded bg-mist/60 p-2 text-xs text-slate">
                      {JSON.stringify(s.evidence, null, 2)}
                    </pre>
                  )}
                  <p className="mt-2 text-xs text-slate">
                    is_fraud_verdict: {String(!!s.is_fraud_verdict)}
                  </p>
                </li>
              ))}
            </ul>
          </section>
        </div>
      </div>
    </AppShell>
  );
}
