"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { apiFetch, ApiError, type Supplier } from "@/lib/api";

export default function SuppliersPage() {
  const [items, setItems] = useState<Supplier[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await apiFetch<{ items: Supplier[]; total: number }>(
        "/api/v1/suppliers?page_size=100"
      );
      setItems(data.items);
      setTotal(data.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load suppliers");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await apiFetch<Supplier>("/api/v1/suppliers", {
        method: "POST",
        body: JSON.stringify({
          code: code.trim(),
          name: name.trim(),
          email: email.trim() || null,
        }),
      });
      setCode("");
      setName("");
      setEmail("");
      setShowForm(false);
      await load();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Could not create supplier"
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <header className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="font-display text-3xl text-ink">Suppliers</h1>
            <p className="mt-1 text-sm text-slate">
              Organization vendor directory ({total})
            </p>
          </div>
          <button
            type="button"
            className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90"
            onClick={() => setShowForm((v) => !v)}
          >
            {showForm ? "Cancel" : "Add supplier"}
          </button>
        </header>

        {error && (
          <p className="rounded-md border border-warn/30 bg-warn/10 px-3 py-2 text-sm text-warn">
            {error}
          </p>
        )}

        {showForm && (
          <form
            onSubmit={onCreate}
            className="grid gap-3 rounded-lg border border-slate/15 bg-white/80 p-4 sm:grid-cols-3"
          >
            <label className="text-sm text-slate">
              Code
              <input
                required
                value={code}
                onChange={(e) => setCode(e.target.value)}
                className="mt-1 w-full rounded-md border border-slate/20 bg-paper px-3 py-2 text-ink"
              />
            </label>
            <label className="text-sm text-slate">
              Name
              <input
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="mt-1 w-full rounded-md border border-slate/20 bg-paper px-3 py-2 text-ink"
              />
            </label>
            <label className="text-sm text-slate">
              Email
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 w-full rounded-md border border-slate/20 bg-paper px-3 py-2 text-ink"
              />
            </label>
            <div className="sm:col-span-3">
              <button
                type="submit"
                disabled={busy}
                className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              >
                {busy ? "Saving…" : "Create supplier"}
              </button>
              <p className="mt-2 text-xs text-slate">Admin role required.</p>
            </div>
          </form>
        )}

        <div className="overflow-x-auto rounded-lg border border-slate/15 bg-white/80">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-slate/10 text-xs uppercase tracking-wide text-slate">
              <tr>
                <th className="px-4 py-3">Code</th>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Email</th>
                <th className="px-4 py-3">Active</th>
              </tr>
            </thead>
            <tbody>
              {items.map((s) => (
                <tr key={s.id} className="border-b border-slate/5 last:border-0">
                  <td className="px-4 py-3 font-medium text-ink">{s.code}</td>
                  <td className="px-4 py-3">{s.name}</td>
                  <td className="px-4 py-3 text-slate">{s.email || "—"}</td>
                  <td className="px-4 py-3">{s.is_active ? "Yes" : "No"}</td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-slate">
                    No suppliers yet.
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
