"use client";

import { FormEvent, useState } from "react";

import { AppShell } from "@/components/AppShell";
import {
  apiFetch,
  ApiError,
  type AIResponse,
  type ExtractResult,
} from "@/lib/api";

const SAMPLE_TEXT = `Supplier: Northwind Office Supply
Invoice Number: INV-DEMO-EXTRACT-01
Invoice Date: 2026-11-01
Due Date: 2026-12-01
PO: PO-2026-0101
Paper ream case x 12 @ $24.50 tax 8%
Subtotal: $294.00
Tax: $23.52
Total: $317.52
Currency: USD
`;

export default function ExtractAssistPage() {
  const [text, setText] = useState(SAMPLE_TEXT);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<AIResponse | null>(null);
  const [reviewed, setReviewed] = useState(false);

  async function runExtract(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setReviewed(false);
    try {
      const data = await apiFetch<AIResponse>("/api/v1/ai/invoice-extract", {
        method: "POST",
        body: JSON.stringify({
          input: { text, ocr_text: text },
          context_ids: [],
          options: {},
        }),
      });
      setResponse(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Extract failed");
      setResponse(null);
    } finally {
      setBusy(false);
    }
  }

  const result = (response?.result || {}) as ExtractResult;
  const header = result.header || {};
  const confidence = result.field_confidence || {};

  return (
    <AppShell>
      <div className="space-y-6">
        <header>
          <h1 className="font-display text-3xl text-ink">Extract assist</h1>
          <p className="mt-1 text-sm text-slate">
            Paste OCR or document text. Fields are suggestions with confidence —
            OCR stays unverified until you review.
          </p>
        </header>

        {error && (
          <p className="rounded-md border border-warn/30 bg-warn/10 px-3 py-2 text-sm text-warn">
            {error}
          </p>
        )}

        <form onSubmit={runExtract} className="space-y-3">
          <label className="block text-sm text-slate">
            Document / OCR text
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={12}
              className="mt-1 w-full rounded-md border border-slate/20 bg-paper px-3 py-2 font-mono text-sm text-ink"
            />
          </label>
          <div className="flex flex-wrap gap-2">
            <button
              type="submit"
              disabled={busy}
              className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {busy ? "Extracting…" : "Run extract"}
            </button>
            <button
              type="button"
              className="rounded-md border border-slate/20 px-4 py-2 text-sm text-slate hover:bg-mist"
              onClick={() => setText(SAMPLE_TEXT)}
            >
              Load sample
            </button>
          </div>
        </form>

        {response && (
          <section className="space-y-4">
            <div className="rounded-lg border border-accent/25 bg-accentSoft/40 px-4 py-3 text-sm">
              <p className="font-medium text-accent">
                {result.ocr_verified
                  ? "OCR verified"
                  : "OCR unverified — user review required"}
              </p>
              <p className="mt-1 text-slate">{response.explanation}</p>
              {response.requires_confirmation && (
                <p className="mt-2 text-xs text-slate">
                  Confirmation required before using these fields on an invoice.
                </p>
              )}
            </div>

            <div className="grid gap-3 rounded-lg border border-slate/15 bg-white/80 p-4 sm:grid-cols-2">
              {Object.keys(header).length === 0 && (
                <p className="text-sm text-slate sm:col-span-2">
                  No header fields detected.
                </p>
              )}
              {Object.entries(header).map(([key, value]) => (
                <div key={key}>
                  <p className="text-xs uppercase text-slate">
                    {key.replace(/_/g, " ")}
                    {confidence[key] != null && (
                      <span className="ml-2 normal-case text-slate/70">
                        conf {(confidence[key] * 100).toFixed(0)}%
                      </span>
                    )}
                  </p>
                  <p className="font-medium text-ink">{value}</p>
                </div>
              ))}
            </div>

            {(result.line_items?.length ?? 0) > 0 && (
              <div className="overflow-x-auto rounded-lg border border-slate/15 bg-white/80">
                <table className="min-w-full text-left text-sm">
                  <thead className="border-b border-slate/10 text-xs uppercase text-slate">
                    <tr>
                      <th className="px-4 py-3">Description</th>
                      <th className="px-4 py-3">Qty</th>
                      <th className="px-4 py-3">Unit</th>
                      <th className="px-4 py-3">Tax</th>
                      <th className="px-4 py-3">Conf</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.line_items!.map((ln, i) => (
                      <tr key={i} className="border-b border-slate/5">
                        <td className="px-4 py-2">{ln.description}</td>
                        <td className="px-4 py-2">{ln.quantity}</td>
                        <td className="px-4 py-2">{ln.unit_price}</td>
                        <td className="px-4 py-2">{ln.tax_rate}</td>
                        <td className="px-4 py-2">
                          {ln.confidence != null
                            ? `${(ln.confidence * 100).toFixed(0)}%`
                            : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {(result.validation_explanations?.length ?? 0) > 0 && (
              <div className="rounded-lg border border-warn/25 bg-warn/5 px-4 py-3 text-sm">
                <p className="font-medium text-warn">Validation explanations</p>
                <ul className="mt-2 list-inside list-disc text-slate">
                  {result.validation_explanations!.map((v) => (
                    <li key={v.code}>
                      <span className="font-medium">{v.code}:</span>{" "}
                      {v.explanation}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {(result.po_candidates?.length ?? 0) > 0 && (
              <div className="rounded-lg border border-slate/15 bg-white/80 px-4 py-3 text-sm">
                <p className="font-medium text-ink">PO candidates (not linked)</p>
                <ul className="mt-2 space-y-1 text-slate">
                  {result.po_candidates!.map((po) => (
                    <li key={po.id}>
                      {po.po_number} · score {po.score} · candidate only
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <label className="flex items-start gap-2 text-sm text-ink">
              <input
                type="checkbox"
                checked={reviewed}
                onChange={(e) => setReviewed(e.target.checked)}
                className="mt-1"
              />
              <span>
                I reviewed these fields. OCR remains unverified until this
                confirmation — values are assistive only; totals stay
                deterministic when creating an invoice.
              </span>
            </label>
            {reviewed && (
              <p className="text-sm text-accent">
                Review acknowledged. Create or edit the invoice manually with
                confirmed values (AI does not auto-save).
              </p>
            )}
          </section>
        )}
      </div>
    </AppShell>
  );
}
