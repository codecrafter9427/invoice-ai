"use client";

import { AppShell } from "@/components/AppShell";
import { ComingSoon } from "@/components/ComingSoon";

export default function ApprovalsPage() {
  return (
    <AppShell>
      <ComingSoon
        title="Approvals"
        description="Approval workflow, comments, and rejection reasons are not implemented yet."
      />
    </AppShell>
  );
}
