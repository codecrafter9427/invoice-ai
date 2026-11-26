# Invoice AI — MVP Specification

Portfolio MVP for Product 4 (Invoice AI). **Milestone 3** delivers AIProvider extract/category/anomaly explain, Invoice Anomaly Radar UI, document metadata registration, and AI API tests. Flutter capture remains M4.

## Purpose

Supplier invoice capture, extraction review, approval, payment tracking, and payable visibility for small businesses — with a transparent **Invoice Anomaly Radar** differentiator.

## Roles

| Role | Access |
|------|--------|
| Admin / Finance Manager (`admin`) | Suppliers, approvals, payments, reports, settings, all org data |
| Reviewer (`reviewer`) | Validate fields, submit for approval |
| Approver (`approver`) | Approve / reject / record pay |
| Staff (`staff`) | Capture invoices and view records |

Every business record is organization-scoped. Endpoints enforce tenant authorization server-side via JWT `org_id` + DB filter.

## Entities

| Entity | Notes |
|--------|--------|
| Organization | Tenant root |
| User | Auth subject + role (`admin` / `reviewer` / `approver` / `staff`) |
| Supplier | Vendor directory — **CRUD (M2)** |
| Invoice | Header + workflow status — **CRUD + workflow (M2)** |
| InvoiceLine | Nested on invoice create/update; deterministic line totals |
| InvoiceDocument | Metadata register + optional pasted OCR text (**M3**) |
| InvoiceReview | Validation notes / flags (seed; full UX later) |
| ApprovalStep | Approve/reject with comments — **API (M2)** |
| Payment | Date, amount, method/reference; updates balance — **API (M2)** |
| PurchaseOrderReference | Candidate PO match only (**M3** extract assist) |
| AccountingCategory | Suggested category; user confirms (**M3**) |
| AuditEvent | Seed + create/update/approve/pay/document mutations |

### Invoice statuses

Uploaded → Processing → Needs Review → Pending Approval → Approved / Rejected → Partially Paid → Paid → Archived

M2 workflow actions: `submit_review`, `submit_approval`, approve/reject, record payment.

## API groups (`/api/v1`)

| Group | Status |
|-------|--------|
| `/auth` | Demo JWT login + `/me` |
| `/suppliers` | Full CRUD (archive on DELETE); admin for mutations |
| `/invoices` | CRUD + nested lines + workflow; `has_anomaly` list filter |
| `/invoice-lines` | Nested via invoices; standalone stub |
| `/documents` | **M3** metadata register/list/get (no OCR SaaS) |
| `/invoice-reviews` | Coming Soon stub |
| `/approvals` | POST decide (role-checked) + pending list |
| `/payments` | POST record updates `amount_paid` / `balance_due` / status |
| `/reports/payables` | Coming Soon stub |
| `/ai/invoice-extract` | **M3** text→JSON + confidence; OCR unverified until review |
| `/ai/invoice-anomalies` | **M3** Anomaly Radar (rules-first; never fraud) |
| `/ai/category-suggestion` | **M3** suggestion; `requires_confirmation=true` |

Health (outside prefix): `GET /health` → version `0.3.0-m3`

Shared conventions: REST JSON, UUID PKs, UTC timestamps, decimal monetary values, error shape `{error:{code,message,details}}`.

AI baseline: `{input, context_ids, options}` → `{result, explanation, sources, requires_confirmation}`.

## Acceptance criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Capture creates draft invoice | **Done** (M2) |
| 2 | OCR unverified until user review | **Done** (M3 extract `ocr_verified=false`) |
| 3 | Duplicate supplier + invoice number flagged | **Done** (M2 + radar `duplicate_like`) |
| 4 | Totals deterministic (code, not AI) | **Done** (`app.services.totals`) |
| 5 | Approvals role-checked and audited | **Done** |
| 6 | Partial/full payments update balance | **Done** |
| 7 | Anomaly is review signal, not fraud | **Done** (Radar; `is_fraud_verdict=false`) |
| 8 | Local setup: Docker Postgres + health + demo login | **Done** |
| 9 | No paid APIs / OCR services required | **Met** (`AI_PROVIDER=demo`) |
| 10 | Seed 10 suppliers / 25 invoices + multi-role + tenant tests | **Done** |
| 11 | Web UI list/create/review/approve/pay | **Done** (M2) |
| 12 | Extract assist + Anomaly Radar UI | **Done** (M3) |
| 13 | Category suggestion requires user confirm | **Done** (M3) |

## Seed

- Org: Acme Payables Demo + Other Co Isolation
- Users: admin, reviewer, approver, staff (+ other-org admin); password `demo`
- 10 suppliers, 25 invoices with lines, documents, reviews/approvals/payments as relevant
- Duplicate pair `INV-DUP-5500`; anomaly examples (tax discrepancy, unusual amount, payment-details note)
- Sample OCR text on `INV-2026-1000`, `INV-ANOM-TAX-01`, `INV-ANOM-PAY-03`
- Varied statuses including unpaid, partially paid, paid

## Backlog by milestone

### M2 — Core payables — **Done**

- Invoice/supplier CRUD + capture → review
- Deterministic validation (subtotal+tax vs total, duplicates, due-before-invoice)
- Payment recording updating `amount_paid` / `balance_due`
- Role-checked approve/reject with audit
- Web UI + API tests

### M3 — AI + differentiator — **Done**

- Wire DemoAIProvider (+ optional Ollama) for extract / category / anomaly **explain**
- Invoice Anomaly Radar UI: rules-first signals; never fraud verdict
- Category suggestion requires user confirm
- Document metadata upload path (no OCR SaaS)
- PO match returned as **candidate only**
- Validation issue explanations on extract

### M4 — Polish

- Flutter camera/gallery + on-device text recognition where free
- Offline capture drafts + sync status
- Full approval UX polish, aging/spend reports, CSV export
- E2E demo script; lint/type gates

## Anomaly Radar rules (M3)

| Code | Rule (deterministic) |
|------|----------------------|
| `total_tax_discrepancy` | `money(subtotal + tax) != money(total)` or line sum ≠ total |
| `duplicate_like` | Same org supplier + invoice number (or seed flag) |
| `unusual_amount` | Total ≥ 3× peer average and gap ≥ 500 |
| `changed_payment_details` | Stated remittance ≠ supplier directory `payment_details` |

AI may explain why a rule fired. **Never** sets `is_fraud_verdict=true` or returns a fraud verdict.

## Out of scope for Milestone 3

Do **not** require Ollama, paid OCR/LLM, Flutter mobile run, or full reports/CSV in M3.
