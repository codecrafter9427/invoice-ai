"use client";

import { AppShell } from "@/components/AppShell";
import { ComingSoon } from "@/components/ComingSoon";

export default function ReportsPage() {
  return (
    <AppShell>
      <ComingSoon
        title="Reports"
        description="Aging and supplier-spend reports with CSV export are Coming Soon."
      />
    </AppShell>
  );
}
