# Invoice AI — Business Insights connector

Read-only, versioned export for Business Insights (and other consumers).

**Base prefix:** `/api/v1/connectors/insights/v1`  
**Product:** `invoice-ai`  
**App version:** `0.6.0-m6`

## Authentication

Two options (document both for Insights adapters):

1. **Org-scoped JWT** — `Authorization: Bearer <access_token>` from `/api/v1/auth/demo-login` (or future prod login). Organization is taken from the token `org_id` claim.
2. **Shared connector token** — set `INSIGHTS_CONNECTOR_TOKEN` in the Invoice AI environment. Call with:
   - `Authorization: Bearer <INSIGHTS_CONNECTOR_TOKEN>`
   - plus **`X-Organization-Id: <uuid>`** (or `?organization_id=<uuid>`)

Never return write capabilities on these routes. Mutations return 404/405.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | `{status, product, api_version, app_version, read_only}` — no auth required |
| `GET` | `/meta` | Metric catalog + auth hints |
| `GET` | `/payables/summary?as_of=` | `outstanding_balance`, `paid_this_month`, `aging_totals`, open count |
| `GET` | `/payables/aging?as_of=` | Same shape as UI aging report |
| `GET` | `/payables/supplier-spend?as_of=` | Same shape as UI supplier-spend |

### `payables/summary` shape

```json
{
  "as_of": "2026-11-27",
  "currency": "USD",
  "outstanding_balance": "12345.67",
  "open_invoice_count": 12,
  "paid_this_month": {
    "year_month": "2026-11",
    "amount_paid": "3200.00",
    "payment_count": 5
  },
  "aging_totals": {
    "current": "…",
    "1_30": "…",
    "31_60": "…",
    "61_90": "…",
    "90_plus": "…"
  },
  "source": { "product": "invoice-ai", "generated_at": "…" }
}
```

**Paid this month:** sum of `payments.amount` where `payment_date` is in `[month_start, as_of]` for the org (deterministic; not AI).

## Existing UI reports

Invoice AI UI continues to use `/api/v1/reports/payables*`. Insights **should** prefer `/connectors/insights/v1/*` so UI reports can evolve without breaking sync.

## Out of scope

Invoice PDFs, OCR text, anomaly explanations, approval comments, and any mutations.
