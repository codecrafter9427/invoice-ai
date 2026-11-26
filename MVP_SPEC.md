# Invoice AI — MVP Specification

Portfolio MVP for Product 4 (Invoice AI). This document tracks intended scope; the current codebase is a **skeleton only**.

## Purpose

Supplier invoice capture, extraction review, approval, payment tracking, and payable visibility for small businesses — with a transparent **Invoice Anomaly Radar** differentiator.

## Roles

| Role | Access |
|------|--------|
| Admin / Finance Manager | Suppliers, approvals, reports, settings, all org data |
| Reviewer | Validate extracted fields, flag issues |
| Approver | Approve / reject / record pay |
| Staff | Capture invoices and view assigned/own records |

Every business record is organization-scoped. Endpoints must enforce tenant authorization server-side (not yet implemented).

## Entities

| Entity | Notes |
|--------|--------|
| Organization | Tenant root |
| User | Auth subject + role membership |
| Supplier | Vendor directory |
| Invoice | Header: number, dates, currency, totals, PO ref, terms, status |
| InvoiceLine | Description, qty, unit price, tax rate, line total |
| InvoiceDocument | Uploaded PDF/image metadata (no paid OCR service) |
| InvoiceReview | Validation notes / flags |
| ApprovalStep | Approve/reject with comments and audit |
| Payment | Date, amount, method/reference; partial supported |
| PurchaseOrderReference | Candidate PO match only |
| AccountingCategory | Suggested category; user confirms |
| AuditEvent | Approvals, adjustments, important mutations |

### Invoice statuses (planned)

Uploaded → Processing → Needs Review → Pending Approval → Approved / Rejected → Partially Paid → Paid → Archived

## API groups (`/api/v1`)

| Group | Status |
|-------|--------|
| `/auth` | Demo login placeholder |
| `/suppliers` | Coming Soon stub |
| `/invoices` | Coming Soon stub |
| `/invoice-lines` | Coming Soon stub |
| `/documents` | Coming Soon stub |
| `/invoice-reviews` | Coming Soon stub |
| `/approvals` | Coming Soon stub |
| `/payments` | Coming Soon stub |
| `/reports/payables` | Coming Soon stub |
| `/ai/invoice-extract` | Stub via AIProvider (no real OCR) |
| `/ai/invoice-anomalies` | Stub via AIProvider (differentiator) |
| `/ai/category-suggestion` | Stub via AIProvider |

Shared conventions: REST JSON, UUID PKs, UTC timestamps, decimal monetary values, error shape `{error:{code,message,details}}`, list pagination/search/sort/filters.

AI request baseline: `{input, context_ids, options}`  
AI response baseline: `{result, explanation, sources:[{type,id,label}], requires_confirmation}`

Health (outside prefix): `GET /health`

## Web baseline (planned)

- Dashboard: awaiting review/approval, overdue unpaid, paid this month, outstanding
- Supplier directory; PDF/image upload and manual invoice entry
- Header + line items with document preview and editable fields
- Validation: subtotal+tax vs total, duplicate supplier/invoice number, missing fields, due-before-invoice-date
- Approval history/comments/rejection reason
- Payment recording with partial payments
- Aging and supplier-spend reports; CSV export; searchable invoice list

## Mobile baseline (planned)

- Camera/gallery capture; on-device text recognition where supported (free SDKs)
- Crop/rotate if free library supports; extracted fields editable
- Save capture draft offline; invoice list/status
- Review, edit, flag issue, submit for approval
- Role-based approve/reject; record payment/reference
- Duplicate warning before submit

## AI features (planned)

| Feature | Behavior |
|---------|----------|
| Invoice extract | Header + lines from OCR text via local model or demo; structured JSON + confidence |
| Validation explain | Explain validation issues; totals remain deterministic code |
| PO match | Candidate match only; user confirms |
| Category suggestion | Based on description/history; user confirms |
| Anomaly Radar | Transparent review signals; never fraud verdict |

Rules: backend-only model calls; typed I/O; validate output; label AI content; human approval before business-changing actions; DemoAIProvider when Ollama unavailable. No accounting/tax advice. No paid OCR/LLM APIs.

## Differentiator — Invoice Anomaly Radar

Transparent signals (rules first) for:

1. Unusual supplier amount vs history
2. Duplicate-like invoice (supplier + number / near-duplicate content)
3. Total / tax discrepancy vs line math
4. Changed payment details vs prior supplier records

AI may **explain** a signal. AI must **never** declare fraud. Operator reviews and decides.

## Acceptance criteria (Milestone targets)

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Capture creates draft invoice | Not started |
| 2 | OCR is unverified until user review | Stub only / no OCR |
| 3 | Duplicate supplier + invoice number flagged | Not started |
| 4 | Totals are deterministic (code, not AI) | Not started |
| 5 | Approvals are role-checked and audited | Not started |
| 6 | Partial/full payments update balance | Not started |
| 7 | Anomaly is a review signal, not fraud verdict | Stub only |
| 8 | Local setup: Docker Postgres + health + demo login shell | Skeleton |
| 9 | No paid APIs / OCR services required | Met |

## Seed targets (later)

10 suppliers, 25 invoices with line items, duplicate/anomaly examples, varied payment states. Fictional data only. Demo org with at least two roles.

## Backlog (explicitly deferred)

- Full SQLAlchemy models + Alembic migrations
- Seed script with anomaly/duplicate fixtures
- Real JWT/session auth and org-scoped authorization
- Document upload + on-device OCR pipeline
- Approval workflow engine and payment ledger
- Aging/spend reports and CSV export
- Mobile offline draft queue and conflict handling
- Wired Ollama prompts for extract / anomaly explanation / category
- Unit tests for totals; API tenant auth tests; E2E demo script

## Out of scope for this scaffold

Do **not** implement OCR extraction, approval workflows, payments, or real AI extraction in Milestone 1 skeleton.
