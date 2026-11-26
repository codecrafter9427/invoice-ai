# Invoice AI

Supplier invoice capture, extraction review, approval, payment tracking, and payable visibility for small businesses.

**Milestone 4 complete:** aging + supplier-spend reports with CSV export, category suggestion confirm via PATCH, tightened document preview metadata, web UX polish, Flutter capture/list against API, expanded tests, and a scripted [DEMO.md](./DEMO.md).

## Purpose

- Capture supplier invoices (manual entry + text/OCR extract assist) and review fields
- Validate totals, duplicates, and dates with deterministic calculations
- Route invoices through review → approval → payment tracking
- Surface **Invoice Anomaly Radar**: transparent review signals — never fraud verdicts
- Aging and supplier-spend reports with CSV export
- Demo locally with free tooling only (no paid APIs or OCR services)

## Stack

| Layer | Technology |
|-------|------------|
| Web | Next.js + TypeScript |
| Backend | FastAPI + Pydantic + SQLAlchemy + Alembic |
| Database | PostgreSQL (UUID PKs, `Numeric` monetary decimals) |
| Mobile | Flutter (login / list / capture draft against API) |
| AI | `AIProvider` + `DemoAIProvider` (default); optional Ollama adapter |
| Auth | Demo JWT login, org-scoped authorization |

## Project layout

```
products/invoice-ai/
  README.md
  DEMO.md                     # Scripted M4 checklist
  MVP_SPEC.md
  .env.example
  docker-compose.yml          # Postgres on host port 5436
  backend/
    app/                      # FastAPI app, services, APIs, ai/
    alembic/                  # Migrations
    scripts/seed.py           # Demo seed
    tests/                    # Health, auth/tenant, M2–M4 tests
  web/                        # Next.js payables UI
  mobile/                     # Flutter app (see mobile/README.md)
```

## Prerequisites

- Docker Desktop (PostgreSQL)
- Python 3.11+
- Node.js 20+
- Flutter SDK (optional — for device run; see `mobile/README.md`)
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

- Health: `GET http://localhost:8004/health` → `0.4.0-m4`
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

Documented Flutter SDK install and device base URLs: [mobile/README.md](./mobile/README.md).

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

## Tests & quality gates

```bash
cd backend
pytest -q
```

```bash
cd web
npm run lint
npm run typecheck
```

Covers `/health`, demo login, tenant isolation, deterministic totals, duplicate flags, role-checked approvals, payments, demo extract, Anomaly Radar (never fraud), **category confirm PATCH**, **aging/spend reports + CSV**, document preview metadata, and AI auth.

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

## Demo steps (M4)

Full scripted checklist: **[DEMO.md](./DEMO.md)**

Short path:

1. Boot DB + seed + API (`0.4.0-m4`) + web
2. Staff: create invoice → review → Approver: approve → partial pay
3. Extract assist + Anomaly Radar (signals labeled not fraud)
4. Confirm category on invoice detail (PATCH persist)
5. Reports → aging + supplier spend → CSV export
6. Optional Flutter: login → list → capture draft

## Architecture notes

- Organization-scoped JWT; every list/get/mutation filters by `org_id`
- Monetary math and aging buckets are **deterministic code** (`app.services.totals`, `app.services.reports`)
- AI endpoints return `{result, explanation, sources, requires_confirmation}` — category/extract require human confirm
- Document endpoints register **metadata + optional pasted OCR text** only (no SaaS OCR upload)
- Reports: `GET /api/v1/reports/payables/aging`, `/supplier-spend`, `/export.csv?report=aging|supplier_spend`

## Milestones

| Milestone | Scope | Status |
|-----------|--------|--------|
| **M1** | Env, Docker Postgres, models, Alembic, demo JWT + roles, org scoping, seed, `/health`, auth/tenant tests | **Done** |
| **M2** | Supplier/invoice CRUD, totals/duplicates/dates, workflow, approvals + audit, payments + balance, web UI, API tests | **Done** |
| **M3** | AIProvider extract/category/anomaly explain; Invoice Anomaly Radar UI; document metadata upload | **Done** |
| **M4** | Reports + CSV, category confirm PATCH, document preview, web/Flutter polish, DEMO.md, expanded tests | **Done** |

## Known limitations

- Prototype JWT auth only — not production security
- Extract is heuristic over pasted/OCR text (no SaaS OCR); user must review
- Anomaly Radar never auto-blocks payment; signals are advisory
- Category suggestion is not accounting/tax advice; confirm before save
- Standalone `/invoice-lines` remains a stub (lines nest under invoices)
- Flutter camera/ML Kit OCR and offline draft queue are optional / Coming Soon (paste-text capture works)
- Mobile approvals/payments UX remain web-primary for the demo

See [MVP_SPEC.md](./MVP_SPEC.md) for entities, API groups, and acceptance criteria.
