# Invoice AI — Milestone 4 / 5 demo checklist

Scripted walkthrough for local demo (no paid APIs / OCR). Tick each step.

**M5:** Mobile camera/gallery free ML Kit OCR → review → draft (paste fallback OK).

## Prerequisites

- [ ] Docker Desktop running
- [ ] Python 3.11+ venv with `pip install -r backend/requirements.txt`
- [ ] Node 20+ for web
- [ ] (Optional) Flutter SDK for mobile — see `mobile/README.md`

## Boot

```bash
cd products/invoice-ai
cp .env.example .env          # if needed
docker compose up -d

cd backend
# activate .venv
alembic upgrade head
python -m scripts.seed
uvicorn app.main:app --reload --port 8004
```

```bash
cd web
npm install
npm run dev                   # http://localhost:3004
```

- [ ] `GET http://localhost:8004/health` → `version`: **`0.4.0-m4`**

## Web demo (primary)

Password for all accounts: **`demo`**

### A. Capture → review → approve → pay

1. [ ] Login as `staff@invoiceai.local`
2. [ ] **Invoices → New invoice** — pick supplier, add a line, create
3. [ ] Confirm duplicate flag if you reuse `INV-DUP-5500`
4. [ ] Open the invoice → **Submit for review**
5. [ ] Sign out; login as `reviewer@invoiceai.local` → **Submit for approval**
6. [ ] Sign out; login as `approver@invoiceai.local` → Approvals or invoice detail → **Approve**
7. [ ] Record a **partial payment**, then remaining balance → status **paid** / **partially_paid**

### B. Extract assist

1. [ ] Login as `staff@invoiceai.local` → **Extract assist**
2. [ ] Run extract on sample text
3. [ ] Confirm `ocr_verified=false` messaging and field confidence
4. [ ] Check **I reviewed** before treating fields as trusted

### C. Anomaly Radar

1. [ ] Open **Anomaly Radar**
2. [ ] Select `INV-ANOM-TAX-01` / `INV-ANOM-AMT-02` / `INV-ANOM-PAY-03` (or any flagged row)
3. [ ] Confirm signals show **not fraud** / never a fraud verdict

### D. Category confirm (PATCH)

1. [ ] Open an invoice detail with a category suggestion
2. [ ] Check confirm → **Save confirmed category**
3. [ ] Reload detail — saved `accounting_category_code` persists

### E. Document preview metadata

1. [ ] Open a seeded invoice that has a document (e.g. with OCR sample)
2. [ ] Confirm Document preview shows filename, content type, byte size, path, OCR preview/char count

### F. Reports + CSV

1. [ ] Login as `demo@invoiceai.local` → **Reports**
2. [ ] Aging buckets + row table load
3. [ ] Supplier spend table loads
4. [ ] **Export aging CSV** and **Export spend CSV** download

## Mobile demo (M5 OCR)

1. [ ] `cd mobile && flutter pub get && flutter run`
2. [ ] Set API base URL (emulator `http://10.0.2.2:8004`)
3. [ ] Login as `staff@invoiceai.local` / `demo`
4. [ ] **Invoice list** shows seeded statuses
5. [ ] **Capture → Camera or Gallery** → on-device ML Kit fills OCR text (or use paste fallback)
6. [ ] Confirm messaging shows `ocr_verified=false` / unverified until review
7. [ ] **Run extract** → edit fields → check **I reviewed** → **Save capture draft**
8. [ ] Confirm draft appears in list (not auto-submitted for review / not approved)
9. [ ] Confirm save is blocked if review checkbox is unchecked

## API-only smoke

```bash
POST /api/v1/auth/demo-login
GET  /api/v1/reports/payables/aging
GET  /api/v1/reports/payables/supplier-spend
GET  /api/v1/reports/payables/export.csv?report=aging
PATCH /api/v1/invoices/{id}/category  {"accounting_category_id","confirmed":true}
POST /api/v1/ai/invoice-extract
POST /api/v1/ai/invoice-anomalies
```

## Quality gates

```bash
cd backend && pytest -q
cd web && npm run lint && npm run typecheck
```

- [ ] pytest green
- [ ] lint / typecheck green (or gaps noted in README)
