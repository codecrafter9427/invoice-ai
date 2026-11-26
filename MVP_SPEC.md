# Invoice AI — MVP Specification

Portfolio MVP for Product 4 (Invoice AI). **Milestone 1** delivers schema, auth, seed, health, and org-scoped list smoke paths. OCR, full approval UX, and Anomaly Radar productization remain later milestones.

## Purpose

Supplier invoice capture, extraction review, approval, payment tracking, and payable visibility for small businesses — with a transparent **Invoice Anomaly Radar** differentiator.

## Roles

| Role | Access |
|------|--------|
| Admin / Finance Manager (`admin`) | Suppliers, approvals, reports, settings, all org data |
| Reviewer (`reviewer`) | Validate extracted fields, flag issues |
| Approver (`approver`) | Approve / reject / record pay |
| Staff (`staff`) | Capture invoices and view assigned/own records |

Every business record is organization-scoped. Endpoints enforce tenant authorization server-side via JWT `org_id` + DB filter.

## Entities (M1 implemented)

| Entity | Notes |
|--------|--------|
| Organization | Tenant root |
| User | Auth subject + role (`admin` / `reviewer` / `approver` / `staff`) |
| Supplier | Vendor directory |
| Invoice | Header: number, dates, currency, totals, PO ref, terms, status; duplicate/anomaly seed flags |
| InvoiceLine | Description, qty, unit price, tax rate, line total (`Numeric`) |
| InvoiceDocument | Uploaded PDF/image metadata (no paid OCR) |
| InvoiceReview | Validation notes / flags |
| ApprovalStep | Approve/reject with comments |
| Payment | Date, amount, method/reference; partial supported |
| PurchaseOrderReference | Candidate PO match only |
| AccountingCategory | Suggested category; user confirms |
| AuditEvent | Seed/important mutations |

### Invoice statuses

Uploaded → Processing → Needs Review → Pending Approval → Approved / Rejected → Partially Paid → Paid → Archived

## API groups (`/api/v1`)

| Group | M1 status |
|-------|-----------|
| `/auth` | Demo JWT login + `/me` |
| `/suppliers` | **GET list** org-scoped; mutations Coming Soon |
| `/invoices` | **GET list** org-scoped; mutations Coming Soon |
| `/invoice-lines` | Coming Soon stub |
| `/documents` | Coming Soon stub |
| `/invoice-reviews` | Coming Soon stub |
| `/approvals` | Coming Soon stub |
| `/payments` | Coming Soon stub |
| `/reports/payables` | Coming Soon stub |
| `/ai/*` | Stub via AIProvider (no real OCR) |

Health (outside prefix): `GET /health`

Shared conventions: REST JSON, UUID PKs, UTC timestamps, decimal monetary values, error shape `{error:{code,message,details}}`.

## Acceptance criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Capture creates draft invoice | M2 |
| 2 | OCR unverified until user review | Stub / M3–M4 |
| 3 | Duplicate supplier + invoice number flagged | Seed examples; validation M2 |
| 4 | Totals deterministic (code, not AI) | Seed uses Decimal math; API calc M2 |
| 5 | Approvals role-checked and audited | Models + seed; workflow M2–M4 |
| 6 | Partial/full payments update balance | Seed states; API M2 |
| 7 | Anomaly is review signal, not fraud | Seed flags; Radar UI M3 |
| 8 | Local setup: Docker Postgres + health + demo login | **M1 done** |
| 9 | No paid APIs / OCR services required | **Met** |
| 10 | Seed 10 suppliers / 25 invoices + multi-role + tenant tests | **M1 done** |

## Seed (M1)

- Org: Acme Payables Demo + Other Co Isolation
- Users: admin, reviewer, approver, staff (+ other-org admin); password `demo`
- 10 suppliers, 25 invoices with lines, documents, reviews/approvals/payments as relevant
- Duplicate pair `INV-DUP-5500`; anomaly examples (tax discrepancy, unusual amount, payment-details note)
- Varied statuses including unpaid, partially paid, paid

## Backlog by milestone

### M2 — Core payables

- Invoice/supplier CRUD + capture → review
- Deterministic validation (subtotal+tax vs total, duplicates, missing fields, due-before-invoice)
- Document upload metadata (no OCR SaaS)
- Payment recording updating `amount_paid` / `balance_due`
- Unit tests for totals

### M3 — AI + differentiator

- Wire DemoAIProvider (+ optional Ollama) for extract / category / anomaly **explain**
- Invoice Anomaly Radar UI: rules-first signals; never fraud verdict
- Category suggestion requires user confirm

### M4 — Polish

- Flutter camera/gallery + on-device text recognition where free
- Offline capture drafts + sync status
- Full approval UX, aging/spend reports, CSV export
- E2E demo script; lint/type gates

## Out of scope for Milestone 1

Do **not** implement OCR extraction pipelines, full approval UX productization, or Anomaly Radar UI in M1.
