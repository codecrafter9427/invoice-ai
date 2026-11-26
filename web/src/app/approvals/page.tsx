"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { apiFetch, ApiError } from "@/lib/api";

type PendingItem = {
  id: string;
  invoice_number: string;
  supplier_id: string;
  status: string;
  total: string;
  balance_due: string;
  currency: string;
  has_duplicate_warning: boolean;
};

export default function ApprovalsPage() {
  const [items, setItems] = useState<PendingItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [comments, setComments] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await apiFetch<{ items: PendingItem[]; total: number }>(
        "/api/v1/approvals/pending-invoices"
      );
      setItems(data.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load approvals");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function decide(invoiceId: string, decision: "approved" | "rejected") {
    setBusyId(invoiceId);
    setError(null);
    try {
      await apiFetch(`/api/v1/approvals?invoice_id=${invoiceId}`, {
        method: "POST",
        body: JSON.stringify({
          decision,
          comment:
            decision === "rejected"
              ? comments[invoiceId] || ""
              : comments[invoiceId] || "Approved from queue",
        }),
      });
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Decision failed");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <header>
          <h1 className="font-display text-3xl text-ink">Approvals</h1>
          <p className="mt-1 text-sm text-slate">
            Invoices awaiting approve / reject ({items.length}). Approver or
            admin only.
          </p>
        </header>

        {error && (
          <p className="rounded-md border border-warn/30 bg-warn/10 px-3 py-2 text-sm text-warn">
            {error}
          </p>
        )}

        <div className="space-y-4">
          {items.map((inv) => (
            <article
              key={inv.id}
              className="rounded-lg border border-slate/15 bg-white/80 p-4"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <Link
                    href={`/invoices/${inv.id}`}
                    className="font-medium text-accent hover:underline"
                  >
                    {inv.invoice_number}
                  </Link>
                  <p className="mt-1 text-sm text-slate">
                    {inv.currency} {inv.total}
                    {inv.has_duplicate_warning ? " · duplicate flag" : ""}
                  </p>
                </div>
                <span className="rounded bg-mist px-2 py-0.5 text-xs">
                  {inv.status}
                </span>
              </div>
              <label className="mt-3 block text-sm text-slate">
                Comment / rejection reason
                <input
                  value={comments[inv.id] || ""}
                  onChange={(e) =>
                    setComments((prev) => ({
                      ...prev,
                      [inv.id]: e.target.value,
                    }))
                  }
                  className="mt-1 w-full rounded-md border border-slate/20 bg-paper px-3 py-2 text-ink"
                />
              </label>
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={busyId === inv.id}
                  onClick={() => void decide(inv.id, "approved")}
                  className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
                >
                  Approve
                </button>
                <button
                  type="button"
                  disabled={busyId === inv.id}
                  onClick={() => void decide(inv.id, "rejected")}
                  className="rounded-md border border-warn px-4 py-2 text-sm font-medium text-warn disabled:opacity-50"
                >
                  Reject
                </button>
              </div>
            </article>
          ))}
          {items.length === 0 && (
            <p className="rounded-lg border border-slate/15 bg-white/80 px-4 py-8 text-center text-slate">
              No invoices pending approval.
            </p>
          )}
        </div>
      </div>
    </AppShell>
  );
}
