"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { apiFetch, ApiError } from "@/lib/api";

type QueueItem = {
  invoice_id: string;
  invoice_number: string;
  supplier_id: string;
  supplier_name: string | null;
  status: string;
  total: string;
  balance_due: string;
  currency: string;
  has_duplicate_warning: boolean;
  has_anomaly_signal: boolean;
  unresolved_review_count: number;
  latest_flag: string | null;
  latest_notes: string | null;
};

export default function ReviewsPage() {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [notes, setNotes] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await apiFetch<{ items: QueueItem[]; total: number }>(
        "/api/v1/invoice-reviews/queue"
      );
      setItems(data.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load review queue");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function addNote(invoiceId: string, flag: string) {
    setBusyId(invoiceId);
    setError(null);
    try {
      await apiFetch("/api/v1/invoice-reviews", {
        method: "POST",
        body: JSON.stringify({
          invoice_id: invoiceId,
          flag,
          notes: notes[invoiceId] || "Reviewed from queue",
        }),
      });
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not create review note");
    } finally {
      setBusyId(null);
    }
  }

  async function submitApproval(invoiceId: string) {
    setBusyId(invoiceId);
    setError(null);
    try {
      await apiFetch(`/api/v1/invoices/${invoiceId}/workflow`, {
        method: "POST",
        body: JSON.stringify({ action: "submit_approval" }),
      });
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Submit for approval failed");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <header>
          <h1 className="font-display text-3xl text-ink">Reviews</h1>
          <p className="mt-1 text-sm text-slate">
            Standalone needs-review queue ({items.length}). Reviewer or admin
            can add flags/notes; staff can view.
          </p>
        </header>

        {error && (
          <p className="rounded-md border border-warn/30 bg-warn/10 px-3 py-2 text-sm text-warn">
            {error}
          </p>
        )}

        <div className="space-y-4">
          {items.length === 0 && !error && (
            <p className="text-sm text-slate">No invoices waiting for review.</p>
          )}
          {items.map((inv) => (
            <article
              key={inv.invoice_id}
              className="rounded-lg border border-slate/15 bg-white/80 p-4"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <Link
                    href={`/invoices/${inv.invoice_id}`}
                    className="font-medium text-accent hover:underline"
                  >
                    {inv.invoice_number}
                  </Link>
                  <p className="mt-1 text-sm text-slate">
                    {inv.supplier_name || inv.supplier_id} · {inv.currency}{" "}
                    {inv.total}
                    {inv.has_duplicate_warning ? " · duplicate" : ""}
                    {inv.has_anomaly_signal ? " · anomaly" : ""}
                  </p>
                  {(inv.latest_flag || inv.latest_notes) && (
                    <p className="mt-1 text-xs text-slate">
                      Latest: {inv.latest_flag || "none"}
                      {inv.latest_notes ? ` — ${inv.latest_notes}` : ""}
                      {inv.unresolved_review_count
                        ? ` (${inv.unresolved_review_count} open)`
                        : ""}
                    </p>
                  )}
                </div>
                <span className="rounded bg-mist px-2 py-0.5 text-xs">
                  {inv.status}
                </span>
              </div>

              <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-end">
                <label className="flex-1 text-xs text-slate">
                  Review note
                  <input
                    className="mt-1 w-full rounded-md border border-slate/20 bg-white px-3 py-2 text-sm text-ink"
                    value={notes[inv.invoice_id] || ""}
                    onChange={(e) =>
                      setNotes((prev) => ({
                        ...prev,
                        [inv.invoice_id]: e.target.value,
                      }))
                    }
                    placeholder="Validation notes…"
                  />
                </label>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={busyId === inv.invoice_id}
                    onClick={() =>
                      void addNote(
                        inv.invoice_id,
                        inv.has_duplicate_warning ? "duplicate" : "other"
                      )
                    }
                    className="rounded-md border border-slate/20 px-3 py-2 text-xs text-slate hover:bg-mist disabled:opacity-50"
                  >
                    Add note
                  </button>
                  <button
                    type="button"
                    disabled={busyId === inv.invoice_id}
                    onClick={() => void submitApproval(inv.invoice_id)}
                    className="rounded-md bg-accent px-3 py-2 text-xs font-medium text-white disabled:opacity-50"
                  >
                    Submit for approval
                  </button>
                </div>
              </div>
            </article>
          ))}
        </div>
      </div>
    </AppShell>
  );
}
