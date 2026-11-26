# Invoice AI

Supplier invoice capture, extraction review, approval, payment tracking, and payable visibility for small businesses.

**Milestone 1 complete:** Postgres schema, Alembic migrations, demo JWT auth with org scoping, seed data, `/health`, and auth/tenant smoke tests. OCR extraction, full approval UX, and Anomaly Radar productization are deferred (see backlog).

## Purpose

- Capture supplier invoices (web upload / mobile camera) and review extracted fields
- Validate totals, duplicates, and missing fields with deterministic calculations
- Route invoices through review → approval → payment tracking
- Surface **Invoice Anomaly Radar** (differentiator): transparent review signals — never fraud verdicts
- Demo locally with free tooling only (no paid APIs or OCR services)

## Stack

| Layer | Technology |
|-------|------------|
| Web | Next.js + TypeScript |
| Backend | FastAPI + Pydantic + SQLAlchemy + Alembic |
| Database | PostgreSQL (UUID PKs, `Numeric` monetary decimals) |
| Mobile | Flutter (shell; M1 run optional) |
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
    app/                      # FastAPI app, models, auth, org-scoped lists
    alembic/                  # Migrations
    scripts/seed.py           # Demo seed
    tests/                    # Health + auth/tenant smoke tests
  web/                        # Next.js shell
  mobile/                     # Flutter shell
```

## Prerequisites

- Docker Desktop (PostgreSQL)
- Python 3.11+
- Node.js 20+
- Flutter SDK (optional for M1)

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

### 5. Mobile (optional for M1)

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

Covers `/health`, demo login, multi-role login, and org-scoped supplier/invoice isolation.

## AI setup

1. Default: `AI_PROVIDER=demo` — deterministic stubs, no network.
2. Optional local Ollama later (M3): `AI_PROVIDER=ollama`, free open model only.
3. No paid LLM or OCR APIs. M1 does not run real extraction.

## Demo steps (M1)

1. `docker compose up -d` → `alembic upgrade head` → `python -m scripts.seed`
2. Start API on `:8004`; confirm `GET /health` → `{status: ok}`
3. `POST /api/v1/auth/demo-login` with `demo@invoiceai.local` / `demo`
4. `GET /api/v1/suppliers` and `GET /api/v1/invoices` with `Authorization: Bearer <token>`
5. Log in as `other@otherco.local` and confirm suppliers/invoices do not overlap
6. Optional: open web login at `http://localhost:3004/login`

## Milestones / backlog

| Milestone | Scope | Status |
|-----------|--------|--------|
| **M1** | Env, Docker Postgres, models, Alembic, demo JWT + ≥2 roles, org scoping, seed (10/25), `/health`, auth/tenant smoke tests, README | **Done** |
| **M2** | Invoice/supplier CRUD, capture → review workflow, deterministic validation (totals, duplicates, dates), document metadata upload (no OCR SaaS), payment recording API | Backlog |
| **M3** | AIProvider + DemoAIProvider wired extract/category/anomaly explain; Invoice Anomaly Radar UI signals (rules first, never fraud); optional local Ollama | Backlog |
| **M4** | Flutter capture/OCR path, offline drafts, full approval UX polish, aging/spend reports + CSV, E2E demo script, lint/type gates | Backlog |

## Known limitations (M1)

- Prototype JWT auth only — not production security
- Supplier/invoice **mutations**, approvals, payments APIs still Coming Soon (lists are org-scoped)
- No OCR extraction or document processing
- AI endpoints remain stubs
- Mobile camera/offline not required for M1
- Duplicate pairs allowed in DB so seed can demonstrate flags; M2 validates before submit

See [MVP_SPEC.md](./MVP_SPEC.md) for entities, API groups, and acceptance criteria.
