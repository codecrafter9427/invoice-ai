"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { apiFetch } from "@/lib/api";

type Counts = {
  needs_review: number;
  pending_approval: number;
  approved: number;
  partially_paid: number;
};

export default function DashboardPage() {
  const [counts, setCounts] = useState<Counts | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const statuses = [
          "needs_review",
          "pending_approval",
          "approved",
          "partially_paid",
        ] as const;
        const results = await Promise.all(
          statuses.map((status) =>
            apiFetch<{ total: number }>(
              `/api/v1/invoices?status=${status}&page_size=1`
            )
          )
        );
        setCounts({
          needs_review: results[0].total,
          pending_approval: results[1].total,
          approved: results[2].total,
          partially_paid: results[3].total,
        });
      } catch {
        setCounts(null);
      }
    }
    void load();
  }, []);

  const cards = [
    {
      label: "Awaiting review",
      value: counts?.needs_review,
      href: "/invoices?status=needs_review",
    },
    {
      label: "Pending approval",
      value: counts?.pending_approval,
      href: "/approvals",
    },
    {
      label: "Approved (unpaid)",
      value: counts?.approved,
      href: "/payments",
    },
    {
      label: "Partially paid",
      value: counts?.partially_paid,
      href: "/payments",
    },
  ];

  return (
    <AppShell>
      <section className="space-y-6">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-accent">
            Dashboard
          </p>
          <h1 className="mt-2 font-display text-3xl text-ink">
            Payables overview
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-slate">
            Live queue counts from org-scoped invoices. Aging reports and Anomaly
            Radar land in later milestones.
          </p>
        </div>
        <ul className="grid gap-3 sm:grid-cols-2">
          {cards.map((card) => (
            <li key={card.label}>
              <Link
                href={card.href}
                className="block rounded-lg border border-slate/15 bg-white/80 px-4 py-5 hover:border-accent/40"
              >
                <p className="text-sm text-slate">{card.label}</p>
                <p className="mt-2 font-display text-3xl text-ink">
                  {card.value ?? "—"}
                </p>
              </Link>
            </li>
          ))}
        </ul>
        <p className="text-sm text-slate">
          <Link href="/invoices/new" className="text-accent hover:underline">
            Create a manual invoice
          </Link>{" "}
          to walk the review → approve → pay path.
        </p>
      </section>
    </AppShell>
  );
}
