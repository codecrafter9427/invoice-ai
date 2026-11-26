"use client";

import { AppShell } from "@/components/AppShell";
import { ComingSoon } from "@/components/ComingSoon";

export default function PaymentsPage() {
  return (
    <AppShell>
      <ComingSoon
        title="Payments"
        description="Payment recording and partial balances are deferred. No payment mutations in this scaffold."
      />
    </AppShell>
  );
}
