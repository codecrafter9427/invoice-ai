"use client";

import { AppShell } from "@/components/AppShell";
import { ComingSoon } from "@/components/ComingSoon";

export default function InvoicesPage() {
  return (
    <AppShell>
      <ComingSoon
        title="Invoices"
        description="Upload, manual entry, validation, and document preview are Coming Soon. OCR extraction is intentionally not implemented."
      />
    </AppShell>
  );
}
