# Invoice AI — MVP Specification

Portfolio MVP for Product 4 (Invoice AI). **Milestone 5** wires Flutter camera/gallery → free on-device ML Kit OCR → review → draft save (paste fallback kept). **Milestone 4** delivered polish: aging/supplier-spend reports + CSV, category confirm PATCH, document preview metadata, web UX polish, Flutter capture/list against API, DEMO.md, and expanded tests.

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
| Supplier | Vendor directory — **CRUD** |
| Invoice | Header + workflow status — **CRUD + workflow** |
| InvoiceLine | Nested on invoice create/update; deterministic line totals |
| InvoiceDocument | Metadata + OCR text preview fields (**M4** tightened) |
| InvoiceReview | Validation notes / flags (seed; full UX later) |
| ApprovalStep | Approve/reject with comments |
| Payment | Date, amount, method/reference; updates balance |
| PurchaseOrderReference | Candidate PO match only |
| AccountingCategory | Suggested category; user confirms via **PATCH** (**M4**) |
| AuditEvent | Seed + create/update/approve/pay/document/category mutations |

### Invoice statuses

Uploaded → Processing → Needs Review → Pending Approval → Approved / Rejected → Partially Paid → Paid → Archived

Workflow actions: `submit_review`, `submit_approval`, approve/reject, record payment.

## API groups (`/api/v1`)

| Group | Status |
|-------|--------|
| `/auth` | Demo JWT login + `/me` |
| `/suppliers` | Full CRUD (archive on DELETE); admin for mutations |
| `/invoices` | CRUD + nested lines + workflow; `has_anomaly` list filter |
| `/invoices/{id}/category` | **M4** PATCH confirm category |
| `/invoice-lines` | Nested via invoices; standalone stub |
| `/documents` | Metadata register/list/get + preview fields |
| `/invoice-reviews` | Coming Soon stub |
| `/approvals` | POST decide (role-checked) + pending list |
| `/payments` | POST record updates `amount_paid` / `balance_due` / status |
| `/reports/payables` | **M4** overview + `/aging` + `/supplier-spend` + `/export.csv` |
| `/ai/invoice-extract` | Text→JSON + confidence; OCR unverified until review |
| `/ai/invoice-anomalies` | Anomaly Radar (rules-first; never fraud) |
| `/ai/category-suggestion` | Suggestion; `requires_confirmation=true` |

Health (outside prefix): `GET /health` → version `0.4.0-m4`

Shared conventions: REST JSON, UUID PKs, UTC timestamps, decimal monetary values, error shape `{error:{code,message,details}}`.

AI baseline: `{input, context_ids, options}` → `{result, explanation, sources, requires_confirmation}`.

## Acceptance criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Capture creates draft invoice | **Done** |
| 2 | OCR unverified until user review | **Done** |
| 3 | Duplicate supplier + invoice number flagged | **Done** |
| 4 | Totals deterministic (code, not AI) | **Done** |
| 5 | Approvals role-checked and audited | **Done** |
| 6 | Partial/full payments update balance | **Done** |
| 7 | Anomaly is review signal, not fraud | **Done** |
| 8 | Local setup: Docker Postgres + health + demo login | **Done** |
| 9 | No paid APIs / OCR services required | **Met** |
| 10 | Seed 10 suppliers / 25 invoices + multi-role + tenant tests | **Done** |
| 11 | Web UI list/create/review/approve/pay | **Done** |
| 12 | Extract assist + Anomaly Radar UI | **Done** |
| 13 | Category suggestion requires user confirm | **Done** (PATCH persist **M4**) |
| 14 | Aging + supplier-spend + CSV | **Done** (M4) |
| 15 | Flutter list/capture against API | **Done** (M4) |
| 16 | Flutter camera/gallery free ML Kit OCR → review → draft | **Done** (M5; no paid OCR / no auto-approve) |

## Seed

- Org: Acme Payables Demo + Other Co Isolation
- Users: admin, reviewer, approver, staff (+ other-org admin); password `demo`
- 10 suppliers, 25 invoices with lines, documents, reviews/approvals/payments as relevant
- Duplicate pair `INV-DUP-5500`; anomaly examples (tax discrepancy, unusual amount, payment-details note)
- Sample OCR text on `INV-2026-1000`, `INV-ANOM-TAX-01`, `INV-ANOM-PAY-03`
- Varied statuses including unpaid, partially paid, paid

## Backlog by milestone

### M1–M3 — **Done**

See prior README / chat history for scope.

### M4 — Polish — **Done**

- Aging + supplier-spend reports; CSV export
- Persist category suggestion confirm (PATCH)
- Tighten document preview metadata
- Web UX polish (list search/filters, detail documents/category, reports)
- Flutter capture/list against API; Flutter SDK docs
- Lint/typecheck + expanded pytest; DEMO.md

### M5 — Mobile OCR — **Done**

- `image_picker` + `google_mlkit_text_recognition` (free on-device only)
- Capture: camera/gallery → OCR text → extract assist → review checkbox → draft (`submit_for_review: false`)
- Paste fallback retained; Android/iOS permissions declared
- OCR unit tests with fakes; widget tests updated
- No DB migration; reuses `POST /ai/invoice-extract` and `POST /invoices`

### Remaining gaps (post-M5)

- Flutter offline draft queue (explicitly out of M5)
- Full mobile approve/pay UX
- Standalone `/invoice-lines` and `/invoice-reviews` beyond stubs
- Production auth / hosted OCR (out of portfolio free-only policy)

## Anomaly Radar rules

| Code | Rule (deterministic) |
|------|----------------------|
| `total_tax_discrepancy` | `money(subtotal + tax) != money(total)` or line sum ≠ total |
| `duplicate_like` | Same org supplier + invoice number (or seed flag) |
| `unusual_amount` | Total ≥ 3× peer average and gap ≥ 500 |
| `changed_payment_details` | Stated remittance ≠ supplier directory `payment_details` |

AI may explain why a rule fired. **Never** sets `is_fraud_verdict=true` or returns a fraud verdict.

## Out of scope

Do **not** require paid OCR/LLM. Ollama remains optional. Flutter camera OCR uses free on-device ML Kit only (M5); paste remains a valid demo path.
