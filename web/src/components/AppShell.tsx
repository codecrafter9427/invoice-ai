"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { clearDemoSession, getDemoEmail, isDemoLoggedIn } from "@/lib/auth";

const NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/suppliers", label: "Suppliers" },
  { href: "/invoices", label: "Invoices" },
  { href: "/approvals", label: "Approvals" },
  { href: "/payments", label: "Payments" },
  { href: "/reports", label: "Reports" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [email, setEmail] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!isDemoLoggedIn()) {
      router.replace("/login");
      return;
    }
    setEmail(getDemoEmail());
    setReady(true);
  }, [router]);

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center text-slate">
        Loading…
      </div>
    );
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-6xl flex-col gap-6 px-4 py-6 md:flex-row md:px-8">
      <aside className="w-full shrink-0 md:w-56">
        <div className="rounded-lg border border-slate/15 bg-white/80 p-4 backdrop-blur">
          <p className="font-display text-xl text-ink">Invoice AI</p>
          <p className="mt-1 truncate text-xs text-slate">{email}</p>
          <nav className="mt-6 flex flex-row flex-wrap gap-2 md:flex-col">
            {NAV.map((item) => {
              const active =
                pathname === item.href ||
                (item.href !== "/dashboard" &&
                  pathname?.startsWith(`${item.href}/`));
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`rounded-md px-3 py-2 text-sm ${
                    active
                      ? "bg-accentSoft font-medium text-accent"
                      : "text-slate hover:bg-mist"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <button
            type="button"
            className="mt-6 w-full rounded-md border border-slate/20 px-3 py-2 text-sm text-slate hover:bg-mist"
            onClick={() => {
              clearDemoSession();
              router.replace("/login");
            }}
          >
            Sign out
          </button>
        </div>
      </aside>
      <main className="min-w-0 flex-1">{children}</main>
    </div>
  );
}
