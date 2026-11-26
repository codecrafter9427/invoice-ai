"use client";

import { AppShell } from "@/components/AppShell";

export default function DashboardPage() {
  return (
    <AppShell>
      <section className="rounded-lg border border-slate/15 bg-white/70 p-8 shadow-sm backdrop-blur">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-accent">
          Dashboard
        </p>
        <h1 className="mt-2 font-display text-3xl text-ink">Payables overview</h1>
        <p className="mt-3 max-w-2xl text-slate">
          Scaffold shell only. Metrics for awaiting review/approval, overdue unpaid,
          paid this month, and outstanding will appear after seed data and CRUD land.
        </p>
        <ul className="mt-8 grid gap-3 sm:grid-cols-2">
          {[
            "Awaiting review",
            "Pending approval",
            "Overdue unpaid",
            "Paid this month",
          ].map((label) => (
            <li
              key={label}
              className="rounded-md border border-dashed border-slate/25 bg-mist/60 px-4 py-5 text-sm text-slate"
            >
              {label}: Coming Soon
            </li>
          ))}
        </ul>
      </section>
    </AppShell>
  );
}
