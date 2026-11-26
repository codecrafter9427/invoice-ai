# Invoice AI

Supplier invoice capture, extraction review, approval, payment tracking, and payable visibility for small businesses.

**Milestone 2 complete:** supplier/invoice CRUD with line items, deterministic totals, duplicate flags, review → approval workflow (role-checked + audited), payment recording with balance updates, web UI, and API tests. OCR extraction, Anomaly Radar UI, and Flutter capture are deferred.

## Purpose

- Capture supplier invoices (manual entry now; camera/OCR later) and review fields
- Validate totals, duplicates, and dates with deterministic calculations
- Route invoices through review → approval → payment tracking
- Surface **Invoice Anomaly Radar** (differentiator) in M3: transparent review signals — never fraud verdicts
- Demo locally with free tooling only (no paid APIs or OCR services)

## Stack

| Layer | Technology |
|-------|------------|
| Web | Next.js + TypeScript |
| Backend | FastAPI + Pydantic + SQLAlchemy + Alembic |
| Database | PostgreSQL (UUID PKs, `Numeric` monetary decimals) |
| Mobile | Flutter (shell; run optional) |
| AI | `AIProvider` + `DemoAIProvider` stubs; optional Ollama later |
| Auth | Demo JWT login, org-scoped authorization |

## Project layout

```
products/invoice-ai/
  README.md
  MVP_SPEC.md
  .env.example
  docker-compose.yml          # Postgres on host port 5436
  backend/
    app/                      # FastAPI app, services, APIs
    alembic/                  # Migrations
    scripts/seed.py           # Demo seed
    tests/                    # Health, auth/tenant, M2 workflow tests
  web/                        # Next.js payables UI
  mobile/                     # Flutter shell
```

## Prerequisites

- Docker Desktop (PostgreSQL)
- Python 3.11+
- Node.js 20+
- Flutter SDK (optional)

## Setup

### 1. Environment

```bash
cd products/invoice-ai
cp .env.example .env
```

### 2. Database

```bash
docker compose up -d
```

PostgreSQL listens on **host port `5436`** (container `5432`).

### 3. Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
alembic upgrade head
python -m scripts.seed
uvicorn app.main:app --reload --port 8004
```

- Health: `GET http://localhost:8004/health`
- API prefix: `/api/v1`
- OpenAPI: `http://localhost:8004/docs`

### 4. Web

```bash
cd web
npm install
npm run dev
```

Open `http://localhost:3004`. Sign in with a demo account below.

### 5. Mobile (optional)

```bash
cd mobile
flutter pub get
flutter run
```

## Demo credentials

Password for all accounts: **`demo`**

| Email | Role |
|-------|------|
| `demo@invoiceai.local` | Admin / Finance Manager |
| `reviewer@invoiceai.local` | Reviewer |
| `approver@invoiceai.local` | Approver |
| `staff@invoiceai.local` | Staff |
| `other@otherco.local` | Admin of isolation org (tenant tests) |

Seed includes: **10 suppliers**, **25 invoices** with line items, duplicate + anomaly flag examples, and unpaid / partial / paid states (fictional data only).

## Tests

```bash
cd backend
pytest -q
```

Covers `/health`, demo login, tenant isolation, deterministic totals, duplicate flags, role-checked approvals, and partial/full payments.

## AI setup

1. Default: `AI_PROVIDER=demo` — deterministic stubs, no network.
2. Optional local Ollama later (M3): `AI_PROVIDER=ollama`, free open model only.
3. No paid LLM or OCR APIs.

## Demo steps (M2)

1. `docker compose up -d` → `alembic upgrade head` → `python -m scripts.seed`
2. Start API: `uvicorn app.main:app --reload --port 8004` — confirm `GET /health`
3. Start web: `cd web && npm run dev` → `http://localhost:3004`
4. Log in as `staff@invoiceai.local` / `demo`
5. **Suppliers:** open Suppliers (admin can add via `demo@invoiceai.local`)
6. **Create invoice:** Invoices → New invoice → pick supplier, add lines, create (totals auto-calc)
7. **Duplicate check:** create a second invoice with the same supplier + invoice number → see duplicate flag on detail
8. **Workflow:** on invoice detail → Submit for review → as `reviewer@…` Submit for approval
9. **Approve:** as `approver@…` open Approvals (or invoice detail) → Approve
10. **Pay:** record a partial payment, confirm status `partially_paid` and reduced balance; pay remainder → `paid`
11. Confirm tenant isolation: `other@otherco.local` cannot open Acme invoice IDs

API-only path (same flow): OpenAPI at `/docs` or:

```bash
# login → create invoice → workflow → approvals → payments
POST /api/v1/auth/demo-login
POST /api/v1/invoices
POST /api/v1/invoices/{id}/workflow  {"action":"submit_review"|"submit_approval"}
POST /api/v1/approvals?invoice_id=…  {"decision":"approved"|"rejected","comment":"…"}
POST /api/v1/payments                {"invoice_id","amount","payment_date","method"}
```

## Milestones / backlog

| Milestone | Scope | Status |
|-----------|--------|--------|
| **M1** | Env, Docker Postgres, models, Alembic, demo JWT + roles, org scoping, seed, `/health`, auth/tenant tests | **Done** |
| **M2** | Supplier/invoice CRUD, totals/duplicates/dates, workflow, approvals + audit, payments + balance, web UI, API tests | **Done** |
| **M3** | AIProvider extract/category/anomaly explain; Invoice Anomaly Radar UI; document metadata upload | Backlog |
| **M4** | Flutter capture/OCR path, offline drafts, reports + CSV, E2E polish | Backlog |

## Known limitations (M2)

- Prototype JWT auth only — not production security
- No OCR extraction or document processing
- Anomaly Radar UI not productized (seed flags only)
- Standalone `/invoice-lines` remains a stub (lines nest under invoices)
- Reports / aging / CSV export deferred
- Mobile camera/offline not required for M2

See [MVP_SPEC.md](./MVP_SPEC.md) for entities, API groups, and acceptance criteria.
