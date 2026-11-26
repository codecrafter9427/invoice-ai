# Invoice AI

Supplier invoice capture, extraction review, approval, payment tracking, and payable visibility for small businesses.

**Milestone 3 complete:** DemoAIProvider extract / category / anomaly explain, Invoice Anomaly Radar (rules-first, never fraud), extract-assist + radar web UI, document metadata registration, and AI API tests. Flutter capture remains optional (M4).

## Purpose

- Capture supplier invoices (manual entry + text/OCR extract assist) and review fields
- Validate totals, duplicates, and dates with deterministic calculations
- Route invoices through review → approval → payment tracking
- Surface **Invoice Anomaly Radar**: transparent review signals — never fraud verdicts
- Demo locally with free tooling only (no paid APIs or OCR services)

## Stack

| Layer | Technology |
|-------|------------|
| Web | Next.js + TypeScript |
| Backend | FastAPI + Pydantic + SQLAlchemy + Alembic |
| Database | PostgreSQL (UUID PKs, `Numeric` monetary decimals) |
| Mobile | Flutter (shell; run optional) |
| AI | `AIProvider` + `DemoAIProvider` (default); optional Ollama adapter |
| Auth | Demo JWT login, org-scoped authorization |

## Project layout

```
products/invoice-ai/
  README.md
  MVP_SPEC.md
  .env.example
  docker-compose.yml          # Postgres on host port 5436
  backend/
    app/                      # FastAPI app, services, APIs, ai/
    alembic/                  # Migrations
    scripts/seed.py           # Demo seed
    tests/                    # Health, auth/tenant, M2 workflow, M3 AI tests
  web/                        # Next.js payables UI
  mobile/                     # Flutter shell
```

## Prerequisites

- Docker Desktop (PostgreSQL)
- Python 3.11+
- Node.js 20+
- Flutter SDK (optional)
- Ollama (optional — not required)

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

Seed includes: **10 suppliers**, **25 invoices** with line items, duplicate + anomaly flag examples, sample OCR text on a few documents, and unpaid / partial / paid states (fictional data only).

## Tests

```bash
cd backend
pytest -q
```

Covers `/health`, demo login, tenant isolation, deterministic totals, duplicate flags, role-checked approvals, payments, **demo extract**, **Anomaly Radar (never fraud)**, category confirmation, and AI auth.

## AI setup (no Ollama required)

Default is fully local and offline:

1. Keep `AI_PROVIDER=demo` in `.env` (this is the default).
2. Start the API — extract, category suggestion, and Anomaly Radar work with deterministic heuristics/rules.
3. No network calls, no paid LLM, no paid OCR.

Optional local Ollama (not needed for demos or tests):

1. Install [Ollama](https://ollama.com) and pull a free open model (e.g. `llama3.2`).
2. Set `AI_PROVIDER=ollama`, `OLLAMA_BASE_URL=http://localhost:11434`, `OLLAMA_MODEL=llama3.2`.
3. If Ollama is down, the adapter falls back to `DemoAIProvider`.
4. Structured extract + anomaly **rules** stay deterministic; Ollama may only enrich explanations. Totals are never computed by AI.

## Demo steps (M3)

1. `docker compose up -d` → `alembic upgrade head` → `python -m scripts.seed`
2. Start API: `uvicorn app.main:app --reload --port 8004` — confirm `GET /health` → `0.3.0-m3`
3. Start web: `cd web && npm run dev` → `http://localhost:3004`
4. Log in as `staff@invoiceai.local` / `demo`
5. **Extract assist:** open Extract assist → Run extract on the sample text → confirm OCR unverified + field confidence → check “I reviewed”
6. **Anomaly Radar:** open Anomaly Radar → select `INV-ANOM-TAX-01` / `INV-ANOM-AMT-02` / `INV-ANOM-PAY-03` → see rules-first signals labeled **not fraud**
7. **Invoice detail:** open a flagged invoice → Anomaly Radar panel + category suggestion (confirm checkbox)
8. **M2 regression:** create invoice → duplicate flag → review → approve → partial pay (totals still from code)

API-only AI path:

```bash
POST /api/v1/auth/demo-login
POST /api/v1/ai/invoice-extract     {"input":{"text":"…"}}
POST /api/v1/ai/invoice-anomalies   {"input":{"invoice_id":"…"}}
POST /api/v1/ai/category-suggestion {"input":{"description":"Hosting plan"}}
POST /api/v1/documents              {"invoice_id","filename","storage_path",…}
```

## Milestones / backlog

| Milestone | Scope | Status |
|-----------|--------|--------|
| **M1** | Env, Docker Postgres, models, Alembic, demo JWT + roles, org scoping, seed, `/health`, auth/tenant tests | **Done** |
| **M2** | Supplier/invoice CRUD, totals/duplicates/dates, workflow, approvals + audit, payments + balance, web UI, API tests | **Done** |
| **M3** | AIProvider extract/category/anomaly explain; Invoice Anomaly Radar UI; document metadata upload | **Done** |
| **M4** | Flutter capture/OCR path, offline drafts, reports + CSV, E2E polish | Backlog |

## Known limitations (M3)

- Prototype JWT auth only — not production security
- Extract is heuristic over pasted/OCR text (no SaaS OCR); user must review
- Anomaly Radar never auto-blocks payment; signals are advisory
- Category suggestion is not accounting/tax advice; confirm before save
- Standalone `/invoice-lines` remains a stub (lines nest under invoices)
- Reports / aging / CSV export deferred to M4
- Mobile camera/offline not required for M3

See [MVP_SPEC.md](./MVP_SPEC.md) for entities, API groups, and acceptance criteria.
