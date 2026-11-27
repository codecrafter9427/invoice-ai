# Invoice AI — Database backup & restore

PostgreSQL for this product listens on **host port `5436`** (see `docker-compose.yml`).

## Backup

```bash
# From host (Docker Desktop / Compose running)
docker exec invoiceai-postgres pg_dump -U invoiceai -d invoice_ai -Fc -f /tmp/invoice_ai.dump
docker cp invoiceai-postgres:/tmp/invoice_ai.dump ./backups/invoice_ai_$(date +%Y%m%d).dump
```

Plain SQL alternative:

```bash
docker exec invoiceai-postgres pg_dump -U invoiceai -d invoice_ai > ./backups/invoice_ai.sql
```

## Restore

```bash
docker cp ./backups/invoice_ai.dump invoiceai-postgres:/tmp/invoice_ai.dump
docker exec invoiceai-postgres pg_restore -U invoiceai -d invoice_ai --clean --if-exists /tmp/invoice_ai.dump
```

Or for SQL:

```bash
Get-Content ./backups/invoice_ai.sql | docker exec -i invoiceai-postgres psql -U invoiceai -d invoice_ai
```

## After restore

```bash
cd backend
alembic upgrade head
# Optional: re-seed only on empty / demo resets
python -m scripts.seed
```

## Notes

- Backups contain fictional demo data only in local setups.
- Do not commit dump files with real customer data.
- Production: schedule dumps outside the container and store encrypted off-host.
