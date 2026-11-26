# Invoice AI — MVP Specification

Portfolio MVP for Product 4 (Invoice AI). **Milestone 2** delivers supplier/invoice CRUD, deterministic totals, duplicate flags, approval workflow, payment recording, web UI, and API tests. OCR, Anomaly Radar UI, and Flutter capture remain later milestones.

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
| InvoiceDocument | Uploaded PDF/image metadata (no paid OCR) |
| InvoiceReview | Validation notes / flags (seed; full UX later) |
| ApprovalStep | Approve/reject with comments — **API (M2)** |
| Payment | Date, amount, method/reference; updates balance — **API (M2)** |
| PurchaseOrderReference | Candidate PO match only |
| AccountingCategory | Suggested category; user confirms |
| AuditEvent | Seed + create/update/approve/pay mutations |

### Invoice statuses

Uploaded → Processing → Needs Review → Pending Approval → Approved / Rejected → Partially Paid → Paid → Archived

M2 workflow actions: `submit_review`, `submit_approval`, approve/reject, record payment.

## API groups (`/api/v1`)

| Group | M2 status |
|-------|-----------|
| `/auth` | Demo JWT login + `/me` |
| `/suppliers` | **Full CRUD** (archive on DELETE); admin for mutations |
| `/invoices` | **CRUD** + nested lines + `POST /{id}/workflow` |
| `/invoice-lines` | Nested via invoices; standalone stub |
| `/documents` | Coming Soon stub |
| `/invoice-reviews` | Coming Soon stub |
| `/approvals` | **POST decide** (role-checked) + pending list |
| `/payments` | **POST record** updates `amount_paid` / `balance_due` / status |
| `/reports/payables` | Coming Soon stub |
| `/ai/*` | Stub via AIProvider (no real OCR) |

Health (outside prefix): `GET /health`

Shared conventions: REST JSON, UUID PKs, UTC timestamps, decimal monetary values, error shape `{error:{code,message,details}}`.

## Acceptance criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Capture creates draft invoice | **M2 done** (manual create → uploaded / needs_review) |
| 2 | OCR unverified until user review | Stub / M3–M4 |
| 3 | Duplicate supplier + invoice number flagged | **M2 done** (`has_duplicate_warning`) |
| 4 | Totals deterministic (code, not AI) | **M2 done** (`app.services.totals`) |
| 5 | Approvals role-checked and audited | **M2 done** |
| 6 | Partial/full payments update balance | **M2 done** |
| 7 | Anomaly is review signal, not fraud | Seed flags; Radar UI **M3** |
| 8 | Local setup: Docker Postgres + health + demo login | **Done** |
| 9 | No paid APIs / OCR services required | **Met** |
| 10 | Seed 10 suppliers / 25 invoices + multi-role + tenant tests | **Done** |
| 11 | Web UI list/create/review/approve/pay | **M2 done** |

## Seed

- Org: Acme Payables Demo + Other Co Isolation
- Users: admin, reviewer, approver, staff (+ other-org admin); password `demo`
- 10 suppliers, 25 invoices with lines, documents, reviews/approvals/payments as relevant
- Duplicate pair `INV-DUP-5500`; anomaly examples (tax discrepancy, unusual amount, payment-details note)
- Varied statuses including unpaid, partially paid, paid

## Backlog by milestone

### M2 — Core payables — **Done**

- Invoice/supplier CRUD + capture → review
- Deterministic validation (subtotal+tax vs total, duplicates, due-before-invoice)
- Payment recording updating `amount_paid` / `balance_due`
- Role-checked approve/reject with audit
- Web UI + API tests

### M3 — AI + differentiator

- Wire DemoAIProvider (+ optional Ollama) for extract / category / anomaly **explain**
- Invoice Anomaly Radar UI: rules-first signals; never fraud verdict
- Category suggestion requires user confirm
- Document metadata upload path (no OCR SaaS)

### M4 — Polish

- Flutter camera/gallery + on-device text recognition where free
- Offline capture drafts + sync status
- Full approval UX polish, aging/spend reports, CSV export
- E2E demo script; lint/type gates

## Out of scope for Milestone 2

Do **not** implement OCR extraction pipelines, Anomaly Radar product UI, or Flutter mobile run requirements in M2.
