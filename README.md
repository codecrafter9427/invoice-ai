# Invoice AI

Supplier invoice capture, extraction review, approval, payment tracking, and payable visibility for small businesses.

**Milestone 6:** Standalone invoice-reviews queue + web Reviews page; human-confirmed PO match (candidates + differences); Insights connector; auth/AI rate limits; JWT `expires_in` + refresh; prod secret guards; backup docs + CI. DemoAI default. Deterministic totals. No paid OCR.

**Milestone 5:** Flutter camera/gallery → free on-device ML Kit OCR → review → draft. Paste fallback kept.

**Milestone 4:** Aging + supplier-spend reports with CSV, category confirm PATCH, document preview, web/Flutter polish, DEMO.md.

## Purpose

- Capture supplier invoices (manual entry + text/OCR extract assist) and review fields
- Validate totals, duplicates, and dates with deterministic calculations
- Route invoices through review → approval → payment tracking
- Human-confirm PO matches (never auto-link)
- Surface **Invoice Anomaly Radar**: transparent review signals — never fraud verdicts
- Expose read-only payables metrics to Business Insights
- Demo locally with free tooling only (no paid APIs or OCR services)

## Stack

| Layer | Technology |
|-------|------------|
| Web | Next.js + TypeScript |
| Backend | FastAPI + Pydantic + SQLAlchemy + Alembic |
| Database | PostgreSQL (UUID PKs, `Numeric` monetary decimals) |
| Mobile | Flutter (login / list / capture with free ML Kit OCR + paste) |
| AI | `AIProvider` + `DemoAIProvider` (default); optional Ollama adapter |
| Auth | Demo JWT login, org-scoped authorization, optional refresh |

## Project layout

```
products/invoice-ai/
  README.md
  DEMO.md
  MVP_SPEC.md
  docs/BACKUP.md
  docs/CONNECTORS.md
  .env.example
  docker-compose.yml          # Postgres on host port 5436
  backend/
  web/
  mobile/
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

PostgreSQL listens on **host port `5436`** (container `5432`). Backup notes: [docs/BACKUP.md](./docs/BACKUP.md).

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

- Health: `GET http://localhost:8004/health` → `0.6.0-m6`
- API prefix: `/api/v1`
- OpenAPI: `http://localhost:8004/docs`
- Insights connector: [docs/CONNECTORS.md](./docs/CONNECTORS.md)

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

CI workflow: `.github/workflows/ci.yml` (pytest + web lint/typecheck).

## AI setup (no Ollama required)

Default is fully local and offline (`AI_PROVIDER=demo`). Optional Ollama enriches explanations only; totals stay deterministic.

## Demo steps (M6)

1. Boot DB + seed + API (`0.6.0-m6`) + web
2. **Reviews** page → needs-review queue → add note → submit for approval
3. Invoice detail → **PO match** candidates/differences → confirm checkbox → link
4. Approver: approve → pay (staff remains forbidden)
5. Reports + Insights: `GET /api/v1/connectors/insights/v1/payables/summary`

Full earlier checklist: **[DEMO.md](./DEMO.md)**

## Architecture notes

- Organization-scoped JWT; every list/get/mutation filters by `org_id`
- Monetary math and aging buckets are **deterministic code**
- PO matches require `confirmed:true` — extract never sets `purchase_order_reference_id`
- Auth/AI endpoints are rate-limited in-memory; login returns `expires_in`; `POST /auth/refresh` slides the session
- `APP_ENV=production` refuses weak `SECRET_KEY` and `DEBUG=true`

## Milestones

| Milestone | Scope | Status |
|-----------|--------|--------|
| **M1** | Env, Docker Postgres, models, Alembic, demo JWT + roles, org scoping, seed, `/health`, auth/tenant tests | **Done** |
| **M2** | Supplier/invoice CRUD, totals/duplicates/dates, workflow, approvals + audit, payments + balance, web UI, API tests | **Done** |
| **M3** | AIProvider extract/category/anomaly explain; Invoice Anomaly Radar UI; document metadata upload | **Done** |
| **M4** | Reports + CSV, category confirm PATCH, document preview, web/Flutter polish, DEMO.md, expanded tests | **Done** |
| **M5** | Flutter camera/gallery + free ML Kit OCR → review → draft; paste fallback | **Done** |
| **M6** | Reviews queue, PO confirm, Insights connector, hardening, CI/backup | **Done** |

## Known limitations

- Prototype JWT auth only — refresh is sliding access, not a stored refresh-token store
- In-memory rate limits reset per process
- Extract is heuristic over pasted/OCR text; user must review
- Anomaly Radar never auto-blocks payment
- Standalone `/invoice-lines` remains a stub
- Flutter offline draft queue remains out of scope
- Local `PurchaseOrderReference` table is not Inventory AI POs

See [MVP_SPEC.md](./MVP_SPEC.md) for entities, API groups, and acceptance criteria.
