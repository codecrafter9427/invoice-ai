# Invoice AI

Supplier invoice capture, extraction review, approval, payment tracking, and payable visibility for small businesses.

This folder is a **portfolio MVP skeleton**. OCR extraction, approval workflows, payments, and real AI extraction are intentionally stubbed or marked Coming Soon.

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
| Database | PostgreSQL (UUID primary keys) |
| Mobile | Flutter |
| AI | `AIProvider` interface + deterministic `DemoAIProvider`; optional local Ollama adapter stub |
| Auth | Demo login placeholder only |

## Project layout

```
products/invoice-ai/
  README.md
  MVP_SPEC.md
  .env.example
  docker-compose.yml
  backend/          # FastAPI API skeleton
  web/              # Next.js app shell
  mobile/           # Flutter shell
```

## Prerequisites

- Docker Desktop (for PostgreSQL)
- Python 3.11+
- Node.js 20+
- Flutter SDK (for mobile shell)

## Setup

### 1. Environment

```bash
cd products/invoice-ai
cp .env.example .env
```

Edit `.env` if needed. Values are local placeholders only.

### 2. Database

```bash
docker compose up -d
```

Starts PostgreSQL only on port `5434` (mapped from container `5432`).

### 3. Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8004
```

- Health: `GET http://localhost:8004/health`
- API prefix: `/api/v1`
- OpenAPI: `http://localhost:8004/docs`

Migrations and seed scripts are placeholders (Milestone 1/2). Do not expect full schema or seed data yet.

### 4. Web

```bash
cd web
npm install
npm run dev
```

Open `http://localhost:3004`. Demo login is a client-side / demo-API placeholder. Suppliers, invoices, approvals, payments, and reports are marked **Coming Soon**.

### 5. Mobile

```bash
cd mobile
flutter pub get
flutter run
```

Shows demo login, home shortcuts, capture stub, and invoice list stub only.

## AI setup

1. Default: `AI_PROVIDER=demo` uses `DemoAIProvider` (deterministic stubs, no network).
2. Optional local Ollama: install [Ollama](https://ollama.com), pull a free open model (e.g. `ollama pull llama3.2`), set `AI_PROVIDER=ollama` and `OLLAMA_BASE_URL` / `OLLAMA_MODEL` in `.env`.
3. Backend-only model calls; typed schemas; no paid LLM or OCR APIs.
4. AI endpoints under `/api/v1/ai/*` return stub responses until Milestone 3.
5. Invoice Anomaly Radar explains review signals only — never declares fraud.

## Demo credentials (placeholder)

| Field | Value |
|-------|--------|
| Email | `demo@invoiceai.local` |
| Password | `demo` |

Not wired to real session/JWT yet.

## Milestones

1. **Scaffold** — repo, env, Docker Postgres, health, demo login shell, Coming Soon routes *(current)*
2. **Core payables** — migrations, seed (10 suppliers / 25 invoices), capture → review CRUD, validation, duplicate flags
3. **AI + differentiator** — Ollama/demo providers, extract stubs → real local extract, Invoice Anomaly Radar, category suggestion
4. **Polish** — mobile OCR path, offline drafts, approvals/payments, tests, README demo recording

## Known limitations

- No real authentication, tenant enforcement, or seed data yet
- Invoice/supplier/approval/payment APIs return Coming Soon stubs
- No OCR extraction or document processing
- AI providers return labeled stubs (Ollama not wired to model calls)
- Mobile has no camera OCR, offline sync, or payment recording
- Prototype security only — not production-ready

See [MVP_SPEC.md](./MVP_SPEC.md) for roles, entities, API groups, acceptance criteria, and backlog.
