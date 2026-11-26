"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { demoLogin } from "@/lib/api";
import { DEMO_CREDENTIALS, setDemoSession } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState<string>(DEMO_CREDENTIALS.email);
  const [password, setPassword] = useState<string>(DEMO_CREDENTIALS.password);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const result = await demoLogin(email, password);
      setDemoSession(result.access_token, result.email);
      router.push("/dashboard");
    } catch (err) {
      // Offline-friendly demo: allow local placeholder if API is down
      if (
        email === DEMO_CREDENTIALS.email &&
        password === DEMO_CREDENTIALS.password
      ) {
        setDemoSession("local-demo-token", email);
        router.push("/dashboard");
        return;
      }
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-lg flex-col justify-center px-4 py-12">
      <div className="rounded-xl border border-slate/15 bg-white/85 p-8 shadow-sm backdrop-blur">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">
          Portfolio MVP
        </p>
        <h1 className="mt-2 font-display text-4xl text-ink">Invoice AI</h1>
        <p className="mt-3 text-slate">
          Demo JWT login against the local API. Prototype auth only — not production.
        </p>
        <form onSubmit={onSubmit} className="mt-8 space-y-4">
          <label className="block text-sm">
            <span className="text-slate">Email</span>
            <input
              className="mt-1 w-full rounded-md border border-slate/20 bg-paper px-3 py-2"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="username"
              required
            />
          </label>
          <label className="block text-sm">
            <span className="text-slate">Password</span>
            <input
              className="mt-1 w-full rounded-md border border-slate/20 bg-paper px-3 py-2"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          {error ? <p className="text-sm text-warn">{error}</p> : null}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-md bg-accent px-4 py-2.5 text-sm font-medium text-white hover:opacity-95 disabled:opacity-60"
          >
            {loading ? "Signing in…" : "Sign in (demo)"}
          </button>
        </form>
        <p className="mt-4 text-xs text-slate">
          Default: {DEMO_CREDENTIALS.email} / {DEMO_CREDENTIALS.password}. Also:
          reviewer@, approver@, staff@invoiceai.local (password: demo).
        </p>
      </div>
    </div>
  );
}
